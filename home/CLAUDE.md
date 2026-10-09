# Working with Charlie

These apply in every project. Repo-specific rules live in each repo's own `CLAUDE.md`.

## Who you are working with

Charlie runs an investment firm and has a quantitative background but no software
background. Assume fluency in finance, options and statistics. Do not assume fluency with
git, shells, Python packaging or software jargon; explain those in plain words the first
time they matter. Charlie reads derivations and audits numbers, not code.

## Numbers

- **Every figure comes with its construction.** State the date window, whether the number
  is real data, a re-run, or proxied, and which script or cache produced it. Put this in
  the message, not in a docstring. When something changes mid-task (a re-run, a new cache,
  a different construction), say so before showing the output.
- **Ask before working around a data gap.** Charlie has a Bloomberg terminal and will pull
  a missing series in minutes. Never silently truncate a window, substitute a proxy
  instrument, or narrow a claim to fit the data on hand. State what is missing, what the
  workaround would cost, and what could be pulled instead. If told to proceed without the
  data, state the limitation in the body of the deliverable, not a footnote.
- **Total return series for every comparison.** Never benchmark against a price index.
- **Never attribute option P&L by entry year.** Calendar-year mark-to-market only.
- When a result depends on a convention that could reasonably go another way (window,
  anchor date, cost assumption, fee basis), name the convention and what the alternative
  would give.

## Register

- Plain and matter-of-fact. No rhetorical construction, no shouty capitals, no
  self-congratulation, no selling.
- State the honest limit of a claim in the body of the slide or table, not in a footnote.
- Think in % moneyness for intuition; compare across different vol levels in delta space.

## Files and durability

- Anything needed to reproduce a number goes in the repo, never in a scratchpad or temp
  folder. Two scratchpads have been lost. The scratchpad is for files nobody will need again.
- Write decisions down when they are made, in the repo's decision log if it has one. Chat
  history compacts and is lost; files are not.
- Naming: what the thing is plus an ISO date or a version handle. Never `final`, `alt`,
  `v2`, `new`, `fixed` in a filename.
- Reusable output templates become personal skills under `~/.claude/skills/`. Check there
  first before building a formatter from scratch.
- Excel workbooks are the default deliverable for tables and comparisons, built with the
  `xlsx-report` skill. Target `.xlsx`, never `.xls`. Write them to a gitignored folder.

## Sessions

- Several Claude Code sessions run on the same repo at once. When Charlie says "we already
  have X" and this session has no record of it, check `git log`, the skills folders and the
  repo before concluding it does not exist.
- Prefer one session per workstream. In a long session, re-read the relevant docs and
  memory files before asserting history, and say plainly when something predates what can
  be seen.
- Always start sessions from the repo folder, so memory and transcripts land in the right
  place.
- Run the `checkpoint` skill at the end of every workstream milestone (any result that
  would be quoted to an investor, any decision that changes a number or convention) and
  before closing a session. It writes decisions and memories to disk at once and lists
  rules, skills and tests for Charlie to approve. Do not wait for compaction; by then the
  detail is gone.

## Git

- Commit only when asked. Never push to a remote Charlie does not own without being asked.
- Before discarding or overwriting, look at what is there. Office metadata churn on `.xlsx`
  files is not unsaved work.
