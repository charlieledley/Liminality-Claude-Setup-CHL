# Liminality Claude setup (CHL)

How Claude Code is set up for Charlie, and nothing else. Kept under version control so the
setup survives a machine loss, can be reviewed like any other change, and can be rebuilt on
a new PC. Initialised 2026-10-09. The live copy that Claude Code actually reads is `~/.claude`
(the `.claude` folder inside your Windows user folder); this repo holds a mirror of it
under `home/`.

## Scope

In: the global rules, settings, hooks and skills; the scripts that sync and back them up;
a note on the parts of the setup that are not files (app settings, connectors, scheduled
tasks, how the phone reaches the PC), in `docs/setup-notes-<date>.md`; and decisions about
the setup. Out: project work of any kind, project `CLAUDE.md` files, transcripts, memory
folders, and secrets. Those belong to their projects or stay on the machine.

## Layout

| Path | What it holds | Tracked |
|---|---|---|
| `home/CLAUDE.md` | global working rules, read in every project | yes |
| `home/settings.json` | hooks and auto-mode settings | yes |
| `home/skills/` | personal skills: `bbg-pull`, `checkpoint`, `xlsx-report` | yes |
| `home/hooks/` | shell hooks referenced from `settings.json` | yes |
| `tools/sync_setup.py` | copies between `~/.claude` and `home/` | yes |
| `tools/backup-to-onedrive.ps1` | hourly copy of this repo to company OneDrive | yes |
| `tools/backup-claude-home-to-onedrive.ps1` | hourly copy of the whole live `~/.claude` to OneDrive | yes |
| `tools/register-backup-tasks.ps1` | recreates every backup task on a rebuilt machine | yes |
| `docs/setup-notes-<date>.md` | the setup that is not files: app settings, connectors, tasks | yes |
| `docs/decisions/` | numbered decision log | yes |

## Backups

Three, independent of each other. Each OneDrive job only ever adds and overwrites, so a file
deleted on the PC stays in the backup, and each appends a line to a `backup.log` in its
destination folder; open that to see when the job last ran.

1. **GitHub**, remote `origin`: the commit history, pushed when asked.
2. **OneDrive, this repo**: the task "Liminality Claude-Setup-CHL backup to OneDrive" runs
   `tools/backup-to-onedrive.ps1` every hour and copies the working folder and this repo's
   Claude session folder into `Liminality-Claude-Setup-CHL-backup-current\` on company OneDrive.
3. **OneDrive, the live `~/.claude` folder**: the task "Liminality claude-home backup to
   OneDrive" runs `tools/backup-claude-home-to-onedrive.ps1` every hour and copies everything
   Claude Code keeps on this machine, minus caches and key files, into
   `Liminality-claude-home-backup-current\`. This is the one that catches a skill edited in
   place before anyone ran the sync, and the transcripts of every project.

The two project repos keep their own hourly OneDrive jobs. `tools/register-backup-tasks.ps1`
knows all four tasks and recreates them on a new machine.

Project-level `CLAUDE.md` files stay in their own repos. Memory folders, session transcripts
and caches are not part of the setup and are not tracked.

## Keeping the two copies in step

Claude Code reads `~/.claude`, not this repo, so edits made in place (for example a skill
improved mid-session) need copying here before they can be committed. Run from this folder:

```
python tools/sync_setup.py           # list differences, change nothing
python tools/sync_setup.py to-repo   # ~/.claude -> home/, then commit
python tools/sync_setup.py to-home   # home/ -> ~/.claude, on a new machine or after a pull
```

`to-repo` mirrors exactly (a skill deleted live is deleted here; git keeps the history).
`to-home` only adds and overwrites, never deletes. Python 3.12 from the standard install is
enough; there is no virtual environment and nothing to pip-install.

## What must never go in here

Secrets of any kind: API keys, tokens, `.env` files, Bloomberg credentials. The `.gitignore`
blocks the usual names, but check a diff before committing `settings.json`.
