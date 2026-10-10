# Claude setup notes, 2026-10-10

Supplements `setup-notes-2026-10-09.md`, which stays valid for the machine, app settings,
connectors, backup tasks and repositories. The sections below replace that note's "Hooks"
section and add what was set up on 2026-10-10 (decision 0004 and the Obsidian sync).

## Hooks

Wired in `home/settings.json`, scripts in `home/hooks/` and `home/skills/`, installed at
`~/.claude/`. Hook commands run under Git Bash and reference `$HOME`.

| Event | Matcher | Script | What it does |
|---|---|---|---|
| SessionStart | `compact` | `hooks/after-compaction-reminder.sh` | reminds the session to re-read rules, decisions and memory after a compaction |
| PreToolUse | `Bash\|PowerShell` | `hooks/guard-bash.py` | blocks force pushes, pushes outside Charlie's personal GitHub, `--no-verify`, whole-tree discards, recursive deletes outside scratch, installs into a project `.venv` |
| PostToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit` | `hooks/check-python-syntax.py` | parses an edited Python file and reports a syntax error or conflict marker at once |
| SessionEnd | all | `skills/obsidian-sync/sync_claude_to_obsidian.py --quiet` | refreshes the Obsidian vault (55-second budget; a routine run takes a few seconds) |

To disable one temporarily, remove its entry from `settings.json` in `~/.claude` (then
`to-repo` when committing the change), or ask Claude to.

## Environment

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `settings.json` enables agent teams (experimental
in Claude Code; set to `0` to turn off).

## Subagents and workflow skills

Seven user-level agents in `~/.claude/agents/`, three workflow skills in `~/.claude/skills/`
(`implement-change`, `fix-bug`, `adversarial-review`), the global rule section "Working with
agents" in `CLAUDE.md`, and the source guide in `~/.claude/docs/`. Decision 0004 maps every
section of the guide to what was adopted, adapted or left out.

## Obsidian

Vault: `OneDrive - Liminality Capital LP\Obsidian Vault` (registered in the Obsidian app on
2026-10-10). The `obsidian-sync` skill mirrors every Claude Code and Cowork transcript, the
memory folders, agents, skills, reference docs and the global rules into `Claude/` inside the
vault, as linked notes. Runs at session end through the hook, or on `/obsidian-sync`.
claude.ai web chats are not on the PC; they arrive through the account's data export, which
the skill's importer reads.
