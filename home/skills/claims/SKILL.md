---
name: claims
description: Append-only store of research conclusions with supersession (temporal memory). Record a conclusion when it is reached; when evidence overturns it, add the new one with --supersedes and a reason; never edit or delete. Use whenever an analysis reaches or overturns a conclusion, before citing an earlier conclusion (check it is still live), at every checkpoint, and when Charlie types /claims. Exports to the Obsidian vault.
argument-hint: add "<conclusion>" | list [--all] | history <id> | md
---

# Claims (temporal memory)

Standard memory stores facts and has no notion of a fact being overturned, which is the
normal state of affairs in research. This store keeps the line of reasoning: every
conclusion, every reversal, and the reason for each. Design from the temporal-memory note in
`~/.claude/docs/`. Standard library only.

## Where the store is

`<repo>/docs/claims.jsonl`, created on first use, tracked with the repo. Outside a repo it is
`~/.claude/claims.jsonl`. `python ~/.claude/skills/claims/claims.py where` prints the path.
Run from the repo folder so the right store is found.

## The two rules

1. **When a conclusion is reached, record it.** One line, with the figure and its construction
   (window, basis, script), tagged with the topic:
   ```
   python "%USERPROFILE%\.claude\skills\claims\claims.py" add "12m expiry earns 14% more gross than 6m, 2007-01-02 to 2026-08-25, hedge_ladder_expiry.py; decision 0006" --tag hedge --tag expiry
   ```
2. **When a conclusion is overturned, supersede it, never correct it.** `--supersedes <id>`
   is rejected without `--reason`. The wrong conclusion and why it fell stay in the record:
   ```
   python "%USERPROFILE%\.claude\skills\claims\claims.py" add "candidate does not dominate Buffer on SPX: its extra return is a 38% larger rates budget" --supersedes 12 --reason "compared at different hedge budgets; equal-budget rerun 2026-09-18"
   ```
   Never edit or delete an entry. A chain stays linear: supersede the live end of a chain,
   and the script says which one that is if you pick a retired id.

## Recall

Before citing an earlier conclusion, run `list` (live claims only). `list --all` shows what
was retired and by which claim. `history <id>` prints the whole chain through a claim, oldest
first, with each reason. `figure-checker` and `reviewer` treat a superseded claim quoted as
current as a P1 finding.

## What is a claim, and what is not

- A **claim** is what the evidence says: a figure, a comparison, a test outcome, a reading of
  the data. Claude records these as it works.
- A **decision** is a choice Charlie makes or a convention the repo adopts. Those stay in
  `docs/decisions/`. A claim that becomes one names its decision file in the text.
- **Memory files** hold how-to-work facts, tooling and feedback, not research results.

## Export

`md` writes `Claude/Claims/Claims - <repo>.md` in the Obsidian vault: live claims, each line
of reasoning as a chain, and the full table. The `obsidian-sync` skill does the same for every
repo's store, so a session-end sync keeps the vault current. The vault is never a dependency.
