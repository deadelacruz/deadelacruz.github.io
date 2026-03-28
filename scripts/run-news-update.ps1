[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$Branch = "",
    [string]$LogPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:LastExternalExitCode = 0

if (-not $RepoRoot) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Write-Log {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp [$Level] $Message"
    Write-Output $line

    if ($LogPath) {
        try {
            $logDir = Split-Path -Parent $LogPath
            if ($logDir -and -not (Test-Path $logDir)) {
                New-Item -ItemType Directory -Path $logDir -Force | Out-Null
            }
            Add-Content -Path $LogPath -Value $line -Encoding UTF8
        } catch {
            Write-Output "$timestamp [WARN] Failed to write to log file: $LogPath"
        }
    }
}

function Find-Executable {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }
    return $null
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Description,
        [switch]$AllowFailure
    )

    [void](Write-Log -Message $Description)
    & $FilePath @Arguments
    $script:LastExternalExitCode = [int]$LASTEXITCODE
    $exitCode = $script:LastExternalExitCode

    if (-not $AllowFailure -and $exitCode -ne 0) {
        throw "$Description failed with exit code $exitCode."
    }
}

function Get-CurrentBranch {
    param([Parameter(Mandatory = $true)][string]$GitExe)
    $branchName = (& $GitExe rev-parse --abbrev-ref HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $branchName) {
        throw "Unable to determine current git branch."
    }
    if ($branchName -eq "HEAD") {
        throw "Detached HEAD detected. Please pass -Branch explicitly."
    }
    return $branchName
}

function Get-GitChangedPaths {
    param([Parameter(Mandatory = $true)][string]$GitExe)
    $allPaths = @()

    # Unstaged tracked changes
    $unstagedPaths = & $GitExe diff --name-only
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read unstaged git changes."
    }
    $allPaths += $unstagedPaths

    # Staged tracked changes
    $stagedPaths = & $GitExe diff --cached --name-only
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read staged git changes."
    }
    $allPaths += $stagedPaths

    # Untracked files
    $untrackedPaths = & $GitExe ls-files --others --exclude-standard
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read untracked git changes."
    }
    $allPaths += $untrackedPaths

    # Normalize path separators and de-duplicate.
    return @(
        $allPaths |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_.Trim().Replace('\', '/') } |
            Sort-Object -Unique
    )
}

function Is-AllowedWorkingTreePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (
        $Path.StartsWith("_data/news/") -or
        $Path -eq "_data/news_last_updated.yml" -or
        $Path -eq "_data/news_metrics.json"
    )
}

$originalLocation = Get-Location

