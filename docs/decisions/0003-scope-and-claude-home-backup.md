# 0003 · Scope: Claude setup only, plus a whole-folder backup of ~/.claude

**Status:** decided 2026-10-09 (Charlie).

## Decision

1. **This repo is purely about how Claude Code is set up for Charlie**, on this PC and any
   device that reaches it. It holds the mirror of `~/.claude` (`home/`), the sync and backup
   scripts, a setup note for the parts that are not files (`docs/setup-notes-<date>.md`), and
   decisions about the setup. No project work, no project `CLAUDE.md`, no transcripts, no
   memory, no secrets.
2. **A fourth backup job copies the whole live `~/.claude` folder** to OneDrive hourly,
   "Liminality claude-home backup to OneDrive", script `tools/backup-claude-home-to-onedrive.ps1`.
   Before this, the global rules, settings, the `checkpoint` and `xlsx-report` skills, pasted
   uploads, the edit history and the transcripts of folder-less sessions had no backup at all,
   and the mirror in `home/` is only as fresh as the last sync. The job excludes caches and
   key files.
3. **`tools/register-backup-tasks.ps1` is the record of every backup task** on the machine,
   so a rebuild recreates them with one command. The per-repo jobs stay in their repos; this
   script only knows their names and script paths.

## What was deliberately left out

- Replacing the per-repo OneDrive jobs with the claude-home job. They back up the project
  folders themselves, which the claude-home job does not touch, so they stay.
- De-duplicating the transcript folders that both the per-repo jobs and the claude-home job
  copy. About 220 MB of OneDrive, not worth the complexity.
- Anything phone-side: Remote Control drives sessions on this PC, so there is nothing there.

## Alternatives considered

A note in the README saying "run the sync after editing a skill" would be cheaper than a
fourth job, but the gap it closes is precisely the one that depends on remembering.
