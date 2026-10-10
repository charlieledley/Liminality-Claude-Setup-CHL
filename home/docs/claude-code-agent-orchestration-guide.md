# Claude Code Agent Orchestration Guide

> A practical playbook for getting maximum leverage from Claude Code using **CLAUDE.md, skills, subagents, agent teams, worktrees, hooks, MCP, verification loops, and dynamic workflows**.

---

## 1. The Core Mental Model

Do not treat Claude Code as a smarter autocomplete.

Treat it like an **engineering organization**:

```text
You
 │
 ▼
Lead / Orchestrator
 │
 ├── Research Agent
 ├── Architecture Agent
 ├── Implementation Agent(s)
 ├── Test Agent
 ├── Security Agent
 └── Reviewer Agent
```

The lead agent should primarily:

1. Understand the objective.
2. Explore enough of the codebase to establish constraints.
3. Break the work into independently verifiable tasks.
4. Delegate context-heavy research.
5. Coordinate implementation.
6. Run verification.
7. Request adversarial review.
8. Integrate only verified work.

Claude Code officially supports several parallelization mechanisms, including subagents, independent/background sessions, agent teams, worktrees, and dynamic workflows.

The principle is:

```text
Main context = decisions + coordination
Worker contexts = exploration + execution
Deterministic tools = validation
```

---

# 2. Build the Project Operating System First

Before asking Claude to build features, configure the environment it will operate inside.

A useful project structure:

```text
your-project/
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── researcher.md
│   │   ├── architect.md
│   │   ├── implementer.md
│   │   ├── reviewer.md
│   │   ├── security-reviewer.md
│   │   └── test-engineer.md
│   ├── skills/
│   │   ├── implement-feature/
│   │   │   └── SKILL.md
│   │   ├── review-pr/
│   │   │   └── SKILL.md
│   │   └── debug/
│   │       └── SKILL.md
│   ├── rules/
│   │   ├── frontend.md
│   │   ├── backend.md
│   │   └── testing.md
│   └── hooks/
│       └── ...
├── docs/
│   ├── architecture.md
│   └── decisions/
└── src/
```

Claude Code loads project configuration from `.claude`, while `CLAUDE.md` provides persistent project instructions. Project-level configuration can be committed to Git and shared with the team.

---

# 3. Make `CLAUDE.md` Excellent

`CLAUDE.md` should contain information Claude **cannot cheaply infer** or that you would otherwise repeat every session. Claude Code reads these persistent instructions when working in the project.

Do **not** dump your entire documentation into it.

Use something like:

```md
# Project

## Objective

This repository contains a production SaaS application.

## Architecture

Frontend:
- Next.js
- TypeScript
- React Query

Backend:
- Node.js
- PostgreSQL
- Prisma

Infrastructure:
- AWS
- Docker

## Architectural Rules

- API handlers must not contain business logic.
- Business logic belongs in service modules.
- Database access belongs in repositories.
- Never access Prisma directly from UI/API handlers.
- Prefer existing abstractions over creating parallel systems.

## Workflow

For non-trivial changes:

1. Explore relevant code before editing.
2. Identify existing patterns.
3. Produce a short implementation plan.
4. Implement the smallest coherent change.
5. Run targeted tests.
6. Run typecheck/lint.
7. Review the diff.
8. Fix all discovered regressions.

## Testing

Before declaring completion:

```bash
npm run typecheck
npm run lint
npm test
```

Add or update tests whenever behavior changes.

## Safety

Never:

- modify production infrastructure without explicit approval
- delete migrations
- expose secrets
- disable tests merely to make CI green
- silently weaken authentication or authorization

## Git

- Keep changes focused.
- Do not rewrite unrelated files.
- Never use destructive git commands unless explicitly requested.
- Review `git diff` before completion.

## Definition of Done

A task is complete only when:

- implementation matches requirements
- relevant tests pass
- typecheck passes
- lint passes
- edge cases were considered
- final diff has been reviewed
```

### Rule of thumb

Your `CLAUDE.md` should answer:

```text
How do we build software HERE?
```

Not:

```text
What does every file in this repository contain?
```

For large repositories, Claude Code also supports nested `CLAUDE.md` files and path-specific rules so instructions can stay close to the packages they govern.

---

# 4. Separate Knowledge, Workers, and Automation

Do not make one giant prompt responsible for everything.

Use:

```text
CLAUDE.md   → persistent rules
Skills      → reusable procedures
Subagents   → specialized workers
Agent teams → collaborating independent sessions
Hooks       → deterministic enforcement
MCP         → external systems/tools
Workflows   → large deterministic orchestration
```

Claude's own feature guide makes roughly this distinction: skills provide reusable knowledge/workflows, subagents isolate context, agent teams coordinate independent sessions, MCP exposes external services, and hooks trigger deterministic automation during the agent lifecycle.

---

# 5. Build Specialized Subagents

Subagents are one of the highest-leverage Claude Code features.

