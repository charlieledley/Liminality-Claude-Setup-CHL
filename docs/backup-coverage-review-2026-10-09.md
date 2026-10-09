# Backup coverage review, 2026-10-09

A systematic pass over everything on this machine and in the Claude setup that would hurt to
lose, and what covers it. Written after Charlie asked what else might not be covered.
"OneDrive" means the hourly copy-only jobs described in `setup-notes-2026-10-09.md`.

## Covered

| What | Where it lives | Covered by |
|---|---|---|
| Working folders of the three repos, including gitignored data, caches, exports, `.env` | `C:\Liminality-*` | OneDrive, hourly |
| Commit history of the three repos | `.git` inside each | OneDrive (the `.git` folder is copied) |
| Transcripts and memory, every project and folder-less sessions | `~/.claude/projects` | OneDrive, per-repo jobs and the claude-home job |
| Global rules, settings, skills, hooks | `~/.claude` | this repo, plus OneDrive via the claude-home job |
| Pasted uploads, edit history for undo | `~/.claude/uploads`, `~/.claude/file-history` | OneDrive, claude-home job |
| Scheduled tasks | Windows Task Scheduler | `tools/register-backup-tasks.ps1` |
| App settings, connectors, hook wiring | the app and the claude.ai account | written down in the setup note; re-applied by hand |

## Gaps found

Gaps 1 and 2 were closed later the same day: every put-writing branch was pushed to `mine`,
and swap-spreads got a personal-account `origin` and was pushed. The organisation remote for
put-writing is still unexplained. The rest stand.

1. **The GitHub copy of put-writing is stale, and its shared remote is gone.** The remote
   `origin` (the LiminalityCapital organisation repo) answers "repository not found" on
   2026-10-09: deleted, renamed, or the stored login no longer has access. The personal remote
   `mine` works but last received a push on 2026-09-27; the working branch has had 61 commits
   since, through the F2.1 pin of 2026-10-06. Two branches (`charlie-sandbox`,
   `transfer/hedge-ladders-2026-10-05`) have never been pushed anywhere, and 29 files are
   uncommitted. Until pushed, the only copy of twelve days of work is OneDrive.
2. **Swap-spreads has no GitHub copy at all.** Thirteen commits and seven uncommitted files,
   OneDrive only.
3. **The PostgreSQL database is outside every backup here.** Put-writing reads its vol
   surfaces, swap curves, CPI series and, importantly, the saved strategies (the
   `dashboard_saved_strategies` table that holds F2.0/F2.1 as saved) from an internal server
   that is not this PC. Whoever runs that server owns its backup; nothing in this review can
   confirm one exists. The shipped hedge caches in the repo mean the dashboard can run without
   it, but the saved strategies and the surfaces could not be rebuilt from this machine.
4. **Everything off-machine goes to one place.** All four jobs write to the same company
   OneDrive account. Copy-only protects against deletion, but a file corrupted on the PC is
   copied over its backup on the next run because the copy is newer. OneDrive's own version
   history is the safety net there; it has not been checked, and only put-writing has a frozen
   dated snapshot (`Liminality-backtest-backup-2026-09-22`, before F2). Swap-spreads and the
   Claude folder have none.
5. **A 682 MB folder `Claude_Backup` on the Desktop, last touched 2026-09-17**, holds a copy
   of the desktop app's data from an earlier recovery. The Desktop is not synced to OneDrive,
   so this exists on this disk only. Probably superseded; Charlie to say whether it can go
   into the OneDrive snapshot folder or be deleted.
6. **The database password lives in exactly one backed-up place**, the `.env` inside the
   put-writing OneDrive copy, by design. A password-manager entry would be the proper second
   home. Not a Claude matter.

## Deliberately not covered, and why

- `~/.claude.json` and the Git Credential Manager store: the Claude and GitHub logins. Signing
  in again on a new machine is the restore.
- Python virtual environments: rebuilt from each repo's `requirements.txt`, with `blpapi` from
  Bloomberg's package index. Put-writing's second environment `.venv-deck` has no requirements
  file recorded; worth adding one there.
- Account-side Claude items (connectors, plugins, claude.ai memory and projects): not files.
  The setup note lists the connectors so they can be re-enabled.
- Caches, shell snapshots, session key files: regenerable or sensitive.

## Suggested order of fixes

1. ~~Push put-writing to `mine`~~ done 2026-10-09; still to sort out what happened to `origin`.
2. ~~Create the GitHub repos for swap-spreads and this repo~~ done 2026-10-09.
3. Ask whoever runs the PostgreSQL server how it is backed up, and consider a periodic dump
   of the saved-strategies table into the put-writing repo.
4. Add a monthly dated snapshot alongside each `-current` folder, or confirm OneDrive version
   history is on for the account.
5. Decide the fate of `Desktop\Claude_Backup`.
