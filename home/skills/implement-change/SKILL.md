---
name: implement-change
description: Lead-engineer workflow for a substantial change to code, an analysis, a workbook or a deck - research by subagents, one plan, questions for Charlie only where the method or a number is at stake, scoped implementation, verification, adversarial review, fixes, final report with provenance. Use when Charlie types /implement-change, or for any task that changes a quoted figure, a method, a convention, the dashboard or an investor deliverable. Not for tiny edits.
argument-hint: <what to change and the acceptance criteria>
---

# Implement a change

Operate as the lead engineer. Keep decisions and coordination in this context; push
exploration and execution into subagents. Do not research, implement and judge the same
change in one context when it matters.

Small change (one file, no figure moves, no convention touched): skip this and just do it.

## 1. Understand

Extract from the request: the user-visible outcome, the acceptance criteria, the constraints,
and the assumptions that are unclear. Write them down in the plan, not in your head.

## 2. Interview the problem

Ask Charlie only the questions that would materially change the method or a number: window,
anchor date, record end, convention, cost or fee basis, benchmark, a data gap. Do not ask
anything the repo can answer. Ask them now, before research, if they gate the design; otherwise
after the plan, in one batch. Never pick a window, a proxy or a truncation silently.

## 3. Research (parallel subagents)

Launch `researcher` agents in one message, one per independent question, such as:
- the code path and conventions behind the thing being changed;
- the data: series, window, frequency, basis, gaps;
- existing similar work, decisions and memory entries, and whether another session already
  built it (git log, skills folder);
- tests and pins that the change would move.

Each returns evidence with `path:line`. Keep only the conclusions in this context.

## 4. Plan

Give the research to `architect`. Require: the smallest design that reuses what exists, one
owner per file, the decision file if a figure or convention moves, a machine-checkable
verification plan, and the list of questions for Charlie. Put those questions to him and
wait. Write the decision file (status proposed) before implementation starts.

## 5. Implement

Break the plan into tasks with non-overlapping file ownership. Sessions share one working
tree, so two agents never edit the same file; serialise shared files. Give each `implementer`
a contract: objective, files owned, files read-only, constraints, verification commands,
deliverable format. Run independent tasks in parallel. No commits.

## 6. Verify

Run the targeted tests and the named pin with the project Python. Syntax-check edited
Python. Rebuild or render what the plan says to look at, and look at it. Every figure
produced gets its construction stated: window, real or re-run or proxied, script or cache.

## 7. Adversarial review

Run the `adversarial-review` skill on the final diff and deliverable: `reviewer` always,
`figure-checker` whenever a number is involved, `security-reviewer` when the change touches
the dashboard server, credentials, the database, remotes or downloaded files. Do not pass
the implementer's reasoning to them.

## 8. Fix and re-verify

Resolve every P0, P1 and P2. Re-run the verification from step 6. Re-review if a fix was
more than cosmetic.

## 9. Report

Return to Charlie, plain register:
1. what changed and why, in a few sentences;
2. the figures, each with window, source and script;
3. the commands run and their results, failures included;
4. reviewer findings and how each was resolved, and any left open;
5. what remains uncertain or unverified;
6. the deliverable as a file card (workbook attached, slide rendered).

Record each conclusion the work reached in the claim store (`claims` skill), superseding any
it overturned with the reason. Then run the `checkpoint` skill. Commit only if Charlie asked.
