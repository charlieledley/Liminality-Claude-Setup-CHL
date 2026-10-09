# 0001 · Repo layout and sync model

**Status:** proposed 2026-10-09 (Claude, at initialisation); Charlie to confirm or amend.

## Decision

The repo is a mirror of `~/.claude`, not a replacement for it. Claude Code keeps reading the
live folder; this repo exists so the setup is backed up, reviewable and installable elsewhere.

- `home/` mirrors the synced part of `~/.claude`: `CLAUDE.md`, `settings.json`, `skills/`,
  `hooks/`. Same relative paths, so a diff between the two reads directly.
- `tools/sync_setup.py` is the only way files move between the two. It has three modes:
  show differences (default), `to-repo` (exact mirror of the live folder, deletions included),
  `to-home` (adds and overwrites, never deletes).
- Standard-library Python only, no virtual environment, nothing to install.
- `docs/decisions/` for this log. `main` is the integration branch. No remote until Charlie
  names one.

## What was deliberately left out

- **Memory folders** (`~/.claude/projects/...`). They are per-repo and per-machine, contain
  working notes rather than configuration, and change every session.
- **Session transcripts, caches, backups, policy files.** Machine state, not setup.
- **A symlink or junction** from `~/.claude` into the repo in place of copying. It would remove
  the sync step, but Windows junctions behave differently across tools and a broken one takes
  every skill offline at once. Revisit if the sync step proves annoying.
- **Project `CLAUDE.md` files.** They belong to their repos.
- **Tests.** Nothing here produces a figure.

## Alternatives considered

Committing `~/.claude` itself as a repo would avoid the mirror, but it would put transcripts,
caches and memory under version control and the `.gitignore` would have to exclude most of
the folder. A separate repo with an explicit sync is simpler to reason about.
