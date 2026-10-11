---
name: fix-bug
description: Investigate and fix a bug or a wrong number using independent investigators with competing hypotheses, prove the root cause with the smallest failing case, apply the smallest fix, pin a regression test and have the fix reviewed for symptom-only patches. Use when Charlie types /fix-bug, reports a number that does not reconcile, or a behaviour that is wrong. Not for typos.
argument-hint: <the symptom, with the figure or error text>
---

# Fix a bug

Do not begin by editing code. A wrong number in this repo has usually been a convention
(window, anchor, basis, cost vector, join) rather than a typo, and the first plausible
explanation is often not the right one.

## Stage 1. Independent investigation

For a hard bug, launch three `researcher` agents in one message with the same symptom and
no shared conclusions. Each must return: the most likely root cause, the evidence for it
(`path:line`, figures), the evidence that would falsify it, and the cheapest experiment that
discriminates it from the alternatives. A fourth researcher inspects logs, caches and tests.

For a simple bug, one researcher tracing the execution path is enough.

Also ask: did a parallel session change something recently (`git log`), did the data move
(record end, cache rebuilt), did a convention change without a decision file.

## Stage 2. Prove the root cause

Before any fix:
- reproduce the symptom with the project Python from the main checkout;
- reduce it to the smallest failing case (one date, one tranche, one leg);
- run the discriminating experiment from stage 1;
- write the causal chain in one paragraph, with the numbers.

If the cause is a convention choice rather than a defect (the figure was built on a different
window or basis), stop and put the choice to Charlie; that is a decision, not a fix.

## Stage 3. Fix and verify

Give one `implementer` a contract: the root cause, the smallest fix, the files it may touch,
and the reproduction to re-run. No unrelated changes. Then `test-engineer` adds the
regression test, pinning the smallest failing case, and runs the existing pins.

## Stage 4. Review

`reviewer` inspects the fix for: a symptom-only patch, hidden variants of the same bug
elsewhere, backwards compatibility with saved presets and caches, a pin moved without a
decision. `figure-checker` if the fix changes a quoted number: every figure the bug touched
must be re-stated with its construction, and any decision file or deck data refreshed.

## Report

Root cause with evidence, the fix, the regression test, every figure that changed (old,
new, construction), the commands run, and what is still unverified. Every conclusion the bug
overturned is superseded in the claim store (`claims` skill) with the root cause as the
reason, and the corrected conclusion recorded. Then `checkpoint`. Commit only if asked.
