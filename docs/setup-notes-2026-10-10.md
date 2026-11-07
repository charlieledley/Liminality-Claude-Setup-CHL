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

## Backups (change on 2026-10-11)

The claude-home task now also copies two subfolders of the desktop app's own data folder,
`%APPDATA%\Claude`, into `Liminality-claude-home-backup-current\app-data\`:
`claude-code-sessions` (the session index: titles, archive flags, the map from app session to
transcript file) and `local-agent-mode-sessions` (Cowork chat transcripts), minus plugin
bundles, caches and key files. The app folder is wiped by a reinstall (2026-09-22) and was
covered by nothing before. Same task, same script.

A fifth scheduled task, "Liminality Obsidian vault sync", runs `tools/sync-obsidian-vault.ps1`
hourly (registered 2026-10-11) so the vault stays current while sessions sit open; the
SessionEnd hook only fires when a session closes. It logs to `obsidian-sync.log` beside the
claude-home backup log. `register-backup-tasks.ps1` knows all five.

Since 2026-11-06 the same hourly task also runs `tools/sync_setup.py to-repo`, so `home/` always
mirrors the live `~/.claude` (it never commits), and logs how many paths the repo has
uncommitted. A SessionStart hook, `hooks/setup-repo-drift.sh`, prints that count into every new
session so the drift is noticed. Reason: three weeks of live skill and rule edits sat unmirrored
and uncommitted in October because no session ran the mirror step.
Obsidian is installed on this PC (2026-10-10); its vault is in company OneDrive, so OneDrive
mirrors it, and every note under `Claude/` regenerates from the transcripts.

## Claim store (temporal memory)

The `claims` skill (`~/.claude/skills/claims/claims.py`) keeps an append-only record of
research conclusions per repo at `docs/claims.jsonl`, with supersession and a mandatory
reason. The global rule, the checkpoint skill and the review agents use it; decision 0005 has
the details and how it sits beside the decision logs and memory. The source note is in
`~/.claude/docs/temporal-memory.md`.

## Obsidian

Vault: `OneDrive - Liminality Capital LP\Obsidian Vault` (registered in the Obsidian app on
2026-10-10). The `obsidian-sync` skill mirrors every Claude Code and Cowork transcript, the
memory folders, agents, skills, reference docs and the global rules into `Claude/` inside the
vault, as linked notes. Runs at session end through the hook, or on `/obsidian-sync`.
claude.ai web chats are not on the PC; they arrive through the account's data export, which
the skill's importer reads.

## Scheduled tasks in the desktop app (change on 2026-10-15)

The app's own scheduler (the "Scheduled" section of the sidebar) keeps one registry per
account, org and mode: `%APPDATA%\Claude\local-agent-mode-sessions\<acct>\<org>\scheduled-tasks.json`
for tasks created in a Cowork chat, whose prompts live under `C:\Users\charlie\Claude\Scheduled\`,
and `%APPDATA%\Claude\claude-code-sessions\<acct>\<org>\scheduled-tasks.json` for tasks created
from a Claude Code session, whose prompts live under `~/.claude/scheduled-tasks/<id>/SKILL.md`.
A run is a new session of the same mode; a Claude Code task runs in the working folder of the
session that created it (the registry's `cwd`), so tasks are created from a session opened in
the folder they should run in. Runs happen only while the app is open. The scheduled-tasks
tools in a session see only that mode's registry.

Cowork cannot run its Linux sandbox on this PC: the machine is a VMware virtual machine
without nested virtualization (the app reports "Claude's workspace requires hardware
virtualization"), so Cowork sessions have no shell or file tools, though browsers, search and
connectors work. Enabling it is a per-VM option on the VMware host, not a BIOS setting here.

The two daily digests (Daily Tab Digest 06:00, Daily Candidate Watch 07:00) were created in
Cowork on 2026-10-12 and never fired. On 2026-10-15 they were recreated as Claude Code tasks
from a session in `C:\Liminality-digests`, which holds the prompt sources (`prompts/`), a
README and the daily output files. Both prompts now use Claude in Chrome only, the Bash tool
with Python for the email transform, and a catch-up window that runs from the previous
edition's date. The Cowork copies were still enabled in the Cowork registry at the time of
writing and are disabled from the Scheduled sidebar; nothing here can remove them. Further
tasks (topic watch, schedule summary, inbox triage) were added to the same folder the same
day from that session.
