[CmdletBinding()]
param(
    [string]$TaskName = "UpdateNewsEvery12HoursLocal",
    [string]$RepoRoot = "",
    [string]$Branch = "",
    [string]$NewsApiKey = "",
    [switch]$SkipVenvSetup,
    [switch]$RunNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Write-SetupLog {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "$timestamp [$Level] $Message"
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
        [Parameter(Mandatory = $true)][string]$Description
    )
    Write-SetupLog -Message $Description
    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
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
        throw "Detached HEAD detected. Re-run with -Branch."
    }
    return $branchName
}

function Resolve-NewsApiKey {
    param([string]$InputKey)

    if ($InputKey) {
        [Environment]::SetEnvironmentVariable("NEWSAPI_KEY", $InputKey, "User")
        $env:NEWSAPI_KEY = $InputKey
        return $InputKey
    }

    if ($env:NEWSAPI_KEY) {
        return $env:NEWSAPI_KEY
    }

    $userKey = [Environment]::GetEnvironmentVariable("NEWSAPI_KEY", "User")
    if ($userKey) {
        $env:NEWSAPI_KEY = $userKey
        return $userKey
    }

    $machineKey = [Environment]::GetEnvironmentVariable("NEWSAPI_KEY", "Machine")
    if ($machineKey) {
        $env:NEWSAPI_KEY = $machineKey
        return $machineKey
    }

    return $null
}

try {
    $resolvedRepoRoot = (Resolve-Path $RepoRoot).Path
    $runnerScript = Join-Path $resolvedRepoRoot "scripts\run-news-update.ps1"
    if (-not (Test-Path $runnerScript)) {
        throw "Runner script not found: $runnerScript"
    }

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

    Push-Location $resolvedRepoRoot
    try {
        if (-not (Test-Path (Join-Path $resolvedRepoRoot ".git"))) {
            throw "This folder is not a git repository. Clone it with git first."
        }

        $insideWorkTree = (& $gitExe rev-parse --is-inside-work-tree 2>$null).Trim()
        if ($LASTEXITCODE -ne 0 -or $insideWorkTree -ne "true") {
            throw "This folder is not a git repository. Clone it with git first."
        }

        $originUrl = (& $gitExe remote get-url origin 2>$null).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $originUrl) {
            throw "Git remote 'origin' is missing. Set origin to your GitHub repository URL."
        }

        if (-not $Branch) {
            $Branch = Get-CurrentBranch -GitExe $gitExe
        }
        Write-SetupLog -Message "Using branch '$Branch'"
    } finally {
        Pop-Location
    }

    $apiKey = Resolve-NewsApiKey -InputKey $NewsApiKey
    if (-not $apiKey) {
        throw "NEWSAPI_KEY is missing. Re-run setup with -NewsApiKey or set NEWSAPI_KEY in user environment."
    }
    Write-SetupLog -Message "NEWSAPI_KEY is available for scheduled runs."

    $venvPython = Join-Path $resolvedRepoRoot ".venv\Scripts\python.exe"
    if (-not $SkipVenvSetup) {
        $pythonExe = Find-Executable -Candidates @(
            "python.exe",
            "python",
            "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe",
            "C:\Program Files\Python311\python.exe",
            "C:\Python311\python.exe"
        )
        if (-not (Test-Path $venvPython)) {
            if (-not $pythonExe) {
                throw "Python is not installed and .venv does not exist. Install Python first."
            }
            Invoke-External -FilePath $pythonExe -Arguments @("-m", "venv", ".venv") -Description "Creating Python virtual environment (.venv)"
        }

        if (-not (Test-Path $venvPython)) {
            throw "Virtual environment python executable not found: $venvPython"
        }

        Invoke-External -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip") -Description "Upgrading pip in .venv"
        $requirementsPath = Join-Path $resolvedRepoRoot "requirements.txt"
        Invoke-External -FilePath $venvPython -Arguments @("-m", "pip", "install", "-r", $requirementsPath) -Description "Installing Python dependencies"
    } else {
        Write-SetupLog -Level "WARN" -Message "Skipping .venv dependency setup as requested."
    }

    $logsDir = Join-Path $resolvedRepoRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }
    $logPath = Join-Path $logsDir "news-update.log"

    $safeRunnerPath = $runnerScript.Replace('"', '""')
    $safeRepoRoot = $resolvedRepoRoot.Replace('"', '""')
    $safeBranch = $Branch.Replace('"', '""')
    $safeLogPath = $logPath.Replace('"', '""')
    $taskArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$safeRunnerPath`" -RepoRoot `"$safeRepoRoot`" -Branch `"$safeBranch`" -LogPath `"$safeLogPath`""

    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $taskArgs
    $triggerMorning = New-ScheduledTaskTrigger -Daily -At "08:00"
    $triggerEvening = New-ScheduledTaskTrigger -Daily -At "20:00"
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
    $userId = "$env:USERDOMAIN\$env:USERNAME"
    try {
        $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType S4U -RunLevel Limited
        Write-SetupLog -Message "Using S4U logon type so task can run even when you are logged out."
    } catch {
        Write-SetupLog -Level "WARN" -Message "S4U logon type is unavailable on this machine. Falling back to Interactive."
        $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
    }

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger @($triggerMorning, $triggerEvening) `
        -Settings $settings `
        -Principal $principal `
        -Description "Runs local news update every 12 hours and pushes updates to GitHub." `
        -Force | Out-Null

    Write-SetupLog -Message "Scheduled task '$TaskName' created."
    Write-SetupLog -Message "Run times: daily at 08:00 and 20:00 local machine time."
    Write-SetupLog -Message "Log file: $logPath"

    if ($RunNow) {
        Start-ScheduledTask -TaskName $TaskName
        Write-SetupLog -Message "Task started immediately."
    }

    Write-SetupLog -Message "Setup complete."
    exit 0
} catch {
    Write-SetupLog -Level "ERROR" -Message $_.Exception.Message
    exit 1
}
