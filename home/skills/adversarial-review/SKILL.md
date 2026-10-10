---
name: adversarial-review
description: Independent review of the current diff, a named file, a workbook, a deck build or a set of figures by separate reviewer agents (correctness, figures, security where relevant), with findings deduplicated and challenged before they are reported. Use when Charlie types /adversarial-review, before anything is quoted, sent or committed, and as step 7 of implement-change. Complements the built-in /code-review, which looks at code only.
argument-hint: [diff | path | "the figures in <file>"]
---

# Adversarial review

Separate the builder from the judge. Whoever wrote the change does not review it, and the
reviewers do not see the writer's reasoning unless it is needed to understand the
requirement.

## 1. Scope

Decide what is under review: the working-tree diff (`git diff` plus untracked files you
created), a named script, a workbook in `exports/`, a rendered deck, or a list of figures.
State the requirement the work was meant to meet. Gather only that; do not pull the whole
conversation into the reviewers' prompts.

## 2. Reviewers (one message, in parallel)

- `reviewer` on the diff and surrounding code: always.
- `figure-checker` on every number in the output: whenever there is one.
- `security-reviewer`: when the change touches the dashboard server, `.env` or credentials,
  the database, git remotes, deletion, scheduled tasks or downloaded files.
- The built-in `/code-review` at high effort may be added for pure code changes.

Give each the requirement, the scope, and the instruction to return only actionable findings
with severity and evidence.

## 3. Deduplicate and challenge

Merge the findings. For each P0 and P1, check the evidence yourself before keeping it; drop
findings with no `path:line` or no concrete failure. Where reviewers disagree, say so and
give your judgement.

## 4. Report

P0, P1, P2, P3, then missing tests, then what was checked and by whom. One paragraph: can
this go out, and what must happen first. No praise, no summary of what the change does.

If the review was part of `implement-change`, hand the P0 to P2 list back for fixing.
