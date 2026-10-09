<#
.SYNOPSIS
  Incremental backup of this repo and its Claude session history to company OneDrive.

.DESCRIPTION
  Copies only new and changed files into <OneDrive>\Liminality-Claude-Setup-CHL-backup-current\.
  Runs hourly from the Windows scheduled task "Liminality Claude-Setup-CHL backup to OneDrive".
  Same script as the put-writing and swap-spreads repos, with the paths changed.

  COPY-ONLY, NEVER DELETE. There is deliberately no /MIR or /PURGE: if a file disappears from
  this machine it must NOT disappear from the backup on the next run, since that is the exact
  failure this exists to insure against. The cost is that files deleted on purpose linger.

  Paths come from environment variables, so there is no machine- or user-specific text here.

.NOTES
  Excluded: .venv, __pycache__, .pytest_cache. This repo holds no secrets; the live
  ~/.claude folder it mirrors is covered by the repo itself (home/), not by this script.
#>

$ErrorActionPreference = 'Stop'

$od = if ($env:OneDriveCommercial) { $env:OneDriveCommercial } else { $env:OneDrive }
if (-not $od -or -not (Test-Path $od)) { Write-Error "OneDrive folder not found"; exit 1 }

$project  = 'C:\Liminality-Claude-Setup-CHL'
$sessions = Join-Path $env:USERPROFILE '.claude\projects\C--Liminality-Claude-Setup-CHL'
$dest     = Join-Path $od 'Liminality-Claude-Setup-CHL-backup-current'
$log      = Join-Path $dest 'backup.log'

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Add-Content -Path $log -Encoding utf8 -Value ("`r`n===== {0} =====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

# /E every subdir, /XO skip when the destination copy is newer, /FFT+/DST tolerate timestamp
# granularity across filesystems, /R:1 /W:1 so a locked file costs a second rather than minutes.
$common = @('/E', '/XO', '/R:1', '/W:1', '/NFL', '/NDL', '/NP', '/NJH', '/FFT', '/DST',
            '/XD', '.venv', '__pycache__', '.pytest_cache')

$worst = 0
foreach ($job in @(
    @{ From = $project;  To = (Join-Path $dest 'project');         Name = 'project' },
    @{ From = $sessions; To = (Join-Path $dest 'claude-sessions'); Name = 'transcripts + memory' }
)) {
    if (-not (Test-Path $job.From)) {
        Add-Content -Path $log -Encoding utf8 -Value ("  SKIP {0}: source missing" -f $job.Name)
        continue
    }
    $null = & robocopy $job.From $job.To @common 2>&1 | Out-String
    $code = $LASTEXITCODE
    if ($code -gt $worst) { $worst = $code }
    # robocopy: 0 = nothing to do, 1 = files copied, <8 = benign, >=8 = a real failure
    $verdict = if ($code -ge 8) { 'FAILED' } elseif ($code -eq 0) { 'no change' } else { 'copied' }
    Add-Content -Path $log -Encoding utf8 -Value ("  {0,-22} {1} (rc={2})" -f $job.Name, $verdict, $code)
}

if ($worst -ge 8) {
    Add-Content -Path $log -Encoding utf8 -Value "  RESULT: FAILED"
    exit 1
}
Add-Content -Path $log -Encoding utf8 -Value "  RESULT: ok"
exit 0
