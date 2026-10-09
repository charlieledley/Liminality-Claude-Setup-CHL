# CLAUDE.md — Liminality Claude setup (CHL)

Read this first in every session in this repo. The personal rules are in the global
`~/.claude/CLAUDE.md`, which this repo mirrors at `home/CLAUDE.md`.

## What this repo is

A version-controlled mirror of Charlie's `~/.claude` folder: global `CLAUDE.md`,
`settings.json`, personal skills and hooks. See `README.md` for the layout and the sync
commands. Decisions go in `docs/decisions/`.

## Rules

- **`~/.claude` is the live copy; `home/` is the record.** Claude Code never reads `home/`.
  After editing anything under `home/`, run `python tools/sync_setup.py to-home` so the change
  takes effect; after editing a skill in place, run `to-repo` before committing. Check with
  the no-argument form first.
- When a skill changes, update its `SKILL.md` and this repo in the same session, and say in
  the commit message which skill changed and why. Other sessions on other repos pick the
  change up only through `~/.claude`.
- Never commit secrets. `settings.json` is tracked; read its diff before staging it.
- Commit only when asked.

## Git and backups

- `main` is the integration branch. Several Claude sessions may share this working tree:
  before `git add`, run `git status` and stage only the files you changed, by path.
- Remote `origin` is the GitHub backup (see `docs/decisions/0002-backups.md` for which
  account owns it). **Never push without being asked.**
- Backup: `tools/backup-to-onedrive.ps1` runs hourly from the Windows scheduled task
  "Liminality Claude-Setup-CHL backup to OneDrive" and copies the repo (minus `.venv` and
  caches) and this project's Claude transcript and memory folder into
  `OneDrive - Liminality Capital LP\Liminality-Claude-Setup-CHL-backup-current\`. Copy-only,
  never deletes. Log is `backup.log` in that folder. Set up 2026-10-09, mirroring the
  put-writing and swap-spreads jobs.
