# 0004 · Agent orchestration: subagents, workflow skills, enforcing hooks

**Status:** proposed 2026-10-10 (Claude, on Charlie's instruction to implement the "Claude Code
Agent Orchestration Guide" without conflicting with `CLAUDE.md` or memory); Charlie to confirm
or amend. The guide itself is kept at `home/docs/claude-code-agent-orchestration-guide.md`.

## Decision

Implement the guide at user level (`~/.claude`), adapted to research repos, with nothing added
to the project repos. The global `CLAUDE.md` gains a "Working with agents" section; the
existing rules win wherever the guide overlaps them.

| Guide section | What was done | Adaptation or reason |
|---|---|---|
| 2, 40: per-project `.claude/agents`, `skills`, `rules` | Agents and skills live in `~/.claude` only | `.claude/` is gitignored and per machine in both project repos; reusable things are personal-scope by standing rule (memory `output-template-workflow`); repo-specific rules stay in each repo's `CLAUDE.md`, so no `.claude/rules/` |
| 3, 41: CLAUDE.md template, Definition of Done | Short "Working with agents" section and a Definition of Done added to the global file | The project files already hold the architecture and conventions; the guide's SaaS template does not apply. Done means: scope as asked, pins run with the project Python and reported, provenance on every figure, diff inspected, nothing committed unless asked, independent review, file card, checkpoint |
| 5: specialised subagents | `researcher`, `architect`, `implementer`, `test-engineer`, `reviewer`, `security-reviewer`, plus `figure-checker` | `figure-checker` replaces the guide's performance reviewer: in these repos the thing most likely to be wrong is a number's construction. Each agent carries the conventions that have bitten (total return, calendar-year attribution, window stated, costs charged, beta basis, PeriodIndex, anchor). `researcher` runs on Sonnet (cheap breadth, guide §26); the rest inherit the session model |
| 6, 7, 20, 25, 26, 35: delegate and parallelise research | Rule in `CLAUDE.md`; `implement-change` and `fix-bug` launch researchers in parallel | As written |
| 8, 9: agent teams | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `settings.json`; rule says teams only for substantial independent parts that must talk | Experimental per the docs; can be turned off by setting the value to `0` |
| 10: worktrees | Not adopted as the default | Sessions share one working tree here, and worktrees lack `.venv`, caches and `.env` (memory `worktrees-miss-ignored-files`). Rule: non-overlapping file ownership instead; worktrees for isolated branch work only |
| 11, 21, 22, 23: contracts, structured returns, cited evidence, ownership | Built into every agent's return format and the skills' delegation steps | As written |
| 12, 13, 14, 29: explore, plan, implement, verify, adversarial review | `implement-change` skill | Verification here is pytest pins and a rendered deck, not typecheck and lint; review includes figures and investor-facing language |
| 15, 30: competing hypotheses for bugs | `fix-bug` skill | Adds the case where the "bug" is a convention choice, which goes to Charlie as a decision |
| 16: hooks for policy | `guard-bash.py` (PreToolUse on Bash and PowerShell), `check-python-syntax.py` (PostToolUse on edits), SessionEnd Obsidian sync | Formatter hook not adopted: no formatter in the project venvs, and reformatting shared files would churn a working tree used by several sessions. Test-before-completion hook not adopted: the pins take 30 to 100 seconds and need the database; the pre-commit hook already runs them on commit |
| 17: MCP | No change | Connectors are set in the claude.ai account (setup note 2026-10-09) |
| 18: skills for repeated workflows | `implement-change`, `fix-bug`, `adversarial-review` | Alongside the existing `checkpoint`, `xlsx-report`, `bbg-pull`, `obsidian-sync` |
| 19, 36: dynamic workflows | No change | The built-in Workflow tool exists; the guide's scale has not arisen |
| 27, 42: interview the problem, humans at decision points | Rule: ask only method-or-number questions, in one batch | Consistent with "ask before working around a data gap" |
| 37: agent view | Not applicable | Desktop app, no `claude` on the PATH |
| 43: permission strategy | Read-only git and pytest commands allowed globally; everything destructive goes through the guard hook | Deny rules are advisory per the docs; the hook enforces |
| 45: progressive autonomy | Recorded here as the operating principle | Autonomy grows with pins and reviews, not trust |

## What the guard hook blocks

Force pushes, pushes to any remote outside Charlie's personal GitHub (resolved through
`git remote get-url`), `--no-verify`, `git reset --hard`, whole-tree `checkout`/`restore .`,
`git clean -f`, `stash drop`, forced branch deletes, recursive deletes outside Temp or scratch
folders, and `pip install` into a project `.venv` without `--target`. A blocked command is
reported to Claude as a question for Charlie. It is a seat belt, not a security boundary.

## What was deliberately left out

- Per-repo `.claude/agents` or `.claude/rules`: see the table.
- A formatter or a test-on-stop hook: see the table.
- Changes to either project `CLAUDE.md`: nothing in the guide contradicts them, and the global
  section applies in both.
- Pinning the guide's SaaS-specific advice (typecheck, lint, migrations, tenant isolation).

## What it changes

Every future session reads the new `CLAUDE.md` section, can delegate to the seven agents, can
run the three skills, and is subject to the hooks. The agents, skills, hooks and the guide are
mirrored in `home/` and synced with `tools/sync_setup.py`. The Obsidian vault mirrors the agents
and the reference documents too (`obsidian-sync` skill).
