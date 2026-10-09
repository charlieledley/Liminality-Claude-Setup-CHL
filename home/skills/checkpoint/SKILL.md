---
name: checkpoint
description: Review the session so far for anything that should outlive the chat - decisions that changed a number or convention, facts and corrections worth a memory, output templates worth a skill, rules for CLAUDE.md, figures no test pins - then write the low-risk items to disk and list the rest for Charlie. Run at the end of every workstream milestone and before closing a session, or when Charlie types /checkpoint. Do not wait for compaction.
---

# Checkpoint

Chat history compacts and is lost. Files are not. This skill is the pass that moves the
durable parts of a session into files before that happens. It runs at milestones, not at
compaction, because by the time compaction is near there is no room left to do the review.

## Scope

Review everything since the last checkpoint. The previous checkpoint's report is visible in
the conversation if one was run; if none is visible, review the whole visible conversation
and say so in the report. Anything already lost to an earlier compaction cannot be recovered
here; do not guess at it.

## The five questions

Go through each one against the session. Be selective. The memory folder already has thirty
entries; a checkpoint that adds five more every time makes the index useless.

1. **Decisions.** Did anything change a number, a method or a convention? A window, an anchor
   date, a cost assumption, a benchmark, a fallback, a naming choice. Did Charlie approve or
   reject an approach? These go in the repo's decision log if it has one (`docs/decisions/`).
2. **Memories.** Did we learn something about the repo, the data, the tooling or how Charlie
   wants to work that is not derivable from the code, the git history or `CLAUDE.md`? Did
   Charlie correct something, or confirm an approach after a wrong turn? Corrections and the
   reason behind them are the highest-value memories.
3. **Skills.** Was an output template, a formatter, a data-pull recipe or a checklist built
   that will be wanted again in another project? Was a skill used in a way that exposed a gap
   in it?
4. **Rules.** Did a mistake happen that a one-line rule in `CLAUDE.md` would have prevented?
   Global (`~/.claude/CLAUDE.md`) if it applies to every project, project if it is about this
   repo. A rule is for something that has actually bitten, not something that might.
5. **Tests.** Was a figure quoted that will be quoted again, and does any test pin it? Was a
   bug fixed that a test would catch if it came back?

## What to write now

Decisions and memories are written immediately. They are files on disk that Charlie can read,
and both live somewhere visible (the repo, or the memory folder with its index), so a bad one
is easy to spot and delete.

**Decision file.** `docs/decisions/NNNN-<what-it-decides>.md`, next number in sequence, status
line with the date and who decided (Charlie, or "proposed (Claude); Charlie to confirm").
Match the style of the existing files: what was decided, the alternatives, what it changes,
which figures it affects. If the folder has a `README.md` index, add a line. If the repo has
no decision log, create `docs/decisions/` with the first file and a two-line README.

**Memory file.** One fact per file in the session's memory folder (the path is in the memory
instructions at the top of the session). Frontmatter with `name`, `description` and
`metadata.type` (user / feedback / project / reference). For feedback and project entries,
follow the fact with **Why:** and **How to apply:** lines. Convert relative dates to absolute.
Link related memories with `[[name]]`. Then add one line to `MEMORY.md`. Before writing,
check whether an existing file already covers it and update that file instead.

Do not save what the repo already records. Do not save anything only this conversation
needs. Do not put content in `MEMORY.md`; it is an index.

## What to propose, not write

Rules, skills and tests change how every future session behaves or assert a figure Charlie
has not audited. List them; do not write them until Charlie says yes.

For each item give one line: what it is, where it would go, and the mistake or repetition it
addresses. If Charlie is not present (an autonomous run), leave the list in the report and
stop; a later session or Charlie picks it up.

When Charlie says yes to a skill, build it under `~/.claude/skills/<name>/SKILL.md` with the
frontmatter the other skills use. When he says yes to a test, write it so it pins the exact
construction (window, anchor, config) and fails with a message that names the convention.

## The report

Plain register. Three short sections, each a list or the word "none":

- **Written**: each file with its path and a one-line summary.
- **Proposed**: rules, skills, tests awaiting a yes.
- **Considered and skipped**: things that came up but did not clear the bar, with the reason
  in a few words. This is what lets Charlie catch a wrong call.

Then one line: what the scope was (since which checkpoint, or the whole visible session).

## After a yes

If Charlie approves an item, write it in the same turn and confirm the path. Do not
re-propose it at the next checkpoint.
