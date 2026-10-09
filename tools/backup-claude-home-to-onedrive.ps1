<#
.SYNOPSIS
  Incremental backup of the whole live Claude Code folder (~/.claude) to company OneDrive.

.DESCRIPTION
  Copies new and changed files from <user>\.claude into
  <OneDrive>\Liminality-claude-home-backup-current\claude-home\. Runs hourly from the Windows
  scheduled task "Liminality claude-home backup to OneDrive".

  This covers everything the per-repo jobs do not: the live global CLAUDE.md, settings, skills
  and hooks (regardless of whether tools/sync_setup.py has been run), the transcripts and
  memory of every project including sessions started without a folder, pasted uploads, and
  the edit history Claude keeps for undo. It overlaps the per-repo jobs on their own
  transcript folders; that duplication is deliberate and cheap.

  COPY-ONLY, NEVER DELETE. No /MIR or /PURGE, so a file that disappears from this machine
  stays in the backup.

.NOTES
  Excluded: cache, shell-snapshots, debug, statsig, session-env (regenerable machine state),
  sessions (holds per-session key files), __pycache__, and any *.key file anywhere.
#>

$ErrorActionPreference = 'Stop'

$od = if ($env:OneDriveCommercial) { $env:OneDriveCommercial } else { $env:OneDrive }
if (-not $od -or -not (Test-Path $od)) { Write-Error "OneDrive folder not found"; exit 1 }

$src  = Join-Path $env:USERPROFILE '.claude'
$dest = Join-Path $od 'Liminality-claude-home-backup-current'
$to   = Join-Path $dest 'claude-home'
$log  = Join-Path $dest 'backup.log'

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Add-Content -Path $log -Encoding utf8 -Value ("`r`n===== {0} =====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

if (-not (Test-Path $src)) {
    Add-Content -Path $log -Encoding utf8 -Value "  SKIP claude-home: source missing"
    Add-Content -Path $log -Encoding utf8 -Value "  RESULT: ok"
    exit 0
}

# /E every subdir, /XO skip when the destination copy is newer, /FFT+/DST tolerate timestamp
# granularity across filesystems, /R:1 /W:1 so a locked file costs a second rather than minutes.
$args = @('/E', '/XO', '/R:1', '/W:1', '/NFL', '/NDL', '/NP', '/NJH', '/FFT', '/DST',
          '/XD', 'cache', 'shell-snapshots', 'debug', 'statsig', 'session-env', 'sessions', '__pycache__',
          '/XF', '*.key')

$null = & robocopy $src $to @args 2>&1 | Out-String
$code = $LASTEXITCODE
# robocopy: 0 = nothing to do, 1 = files copied, <8 = benign, >=8 = a real failure
$verdict = if ($code -ge 8) { 'FAILED' } elseif ($code -eq 0) { 'no change' } else { 'copied' }
Add-Content -Path $log -Encoding utf8 -Value ("  {0,-22} {1} (rc={2})" -f 'claude-home', $verdict, $code)

if ($code -ge 8) {
    Add-Content -Path $log -Encoding utf8 -Value "  RESULT: FAILED"
    exit 1
}
Add-Content -Path $log -Encoding utf8 -Value "  RESULT: ok"
exit 0
