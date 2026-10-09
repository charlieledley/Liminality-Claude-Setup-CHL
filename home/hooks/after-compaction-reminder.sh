#!/usr/bin/env bash
# SessionStart hook, matcher "compact". Runs after the context is compacted.
# Whatever this prints is added to the model's context.
cat <<'MSG'
Context was just compacted. Before asserting anything about history, quoting a figure, or saying that something does not exist: re-read the project CLAUDE.md, the decision log (docs/decisions/ if the repo has one) and MEMORY.md in the memory folder. Check git log and ~/.claude/skills before concluding work does not exist; several sessions run on the same repo. If the checkpoint skill has not been run since the last milestone, run it now, because anything not already written to a file may have been lost in the compaction.
MSG
