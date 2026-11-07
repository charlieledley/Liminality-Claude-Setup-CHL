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

# Added 2026-11-06: keep the setup repo's mirror of ~/.claude current and say when the repo has
# drifted from GitHub. Three weeks of live skill and rule edits once sat unmirrored and
# uncommitted because no session ran the mirror step. This copies live -> home/ (never commits)
# and logs how many paths the repo has uncommitted, so the hourly repo backup carries the latest
# skills and the next session's start-up hook can report the drift.
$repo = 'C:\Liminality-Claude-Setup-CHL'
$syncTool = Join-Path $repo 'tools\sync_setup.py'
if (Test-Path $syncTool) {
    $mirror = & python $syncTool to-repo 2>&1 | Out-String
    $copied = ($mirror -split "`r?`n" | Where-Object { $_ -match '^\s+(copied|removed)\s' }).Count
    $dirty = (& git -C $repo status --porcelain 2>$null | Measure-Object -Line).Lines
    $msg = if ($copied -gt 0) { "mirrored $copied changed file(s) from ~/.claude into home/" } else { "mirror already current" }
    $msg += if ($dirty -gt 0) { "; setup repo has $dirty uncommitted path(s), commit when convenient" } else { "; setup repo clean" }
    Add-Content -Path $log -Encoding utf8 -Value ("{0}  setup-repo  {1}" -f $stamp, $msg)
}
exit $code