try {
    $resolvedRepoRoot = (Resolve-Path $RepoRoot).Path
    Set-Location $resolvedRepoRoot

    Write-Log -Message "Starting local news update run in $resolvedRepoRoot"

    $gitExe = Find-Executable -Candidates @(
        "git.exe",
        "git",
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Program Files (x86)\Git\cmd\git.exe",
        "C:\Program Files (x86)\Git\bin\git.exe"
    )
    if (-not $gitExe) {
        throw "Git is not installed or not available on PATH."
    }

    if (-not (Test-Path (Join-Path $resolvedRepoRoot ".git"))) {
        throw "This folder is not a git repository. Clone the repo with git, then rerun setup."
    }

    $insideWorkTree = (& $gitExe rev-parse --is-inside-work-tree 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or $insideWorkTree -ne "true") {
        throw "This folder is not a git repository. Clone the repo first, then rerun setup."
    }

    $originUrl = (& $gitExe remote get-url origin 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $originUrl) {
        throw "Git remote 'origin' is missing. Set origin to your GitHub repository URL."
    }

    if (-not $Branch) {
        $Branch = Get-CurrentBranch -GitExe $gitExe
    }
    Write-Log -Message "Using branch '$Branch'"

    $venvPython = Join-Path $resolvedRepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $pythonExe = $venvPython
    } else {
        $pythonExe = Find-Executable -Candidates @(
            "python.exe",
            "python",
            "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe",
            "C:\Program Files\Python311\python.exe",
            "C:\Python311\python.exe"
        )
    }
    if (-not $pythonExe) {
        throw "Python is not installed or not available on PATH, and .venv is missing."
    }

    if (-not $env:NEWSAPI_KEY) {
        $userKey = [Environment]::GetEnvironmentVariable("NEWSAPI_KEY", "User")
        $machineKey = [Environment]::GetEnvironmentVariable("NEWSAPI_KEY", "Machine")
        if ($userKey) {
            $env:NEWSAPI_KEY = $userKey
        } elseif ($machineKey) {
            $env:NEWSAPI_KEY = $machineKey
        }
    }
    if (-not $env:NEWSAPI_KEY) {
        throw "NEWSAPI_KEY is missing. Set it in user environment before running this task."
    }

    $changedPaths = Get-GitChangedPaths -GitExe $gitExe
    $blockedPaths = @($changedPaths | Where-Object { -not (Is-AllowedWorkingTreePath -Path $_) })
    if ($blockedPaths.Count -gt 0) {
        Write-Log -Level "WARN" -Message "Skipping run. Found non-news working tree changes:"
        foreach ($path in $blockedPaths) {
            Write-Log -Level "WARN" -Message " - $path"
        }
        exit 0
    }

    $gitUserName = (& $gitExe config user.name).Trim()
    if (-not $gitUserName) {
        Invoke-External -FilePath $gitExe -Arguments @("config", "user.name", "Local News Bot") -Description "Configuring local git user.name"
    }
    $gitUserEmail = (& $gitExe config user.email).Trim()
    if (-not $gitUserEmail) {
        Invoke-External -FilePath $gitExe -Arguments @("config", "user.email", "action@github.com") -Description "Configuring local git user.email"
    }

    Invoke-External -FilePath $gitExe -Arguments @("fetch", "origin", $Branch) -Description "Fetching latest remote commits"

    Invoke-External -FilePath $gitExe -Arguments @("pull", "--ff-only", "origin", $Branch) -Description "Pulling latest commits (fast-forward)" -AllowFailure
    $pullCode = $script:LastExternalExitCode
    if ($pullCode -ne 0) {
        Write-Log -Level "WARN" -Message "Fast-forward pull failed. Retrying with rebase."
        Invoke-External -FilePath $gitExe -Arguments @("pull", "--rebase", "origin", $Branch) -Description "Pulling latest commits (rebase fallback)"
    }

    Invoke-External -FilePath $pythonExe -Arguments @("-m", "update_news") -Description "Running news updater"

    try {
        $manilaTimeZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Singapore Standard Time")
        $manilaTime = [System.TimeZoneInfo]::ConvertTime((Get-Date), $manilaTimeZone)
    } catch {
        $manilaTime = (Get-Date).ToUniversalTime().AddHours(8)
    }
    $timestampText = $manilaTime.ToString("yyyy-MM-dd hh:mm:ss tt") + " GMT +8"
    $timestampFile = Join-Path $resolvedRepoRoot "_data/news_last_updated.yml"
    Set-Content -Path $timestampFile -Value "last_updated: `"$timestampText`"" -Encoding UTF8
    Write-Log -Message "Updated timestamp file: $timestampText"

    Invoke-External -FilePath $gitExe -Arguments @("add", "_data/news", "_data/news_last_updated.yml") -Description "Staging news updates"

    & $gitExe diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Log -Message "No news changes detected. Nothing to commit."
        exit 0
    }

    $commitMessage = "Auto-update news (local): $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Invoke-External -FilePath $gitExe -Arguments @("commit", "-m", $commitMessage) -Description "Committing updates"

    $maxPushAttempts = 3
    $pushSuccessful = $false
    for ($attempt = 1; $attempt -le $maxPushAttempts; $attempt++) {
        Invoke-External -FilePath $gitExe -Arguments @("push", "origin", $Branch) -Description "Pushing commit to origin (attempt $attempt/$maxPushAttempts)" -AllowFailure
        $pushCode = $script:LastExternalExitCode
        if ($pushCode -eq 0) {
            $pushSuccessful = $true
            break
        }

        if ($attempt -lt $maxPushAttempts) {
            Write-Log -Level "WARN" -Message "Push failed. Pulling latest with rebase before retry."
            Invoke-External -FilePath $gitExe -Arguments @("pull", "--rebase", "origin", $Branch) -Description "Rebasing before push retry"
        }
    }

    if (-not $pushSuccessful) {
        throw "Push failed after $maxPushAttempts attempts."
    }

    Write-Log -Message "Local news update completed successfully."
    exit 0
} catch {
    Write-Log -Level "ERROR" -Message $_.Exception.Message
    exit 1
} finally {
    Set-Location $originalLocation
}
