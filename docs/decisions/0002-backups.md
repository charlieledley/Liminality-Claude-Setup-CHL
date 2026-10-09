# 0002 · Backups: GitHub remote plus hourly OneDrive copy

**Status:** OneDrive half done 2026-10-09 (Claude, at Charlie's request). GitHub half waiting
on Charlie creating the repository; owner to be recorded here once chosen.

## Decision

Two independent backups, matching the put-writing repo and the swap-spreads OneDrive job:

- **OneDrive.** `tools/backup-to-onedrive.ps1` is the same script as in the other two repos
  with the paths changed. The Windows scheduled task "Liminality Claude-Setup-CHL backup to
  OneDrive" runs it hourly as the logged-in user, start-when-available, one instance at a time,
  30-minute limit. Destination is `Liminality-Claude-Setup-CHL-backup-current\` in the company
  OneDrive, with `project\` and `claude-sessions\` beneath it. Copy-only, never deletes.
- **GitHub.** Remote `origin`, private. Owner: _to be filled in_ (recommended: the
  LiminalityCapital organisation, where the put-writing repo's `origin` lives, so that a
  colleague's setup repo can sit beside it; the alternative is Charlie's personal account).
  Push on request only.

## What was deliberately left out

- **A dated frozen snapshot** like `Liminality-backtest-backup-2026-09-22`. That one was taken
  during a recovery; nothing here warrants it yet.
- **A backup of `~/.claude` itself.** The repo's `home/` folder already is that copy, and the
  OneDrive job copies the repo.

## State of the sibling repos on 2026-10-09

| Repo | GitHub remote | OneDrive task |
|---|---|---|
| put-writing | `origin` (LiminalityCapital), `mine` (personal), `dashboard-v2` | hourly, healthy |
| swap-spreads | none | hourly, healthy, since 2026-10-04 |
| this repo | pending | hourly, from 2026-10-09 |
