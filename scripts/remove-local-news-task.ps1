[CmdletBinding()]
param(
    [string]$TaskName = "UpdateNewsEvery12HoursLocal"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Output "Task '$TaskName' does not exist."
        exit 0
    }

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Task '$TaskName' has been removed."
    exit 0
} catch {
    Write-Output "Failed to remove task '$TaskName': $($_.Exception.Message)"
    exit 1
}
