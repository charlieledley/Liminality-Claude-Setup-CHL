#!/usr/bin/env bash
# SessionStart hook (startup and resume). Prints one line when the Claude setup repo has work
# that is not yet committed, so any new session, in any folder, knows the GitHub copy of the
# setup is behind. The hourly "Liminality Obsidian vault sync" task mirrors ~/.claude into the
# repo; this is the part that makes the drift visible. Whatever this prints is added to the
# model's context. Silent when the repo is clean or missing. Added 2026-11-06.
repo="/c/Liminality-Claude-Setup-CHL"
[ -d "$repo/.git" ] || exit 0
n=$(git -C "$repo" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
[ "$n" -gt 0 ] || exit 0
echo "Setup repo note: C:\\Liminality-Claude-Setup-CHL has $n uncommitted path(s), so the GitHub copy of the Claude setup (rules, skills, hooks, agents) is behind the live ~/.claude folder. If Charlie asks for a commit there, stage by path, check the settings diff for secrets, and push to origin (his personal GitHub). Do not commit unasked."