They operate in separate contexts and return summarized results, which prevents exploratory work from consuming the main conversation's context window. They can also be given specialized instructions and restricted tool access.

Create agents with narrow responsibilities.

## Research Agent

```md
---
name: researcher
description: Investigates the codebase before implementation and returns evidence-backed findings.
---

You are a codebase research specialist.

Your job is to understand, not implement.

For every investigation:

1. Locate the relevant entry points.
2. Trace important execution paths.
3. Find similar existing implementations.
4. Identify tests covering the behavior.
5. Identify architectural constraints.
6. Identify likely regression risks.

Do not edit files unless explicitly requested.

Return:

## Relevant Files
- path — why it matters

## Current Behavior

## Existing Patterns

## Dependencies

## Risks

## Recommended Implementation Surface
```

---

## Architecture Agent

```md
---
name: architect
description: Designs implementation strategies for substantial changes.
---

You are a senior software architect.

Do not implement immediately.

Given a feature or refactor:

1. Study available research.
2. Inspect relevant architecture.
3. Identify the smallest coherent design.
4. Reuse existing abstractions.
5. Avoid unnecessary dependencies.
6. Identify migration and compatibility risks.
7. Define verification criteria.

Return:

## Proposed Design

## Files to Change

## Interfaces

## Data Flow

## Alternatives Considered

## Risks

## Implementation Sequence

## Verification Plan
```

---

## Implementation Agent

```md
---
name: implementer
description: Implements a well-scoped engineering task and verifies the change.
---

You are an implementation specialist.

Before editing:

1. Understand the assigned scope.
2. Read relevant existing code.
3. Follow project conventions.

While implementing:

- keep the change minimal
- avoid unrelated refactors
- add tests for changed behavior
- preserve backwards compatibility unless explicitly told otherwise

Before finishing:

1. Run relevant tests.
2. Run typecheck/lint where appropriate.
3. Inspect the diff.
4. Report anything you could not verify.

Return:

## Changes

## Tests

## Verification

## Remaining Risks
```

---

## Test Agent

```md
---
name: test-engineer
description: Finds missing coverage and tests behavior independently.
---

You are a test engineer.

Analyze the requested behavior and implementation.

Look specifically for:

- happy path
- boundary conditions
- invalid inputs
- state transitions
- concurrency issues
- failure recovery
- backwards compatibility
- regression scenarios

Do not merely duplicate existing tests.

When appropriate, write tests and execute them.

Return:

## Coverage Assessment

## Missing Cases

## Tests Added

## Failures Found

## Confidence
```

---

## Reviewer Agent

```md
---
name: reviewer
description: Performs adversarial code review after implementation.
---

You are an adversarial senior code reviewer.

Assume there may be hidden defects.

Do not praise the implementation.

Search for:

- incorrect assumptions
- logic bugs
- race conditions
- missing error handling
- duplicated abstractions
- performance regressions
- API compatibility issues
- unnecessary complexity
- test gaps

Classify findings:

P0 — critical
P1 — serious
P2 — moderate
P3 — minor

For every finding provide:

- severity
- file/location
- concrete problem
- why it matters
- proposed correction

If you find nothing, explicitly state what you checked.
```

---

## Security Reviewer

```md
---
name: security-reviewer
description: Reviews security-sensitive changes for exploitable weaknesses.
---

You are an application security engineer.

Focus on:

- authentication
- authorization
- access control
- injection
- secret exposure
- SSRF
- XSS
- CSRF
- path traversal
- insecure deserialization
- unsafe redirects
- privilege escalation
- tenant isolation
- dependency risks

Distinguish theoretical concerns from realistic vulnerabilities.

For each issue provide:

Severity:
Attack scenario:
Affected code:
Recommended fix:
```

---

# 6. Delegate Research Aggressively

A common mistake is keeping every exploration step in the main context.

Bad:

```text
Main agent
  reads 100 files
  searches architecture
  reads tests
  investigates dependencies
  implements
  debugs
  reviews

→ enormous noisy context
```

Better:

```text
Main agent
   │
   ├── Researcher → authentication architecture
   ├── Researcher → database model implications
   ├── Researcher → existing test patterns
   └── Researcher → similar feature elsewhere
           │
           ▼
     compressed findings
           │
           ▼
       Main agent
```

Claude's documentation specifically recommends subagents for isolated investigation and context management.

---

# 7. Parallelize Independent Questions

Sequential investigation:

```text
A → B → C → D
```

takes longer and creates unnecessary dependency chains.

When tasks are independent:

```text
      ┌─ A ─┐
      ├─ B ─┤
START ├─ C ─┤ → SYNTHESIZE
      └─ D ─┘
```

Good parallel tasks:

```text
Agent 1: inspect current auth architecture
Agent 2: inspect database implications
Agent 3: inspect API conventions
Agent 4: inspect test strategy
```

Bad parallelization:

