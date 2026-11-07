<#
.SYNOPSIS
  Refresh the Obsidian vault's Claude folder from the sessions, memory and setup on this PC.

.DESCRIPTION
  Runs the obsidian-sync skill (~/.claude/skills/obsidian-sync/sync_claude_to_obsidian.py)
  hourly from the Windows scheduled task "Liminality Obsidian vault sync", so the vault stays
  current while sessions sit open for days (the SessionEnd hook only fires when a session
  closes). Unchanged transcripts are skipped, so a routine run takes a few seconds.

  Appends one line per run to obsidian-sync.log next to the claude-home backup log on
  OneDrive, so every scheduled job on this machine logs in the same place.

.NOTES
  Reads the vault path from Obsidian's own config (%APPDATA%\obsidian\obsidian.json). Needs
  Python 3.12 on the PATH. Never deletes anything in the vault except a session note whose
  title changed, which it renames.
#>

$ErrorActionPreference = 'Stop'

$od  = if ($env:OneDriveCommercial) { $env:OneDriveCommercial } else { $env:OneDrive }
$log = if ($od -and (Test-Path $od)) { Join-Path (Join-Path $od 'Liminality-claude-home-backup-current') 'obsidian-sync.log' } else { Join-Path $env:TEMP 'obsidian-sync.log' }
$script = Join-Path $env:USERPROFILE '.claude\skills\obsidian-sync\sync_claude_to_obsidian.py'

New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

if (-not (Test-Path $script)) {
    Add-Content -Path $log -Encoding utf8 -Value "$stamp  SKIP: sync script missing at $script"
    exit 0
}

$env:PYTHONIOENCODING = 'utf-8'
$out = & python $script 2>&1 | Out-String
$code = $LASTEXITCODE
$line = ($out -split "`r?`n" | Where-Object { $_ -match '^Synced ' } | Select-Object -Last 1)
if (-not $line) { $line = ($out.Trim() -split "`r?`n" | Select-Object -Last 1) }
$verdict = if ($code -eq 0) { 'ok' } else { "FAILED (rc=$code)" }
Add-Content -Path $log -Encoding utf8 -Value ("{0}  {1}  {2}" -f $stamp, $verdict, $line)
exit $code
