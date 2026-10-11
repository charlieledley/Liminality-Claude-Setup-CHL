# 0005 · Claim store: append-only research conclusions with supersession

**Status:** proposed 2026-10-10 (Claude, on Charlie's instruction to implement the
"temporal-memory" note without conflicting with `CLAUDE.md` or memory); Charlie to confirm or
amend. The note is kept at `home/docs/temporal-memory.md`.

## Decision

A `claims` personal skill (`home/skills/claims/claims.py`, standard library only) keeps an
append-only JSONL store of research conclusions. Each entry has an id, a timestamp, the
text, tags, and optionally the id it supersedes with a mandatory reason. Nothing is edited or
deleted. `list` shows live claims, `list --all` everything, `history <id>` the chain through
a claim oldest first with each reason, `md` exports to the Obsidian vault.

- **Store location:** `<repo>/docs/claims.jsonl`, created on first use and tracked with the
  repo (the note asks for a path backed up with the repo). Outside a repo,
  `~/.claude/claims.jsonl`, which the claude-home OneDrive job covers. No project repo was
  touched; the file appears the first time a conclusion is recorded there.
- **Rule in the global `CLAUDE.md`** (the note's step 4), plus the note's standing rule
  "prefer taking the idea without the dependency when the cost is disproportionate".
- **Wiring:** the `checkpoint` skill gains a question 0 (claims) so every milestone records
  or supersedes; `implement-change` and `fix-bug` record at the end; `figure-checker` and
  `reviewer` treat a superseded claim cited as current as a P1 finding.
- **Export, not integration:** `claims.py md` and the `obsidian-sync` skill render every
  store into `Claude/Claims/` in the vault; the vault is never read by the store.

## How it sits beside what already exists

| Record | What goes there | Mutability |
|---|---|---|
| Claim store (`docs/claims.jsonl`) | what the evidence says: a figure, a comparison, a test outcome | append-only; overturned claims are superseded with a reason |
| Decision log (`docs/decisions/`) | choices Charlie makes and conventions the repo adopts | one file per decision; a later decision that reverses one says so in both |
| Memory folder | how to work: tooling, data locations, feedback, corrections of process | updated or deleted when wrong |

The decision log already has supersession at the level of decisions. The claim store adds it
at the level of conclusions, which change far more often (the note's example: four claims in
six hours). A claim that becomes a convention names its decision file in the text, so the two
records point at each other without duplicating.

## Departures from the note

- Ids are `max(id) + 1`, not `len(rows) + 1`, because several sessions can append to one
  store.
- Superseding an already-superseded claim is rejected with the live end of the chain named,
  so chains stay linear and `history` stays readable.
- `history` prints oldest first; the note's reference prints newest first.
- One store per repo instead of one global file, matching where the conclusions are made and
  where they are backed up.

## What was deliberately left out

- Backfilling past conclusions from memory files or the decision log. That would be invented
  history; the store starts with the next conclusion reached.
- Any hook that records claims automatically. A claim needs judgement about what was
  concluded; the checkpoint question is the trigger.
- A graph or database. The note's point.

## What it changes

Every future session records conclusions as it reaches them and checks the store before
citing one. The vault gains a `Claims` section per repo. Done when `history <id>` prints a
readable chain and a conclusion overturned twice is still reconstructible, which the skill's
test run on 2026-10-10 showed.