```text
Agent 1 edits user.ts
Agent 2 edits user.ts
Agent 3 refactors user.ts
Agent 4 updates tests assuming all three versions
```

Parallelize **independent ownership**, not conflicting edits.

---

# 8. Use Agent Teams for Bigger Problems

Agent teams differ from ordinary subagents.

Subagents are excellent for bounded delegated tasks that report back into the main session. Agent teams coordinate multiple independent Claude Code sessions using shared tasks and inter-agent communication.

As of the current Claude Code documentation, agent teams are experimental and must be enabled with:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```



Use teams when the problem has substantial parallel work.

Example:

```text
Lead
 │
 ├── Backend teammate
 │     └── API + service layer
 │
 ├── Frontend teammate
 │     └── UI implementation
 │
 ├── Test teammate
 │     └── integration/e2e tests
 │
 └── Reviewer teammate
       └── independent review
```

A strong kickoff prompt:

```text
Create an agent team for this task.

First investigate the problem before implementation.

Use teammates with non-overlapping ownership:

1. architecture/research
2. backend implementation
3. frontend implementation
4. testing/review

Require research and architecture findings before large implementation
decisions.

Keep file ownership separate whenever possible.

After implementation:
- run tests
- run typecheck/lint
- have an independent reviewer inspect the combined diff
- resolve serious findings
- report final verification evidence
```

---

# 9. Prefer Subagents vs Teams Intentionally

Use **subagents** when:

```text
✓ task is bounded
✓ worker primarily reports findings
✓ isolation is valuable
✓ you want focused context
✓ one lead should own decisions
```

Use **agent teams** when:

```text
✓ several substantial tasks can progress concurrently
✓ agents need independent contexts
✓ workers need to communicate
✓ work lasts across many steps
✓ ownership can be clearly separated
```

Use ordinary Claude Code when:

```text
✓ change is tiny
✓ coordination overhead exceeds implementation work
```

Do not spawn six agents to rename one function.

---

# 10. Use Git Worktrees for True Parallel Development

Multiple implementation agents editing the same checkout can produce conflicts.

For substantial independent branches of work:

```text
repository
├── main checkout
├── worktree-backend
├── worktree-frontend
└── worktree-tests
```

Claude Code's parallel-agent guidance explicitly supports using isolated Git worktrees for parallel sessions.

Example:

```bash
git worktree add ../project-backend -b agent/backend
git worktree add ../project-frontend -b agent/frontend
git worktree add ../project-tests -b agent/tests
```

Then run separate Claude sessions:

```bash
cd ../project-backend
claude
```

```bash
cd ../project-frontend
claude
```

```bash
cd ../project-tests
claude
```

Later:

```bash
git checkout main

git merge agent/backend
git merge agent/frontend
git merge agent/tests
```

Then perform a final integrated verification pass.

---

# 11. Give Agents Contracts, Not Vague Roles

Weak:

```text
You are the backend agent. Build the backend.
```

Strong:

```text
OWNERSHIP

