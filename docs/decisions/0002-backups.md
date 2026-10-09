# 0002 · Backups: GitHub remote plus hourly OneDrive copy

**Status:** done 2026-10-09. OneDrive job registered; GitHub remote `origin` added and pushed
the same day. Owner: Charlie's personal GitHub account, private, repo name corrected to
`Liminality-Claude-Setup-CHL` after a first push under a mistyped name.

## Decision

Two independent backups, matching the put-writing repo and the swap-spreads OneDrive job:

- **OneDrive.** `tools/backup-to-onedrive.ps1` is the same script as in the other two repos
  with the paths changed. The Windows scheduled task "Liminality Claude-Setup-CHL backup to
  OneDrive" runs it hourly as the logged-in user, start-when-available, one instance at a time,
  30-minute limit. Destination is `Liminality-Claude-Setup-CHL-backup-current\` in the company
  OneDrive, with `project\` and `claude-sessions\` beneath it. Copy-only, never deletes.
- **GitHub.** Remote `origin`, private, in Charlie's personal account (chosen 2026-10-09 over
  the LiminalityCapital organisation; the organisation's put-writing repo was found
  unreachable the same day, see `docs/backup-coverage-review-2026-10-09.md`). Push on
  request only.

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
