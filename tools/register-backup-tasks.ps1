<#
.SYNOPSIS
  (Re)register the hourly OneDrive backup tasks in Windows Task Scheduler.

.DESCRIPTION
  One place that knows every backup job, so a rebuilt machine gets them all back with one
  command. Each task runs its script hourly as the logged-in user, catches up if the PC was
  asleep, runs one instance at a time, and is killed after 30 minutes.

  Run from PowerShell:
      powershell -ExecutionPolicy Bypass -File tools\register-backup-tasks.ps1
  To touch only one task:
      powershell -ExecutionPolicy Bypass -File tools\register-backup-tasks.ps1 -Only "Liminality claude-home backup to OneDrive"

  A task whose script is not on this machine is skipped, so this is safe to run on a PC that
  has only some of the repos. An existing task of the same name is replaced.
#>
param([string] $Only)

$ErrorActionPreference = 'Stop'

$tasks = @(
    @{ Name = 'Liminality backtest backup to OneDrive'
       Script = 'C:\Liminality-put-writing-strategy\tools\backup-to-onedrive.ps1' },
    @{ Name = 'Liminality french-swap-spreads backup to OneDrive'
       Script = 'C:\Liminality-french-swap-spreads\tools\backup-to-onedrive.ps1' },
    @{ Name = 'Liminality Claude-Setup-CHL backup to OneDrive'
       Script = 'C:\Liminality-Claude-Setup-CHL\tools\backup-to-onedrive.ps1' },
    @{ Name = 'Liminality claude-home backup to OneDrive'
       Script = 'C:\Liminality-Claude-Setup-CHL\tools\backup-claude-home-to-onedrive.ps1' }
)

$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

foreach ($t in $tasks) {
    if ($Only -and $t.Name -ne $Only) { continue }
    if (-not (Test-Path $t.Script)) { Write-Host "skip      $($t.Name)  (script not on this machine)"; continue }
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $t.Script)
    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
        -Description ('Hourly copy-only backup to company OneDrive. Script: {0}' -f $t.Script) -Force | Out-Null
    Write-Host "registered $($t.Name)"
}