You own:
- src/api/**
- src/services/**
- tests/api/**

You may inspect but should not modify:
- src/frontend/**

OBJECTIVE

Implement POST /api/invitations.

REQUIREMENTS

- existing users cannot receive duplicate invitations
- invitation expires after 7 days
- authorization follows existing organization-role conventions
- response format must match other API endpoints

BEFORE IMPLEMENTING

Inspect:
- existing invitation model
- auth middleware
- organization membership logic
- similar POST endpoints

VERIFICATION

Run:
npm test -- invitations
npm run typecheck

DELIVERABLE

Return:
- files changed
- important design decisions
- test results
- unresolved risks
```

Agent quality increases dramatically when each worker has:

```text
Objective
+
Ownership
+
Constraints
+
Dependencies
+
Deliverable
+
Verification
```

---

# 12. Separate Exploration From Implementation

One of the strongest Claude Code workflows is:

```text
Explore
   ↓
Plan
   ↓
Implement
   ↓
Verify
```

Anthropic's Claude Code best-practices documentation explicitly recommends exploring before implementation and giving Claude concrete ways to verify its work.

For complicated tasks:

```text
Phase 1
Research only.

Phase 2
Architecture only.

Phase 3
Implementation.

Phase 4
Tests.

Phase 5
Independent review.

Phase 6
Fix findings.

Phase 7
Final verification.
```

Do not make the same context simultaneously discover requirements, invent architecture, implement it, and judge whether its own decisions were correct.

---

# 13. Make Verification the Center of the Workflow

Claude becomes dramatically more reliable when success is machine-checkable.

Weak objective:

```text
Make authentication work.
```

Strong objective:

```text
Implement refresh-token rotation.

Acceptance criteria:

1. successful refresh returns new access + refresh tokens
2. previous refresh token becomes invalid
3. reused token invalidates its token family
4. expired tokens return 401
5. existing login flow remains unchanged

Verify with:

npm test -- auth
npm run typecheck
npm run lint
```

Think:

```text
Agent capability × feedback quality = useful autonomy
```

The more objective your feedback loop, the more autonomy you can safely give.

---

# 14. Use an Adversarial Review Loop

Do not ask:

```text
Does your implementation look correct?
```

The implementing agent has anchoring bias toward its own solution.

Instead:

```text
Implementer
     ↓
Test suite
     ↓
Independent reviewer
     ↓
Security reviewer if needed
     ↓
Implementer fixes findings
     ↓
Tests again
     ↓
Final reviewer
```

Prompt:

```text
Spawn an independent reviewer.

Do not provide the implementer's reasoning unless necessary.

Have the reviewer inspect:
- requirements
- final diff
- surrounding architecture
- relevant tests

Ask it to actively search for counterexamples, hidden regressions,
incorrect assumptions, and missing tests.

Return only actionable findings with severity and evidence.
```

Anthropic's best-practices guide also recommends adding an adversarial review step when scaling Claude Code work.

---

# 15. Use Competing Hypotheses for Hard Bugs

For difficult debugging, avoid letting the first plausible explanation dominate.

Run multiple investigators independently:

```text
Bug report
    │
    ├── Agent A → hypothesis 1
    ├── Agent B → hypothesis 2
    ├── Agent C → hypothesis 3
    └── Agent D → inspect logs/tests
                  │
                  ▼
              Lead compares
                  │
                  ▼
           targeted experiment
```

Prompt:

```text
Investigate this bug using competing hypotheses.

Spawn three independent investigators.

Each investigator should:
1. inspect the symptoms independently
2. propose the most likely root cause
3. identify evidence supporting it
4. identify evidence that would falsify it
5. propose the cheapest experiment to test it

Do not let investigators see each other's conclusions initially.

Afterward synthesize the hypotheses and run the most discriminating tests.
```

Agent teams are explicitly documented as useful for investigating competing hypotheses.

---

# 16. Use Hooks for Things That Must Always Happen

Prompts are probabilistic.

Hooks are deterministic.

Claude Code hooks can run scripts, HTTP calls, prompts, or agents at lifecycle events, making them appropriate for enforcing project rules and automating repeated checks.

Use prompts for:

```text
"Consider performance."
```

Use hooks for:

```text
"Run formatter after modifications."
```

Useful hooks:

```text
After edit
→ formatter

After edit
→ targeted lint

Before dangerous shell command
→ validation

Before completion
→ test verification

On session end
→ log summary

On sensitive operation
→ require approval
```

Examples of deterministic policy:

```text
Never allow:
rm -rf /
git push --force
dropping production databases
reading forbidden secret directories
```

A useful principle:

```text
Reasoning → agents
Policy → hooks
```

---

# 17. Use MCP as the Agent's External Nervous System

Claude Code already has built-in filesystem and shell capabilities.

MCP becomes valuable when the agent needs structured access to external systems. Claude Code's extension model uses MCP to expose additional services and tools to the agent.

Possible integrations:

```text
GitHub
Databases
Issue trackers
Observability
Documentation
Browsers
Internal APIs
Deployment systems
Cloud infrastructure
```

Architecture:

```text
Claude Code
    │
    ├── filesystem
    ├── shell
    ├── git
    │
    └── MCP
         ├── GitHub
         ├── Postgres
         ├── issue tracker
         ├── monitoring
         └── internal tools
```

Be conservative with write permissions.

Prefer:

```text
read logs
read tickets
read schemas
read deployment state
```

before:

```text
modify production DB
deploy production
delete cloud resources
```

---

# 18. Build Skills for Repeated Workflows

If you repeatedly type the same 300-word prompt, turn it into a skill.

Claude Code skills are reusable instruction/workflow packages that Claude can invoke when appropriate.

Examples:

```text
/implement-feature
/debug-production
/review-pr
/create-migration
/release
/security-audit
/refactor-module
```

Conceptual `SKILL.md`:

```md
---
name: implement-feature
description: Implements substantial product features using research, planning, testing, and review.
---

# Feature Implementation Workflow

When implementing a feature:

## 1. Understand

Extract:
- user-visible behavior
- acceptance criteria
- constraints
- unclear assumptions

## 2. Research

Delegate investigation of:
- relevant architecture
- similar implementations
- tests
- dependencies

## 3. Plan

Produce:
- proposed design
- files affected
- implementation sequence
- risk areas
- verification plan

## 4. Implement

Delegate independent components where appropriate.

## 5. Verify

Run:
- targeted tests
- typecheck
- lint
- build if relevant

## 6. Review

Use an independent review agent.

## 7. Fix

Resolve P0/P1/P2 findings.

## 8. Final Verification

Rerun checks and review the final diff.
```

Now your workflow becomes reusable rather than dependent on remembering the perfect prompt every time.

---

# 19. Use Dynamic Workflows When Orchestration Gets Huge

There is a point where allowing the lead model to manually coordinate dozens of workers becomes inefficient.

Claude Code now distinguishes between model-orchestrated agents and **dynamic workflows**. In a workflow, orchestration logic lives in a script, intermediate results stay outside the model's context, and the system can scale to much larger numbers of agent executions.

Conceptually:

```text
Small task
→ Claude Code

Medium task
→ Claude + subagents

Large parallel task
→ agent team

Large repeatable orchestration
→ workflow
```

For example:

```text
Run 40 independent file audits
        ↓
collect structured results
        ↓
group duplicate findings
        ↓
send only suspicious groups to reviewers
        ↓
run verification agents
        ↓
return compressed final report
```

This is much better than stuffing all 40 raw investigations into the lead agent's context.

---

# 20. Context Is Your Scarce Resource

The main enemy of long autonomous sessions is not intelligence.

It is **context pollution**.

Avoid filling the primary session with:

```text
thousands of lines of logs
dozens of irrelevant source files
full dependency documentation
repeated test output
discarded hypotheses
low-value implementation details
```

Instead:

```text
Worker
  reads 30 files
      ↓
returns
  20-line summary
```

Keep the main context focused on:

```text
requirements
architecture
decisions
task state
important findings
verification results
```

This is one of the main reasons subagents are powerful: their work can remain isolated while only useful results return to the parent context.

---

# 21. Ask Agents to Return Structured Results

Do not let every worker dump arbitrary prose.

Use contracts.

For research:

```md
## Conclusion

## Evidence

## Relevant Files

## Risks

## Recommendation

## Confidence
```

For implementation:

```md
## Files Changed

## Behavior Added

## Tests Added

## Commands Run

## Results

## Remaining Risks
```

For review:

```md
## P0

## P1

## P2

## P3

## Missing Tests

## Final Assessment
```

Structured responses are easier for the lead agent to synthesize correctly.

---

# 22. Make Agents Cite Code Evidence

Research agents should avoid unsupported claims.

Prompt them with:

```text
Every important conclusion must reference concrete evidence from the repository.

Prefer:
path/to/file.ts: relevant symbol or section

Do not infer architecture solely from filenames.
```

Now your orchestration becomes:

```text
claim
  ↓
evidence
  ↓
decision
```

rather than:

```text
guess
  ↓
implementation
```

---

# 23. Separate File Ownership

When several implementation agents are active, assign ownership explicitly.

Example:

```text
Backend Agent
src/api/**
src/services/**

Frontend Agent
src/components/**
src/app/**

Database Agent
prisma/**
src/repositories/**

Testing Agent
tests/**
e2e/**
```

Shared files should ideally have one owner.

If multiple agents must change the same architectural file, serialize that part:

```text
Agent A changes schema
       ↓
Agent B consumes schema
       ↓
Agent C adds integration tests
```

---

# 24. Use Dependency-Aware Task Graphs

Do not think only in lists.

Think in DAGs.

Example:

```text
                 ┌─ Frontend ─────┐
Research → API ──┤                 ├→ Integration tests → Review
                 └─ Backend ──────┘
```

Represent tasks mentally as:

```text
T1 Research

T2 Design API
depends_on: T1

T3 Backend
depends_on: T2

T4 Frontend
depends_on: T2

T5 Integration
depends_on: T3,T4

T6 Review
depends_on: T5
```

Then parallelize only where dependencies permit:

```text
T3 || T4
```

---

# 25. Optimize for Information Gain

Agents should not perform expensive work merely because they can.

Before delegating, ask:

```text
What uncertainty are we trying to remove?
```

Example:

Bad:

```text
Read the entire repository and understand everything.
```

Better:

```text
Determine where authorization for organization-scoped mutations is
currently enforced.

Inspect only enough code to answer:

1. middleware or service layer?
2. how roles are represented?
3. what tests establish expected behavior?
4. which existing mutation best represents the pattern?

Return evidence-backed findings.
```

A specialized investigation gives the lead high-value information per token.

---

# 26. Use Cheap Agents for Breadth, Strong Agents for Judgment

A useful orchestration pattern is:

```text
Broad discovery
→ many focused workers

Synthesis
→ strong lead

Implementation
→ focused workers

Final architecture/security judgment
→ strongest appropriate reviewer
```

Do not waste the most expensive reasoning on repetitive scanning when simpler workers can collect evidence first.

Save high-quality context for:

```text
architecture
tradeoffs
ambiguous bugs
security
cross-system reasoning
final synthesis
```

---

# 27. Let Claude Interview the Problem

For ambiguous features, don't immediately code.

Prompt:

```text
Before implementation, identify the decisions that would materially
change the architecture or user-visible behavior.

Ask me only those questions.

Do not ask questions whose answers can be discovered from the repository.
```

This creates the hierarchy:

```text
Repository-resolvable question
→ agent investigates

Product decision
→ ask human

Implementation detail
→ agent decides
```

That prevents unnecessary human interruption without letting Claude invent important product requirements.

---

# 28. Design Prompts Around Outcomes

Bad:

```text
Open src/auth.ts.
Read token.ts.
Modify line 44.
Add an if statement.
```

Better:

```text
Prevent replay of rotated refresh tokens while preserving the existing
login API.

Investigate the current token lifecycle first.

Reuse existing patterns where possible.

Add tests demonstrating the exploit before the fix and successful
rejection afterward.

Run relevant verification and review the final diff.
```

Claude Code's agentic loop is strongest when you specify the objective and verification target while allowing the agent to investigate how the repository actually works.

---

# 29. A Strong Feature-Orchestration Prompt

```text
Implement the following feature:

[FEATURE]

Acceptance criteria:

[CRITERIA]

Operate as the lead engineer.

PHASE 1 — RESEARCH

Delegate parallel research for:

1. relevant architecture
2. similar implementations
3. test coverage and conventions
4. likely integration risks

Do not implement yet.

PHASE 2 — PLAN

Synthesize the research into:

- proposed design
- affected files
- interface changes
- data-flow changes
- migration concerns
- testing strategy

Prefer the smallest solution consistent with existing architecture.

PHASE 3 — IMPLEMENT

Break implementation into independent tasks.

Delegate tasks in parallel only when they have non-overlapping ownership
or safe dependency boundaries.

Avoid unrelated refactors.

PHASE 4 — VERIFY

Run:

- targeted unit tests
- integration tests where relevant
- typecheck
- lint
- build if relevant

PHASE 5 — ADVERSARIAL REVIEW

Have an independent reviewer inspect:

- requirements
- final diff
- surrounding code
- tests

Look for:

- logic errors
- edge cases
- compatibility regressions
- architectural inconsistencies
- missing tests

PHASE 6 — FIX

Resolve all P0/P1/P2 findings.

PHASE 7 — FINAL VERIFICATION

Rerun relevant checks.

Return:

1. architecture summary
2. implementation summary
3. files changed
4. verification evidence
5. reviewer findings and resolutions
6. remaining risks
```

---

# 30. A Strong Bug-Fixing Prompt

```text
Investigate and fix:

[BUG]

Do not begin by editing code.

Use three stages.

STAGE 1 — INDEPENDENT INVESTIGATION

Delegate investigators to examine:

- execution path
- relevant state/data flow
- recent or nearby implementation patterns
- tests
- likely failure boundaries

For difficult bugs, use competing hypotheses.

Each hypothesis must include:

- evidence
- contradictions
- a test that could falsify it

STAGE 2 — PROVE ROOT CAUSE

Before implementing a fix:

- reproduce the issue when possible
- identify the smallest failing case
- explain the causal chain

STAGE 3 — FIX AND VERIFY

Implement the smallest fix addressing the root cause.

Add a regression test.

Run relevant validation.

Have an independent reviewer search for:

- symptom-only fixes
- hidden variants
- backwards compatibility issues
- missing edge cases

Return the root cause, fix, regression test, and verification evidence.
```

---

# 31. A Strong Refactoring Prompt

```text
Refactor:

[TARGET]

Primary objective:

[OBJECTIVE]

Constraints:

- behavior must remain unchanged
- public APIs must remain compatible unless explicitly noted
- avoid unrelated cleanup
- preserve existing tests

Before implementing:

1. map current dependencies
2. identify public/internal boundaries
3. identify behavioral contracts
4. find relevant test coverage

Develop a migration sequence that keeps the repository working after
each major step.

Where possible, delegate independent migration components.

After implementation:

- run targeted tests
- run the complete relevant suite
- run typecheck/lint
- inspect API changes
- have an independent reviewer specifically search for behavioral drift

Return any behavior that could not be proven equivalent.
```

---

# 32. A Strong Security Audit Prompt

```text
Perform an adversarial security review of:

[SCOPE]

Use independent investigators for:

1. authentication
2. authorization
3. input validation / injection
4. secrets / sensitive data
5. tenant isolation
6. dependency or infrastructure risks

Do not report generic best practices.

Every finding must include:

- severity
- exploit precondition
- concrete attack path
- affected code
- impact
- evidence
- recommended remediation
- confidence

After independent investigation, have a lead reviewer remove duplicates
and reject unsupported findings.

Prioritize exploitable issues over theoretical concerns.
```

---

# 33. A Strong PR Review Prompt

```text
Review the current branch against its base branch.

Use separate reviewers for:

1. correctness
2. architecture
3. tests
4. security
5. performance if relevant

Each reviewer must inspect the diff AND enough surrounding code to
understand context.

Do not spend tokens praising good code.

Return only:

P0
P1
P2
P3

Each finding requires:

- file/location
- concrete failure mode
- evidence
- recommended correction

Afterward, deduplicate findings and challenge questionable findings
before presenting the final report.
```

---

# 34. Use a Builder–Critic Pattern

For important decisions:

```text
Builder
   ↓
proposal
   ↓
Critic
   ↓
objections
   ↓
Builder
   ↓
revision
   ↓
Verifier
```

Example:

```text
Architect A:
design migration strategy

Architect B:
attack Architect A's proposal

Architect A:
revise based on valid criticism

Reviewer C:
evaluate the revised version independently
```

This is especially useful for:

```text
database migrations
authentication
distributed systems
major refactors
public APIs
performance architecture
```

---

# 35. Use a Research–Synthesis Pattern

For unfamiliar codebases:

```text
            ┌── subsystem A researcher
            ├── subsystem B researcher
Question ───┼── test researcher
            ├── history/pattern researcher
            └── dependency researcher
                      │
                      ▼
                  Synthesizer
```

Do not ask every research agent to produce the final answer.

Their job is evidence collection.

The synthesizer's job is judgment.

---

# 36. Use a Map–Reduce Pattern for Large Audits

For hundreds of files:

```text
MAP
Agent 1 → files 1–20
Agent 2 → files 21–40
Agent 3 → files 41–60
...

REDUCE
Reviewer A → deduplicate
Reviewer B → validate suspicious findings

FINAL
Lead → rank + summarize
```

Useful for:

```text
security audits
migration inventories
API inventories
deprecated-code searches
test-gap analysis
large refactors
```

At sufficiently large scale, dynamic workflows are a better fit than manually maintaining all intermediate worker outputs in a lead context.

---

# 37. Use Agent View for Independent Background Work

Claude Code provides an agent view for managing multiple background sessions from one interface. It can be opened with:

```bash
claude agents
```

and is designed for monitoring independent sessions, seeing which need input, and switching between them.

Use this when you have tasks such as:

```text
Session 1 → upgrade dependency
Session 2 → investigate flaky test
Session 3 → write migration
Session 4 → audit API
```

that do not require tight inter-agent communication.

---

# 38. Know When NOT to Parallelize

Parallelism has costs:

```text
token usage
coordination
duplicate investigation
merge conflicts
inconsistent assumptions
review overhead
```

Do not parallelize when:

```text
task is tiny
tasks edit the same files
later work depends heavily on earlier discoveries
architecture is still unknown
a single agent can finish faster than delegation can be coordinated
```

Think:

```text
parallelize uncertainty
before
parallelizing implementation
```

Often the best sequence is:

```text
parallel research
       ↓
single architecture
       ↓
parallel implementation
       ↓
single integration
       ↓
parallel review
```

---

# 39. The Ideal High-End Workflow

For a serious feature:

```text
                         USER
                          │
                          ▼
                    LEAD AGENT
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Research A   Research B   Research C
             │            │            │
             └────────────┼────────────┘
                          ▼
                     ARCHITECT
                          │
                          ▼
                   approved design
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          Backend      Frontend      Database
             │            │            │
             └────────────┼────────────┘
                          ▼
                     INTEGRATION
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
             TESTER              REVIEWER
                │                   │
                └─────────┬─────────┘
                          ▼
                    FIX FINDINGS
                          │
                          ▼
                 SECURITY REVIEW
                    if relevant
                          │
                          ▼
                 FINAL VERIFICATION
                          │
                          ▼
                       RESULT
```

This approximates a real engineering team's separation of responsibilities.

---

# 40. Recommended `.claude` Setup

A mature configuration might look like:

```text
.claude/
│
├── agents/
│   ├── researcher.md
│   ├── architect.md
│   ├── implementer.md
│   ├── debugger.md
│   ├── test-engineer.md
│   ├── reviewer.md
│   ├── security-reviewer.md
│   └── performance-reviewer.md
│
├── skills/
│   ├── implement-feature/
│   │   └── SKILL.md
│   ├── fix-bug/
│   │   └── SKILL.md
│   ├── review/
│   │   └── SKILL.md
│   ├── security-audit/
│   │   └── SKILL.md
│   └── release/
│       └── SKILL.md
│
├── rules/
│   ├── architecture.md
│   ├── frontend.md
│   ├── backend.md
│   ├── database.md
│   └── testing.md
│
└── settings.json

CLAUDE.md
```

---

# 41. Give Claude a Definition of Done

Add something similar to this to your project instructions:

```md
# Definition of Done

Never report implementation work as complete merely because code was written.

Before completion:

1. Check the final diff.
2. Run targeted tests.
3. Run static verification.
4. Confirm acceptance criteria individually.
5. Search for obvious regressions.
6. Ensure no debugging artifacts remain.
7. Ensure unrelated files were not changed.
8. Report commands run and their results.

For substantial changes:

9. Request an independent code review.
10. Resolve serious findings.
11. Rerun verification after fixes.

If something cannot be verified, explicitly say so.
```

This single policy can substantially improve autonomous reliability.

---

# 42. Keep Humans at High-Leverage Decision Points

You should usually make decisions about:

```text
product behavior
major architectural tradeoffs
irreversible migrations
security posture
production changes
large dependency changes
business rules
```

Claude should usually handle:

```text
repository exploration
pattern discovery
implementation
routine refactoring
test creation
static analysis
code review
documentation
mechanical migrations
```

The goal is not:

```text
human removed from loop
```

It is:

```text
human attention spent only where judgment has high value
```

---

# 43. Permission Strategy

Do not maximize autonomy by blindly disabling safeguards.

Maximize autonomy by making **safe operations frictionless** and dangerous operations explicit.

Claude Code lets you configure tool permissions, and those same tool names can be referenced by permission rules, subagent tool restrictions, and hooks.

Conceptually:

```text
AUTO-ALLOW

✓ read repository
✓ search files
✓ run tests
✓ run typecheck
✓ lint
✓ format
✓ inspect git diff
✓ write normal source files

REVIEW

? install dependencies
? external network actions
? deployment
? migration execution
? changing CI/infrastructure

BLOCK / EXPLICIT APPROVAL

✗ production database destruction
✗ force pushing protected branches
✗ destructive filesystem operations
✗ accessing unrelated secrets
```

---

# 44. Keep the Lead Agent Out of the Weeds

A lead agent that personally performs everything becomes a worker rather than an orchestrator.

Bad:

```text
Lead:
researches
codes
tests
debugs
reviews
documents
```

Better:

```text
Lead:
understands objective
forms task graph
delegates research
makes architecture decisions
assigns ownership
tracks dependencies
integrates findings
orders verification
resolves disputes
reports result
```

Delegate high-volume information processing.

Keep high-value decisions centralized.

---

# 45. Use Progressive Autonomy

Do not start a new project with:

```text
Go autonomously build the whole platform.
```

Increase autonomy as your verification infrastructure improves.

### Level 1

```text
Claude suggests changes
Human approves everything
```

### Level 2

```text
Claude edits
Human reviews
```

### Level 3

```text
Claude edits + tests
Human reviews final diff
```

### Level 4

```text
Claude orchestrates workers + automated review
Human reviews major decisions
```

### Level 5

```text
Claude runs repeatable workflows
Hooks enforce policies
Tests verify behavior
Human handles exceptions
```

The prerequisite for autonomy is not trust.

It is **verification infrastructure**.

---

# 46. The Maximum-Leverage Stack

A strong Claude Code environment ultimately looks like:

```text
                    HUMAN
                      │
             goals / decisions
                      │
                      ▼
                LEAD CLAUDE
                      │
             orchestration layer
                      │
       ┌──────────────┼───────────────┐
       │              │               │
       ▼              ▼               ▼
   SUBAGENTS      AGENT TEAMS     WORKFLOWS
       │              │               │
       └──────────────┼───────────────┘
                      │
             specialized SKILLS
                      │
              project CLAUDE.md
                      │
          path-specific RULES
                      │
                      ▼
             BUILT-IN TOOLS
              │    │     │
             FS   Shell  Git
                      │
                      ▼
                     MCP
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
       GitHub      Database    External APIs
                      │
                      ▼
                    HOOKS
                      │
             deterministic policy
                      │
                      ▼
                 VERIFICATION
         ┌────────────┼─────────────┐
         ▼            ▼             ▼
       Tests      Typecheck       Lint
         │            │             │
         └────────────┼─────────────┘
                      ▼
             ADVERSARIAL REVIEW
                      │
                      ▼
                  FINAL DIFF
```

---

# 47. The 10 Rules to Remember

1. **Explore before implementing.**
2. **Keep the main context focused on decisions, not raw investigation.**
3. **Use subagents to isolate expensive research.**
4. **Parallelize independent work, not conflicting work.**
5. **Give every agent clear ownership and deliverables.**
6. **Give every implementation an objective verification loop.**
7. **Separate builder and reviewer whenever the change matters.**
8. **Use hooks for deterministic rules instead of trusting prompts.**
9. **Turn repeated workflows into skills or workflows.**
10. **Increase autonomy only as your ability to verify results increases.**

---

# 48. Default Playbook

For everyday serious development, use this sequence:

```text
1. Tell Claude the outcome and acceptance criteria.

2. Ask it to explore before editing.

3. Delegate independent research to subagents.

4. Synthesize findings into one architecture.

5. Convert architecture into a dependency-aware task graph.

6. Give implementation agents non-overlapping ownership.

7. Parallelize independent tasks.

8. Integrate the changes.

9. Run tests + typecheck + lint.

10. Send the final diff to an independent reviewer.

11. Fix substantive findings.

12. Rerun verification.

13. Inspect the final diff.

14. Report:
    - what changed
    - why
    - tests run
    - reviewer findings
    - remaining uncertainty
```

The goal is to move from:

```text
Claude writes code
```

to:

```text
Claude runs a verified engineering process.
```

That is where agent orchestration starts producing its largest gains.