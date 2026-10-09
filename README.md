# Liminality Claude setup (CHL)

Charlie's personal Claude Code configuration, kept under version control so it survives a
machine loss, can be reviewed like any other change, and can be installed on a second PC.
Initialised 2026-10-09. The live copy that Claude Code actually reads is `~/.claude`
(the `.claude` folder inside your Windows user folder); this repo holds a mirror of it
under `home/`.

## Layout

| Path | What it holds | Tracked |
|---|---|---|
| `home/CLAUDE.md` | global working rules, read in every project | yes |
| `home/settings.json` | hooks and auto-mode settings | yes |
| `home/skills/` | personal skills: `bbg-pull`, `checkpoint`, `xlsx-report` | yes |
| `home/hooks/` | shell hooks referenced from `settings.json` | yes |
| `tools/sync_setup.py` | copies between `~/.claude` and `home/` | yes |
| `docs/decisions/` | numbered decision log | yes |

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
