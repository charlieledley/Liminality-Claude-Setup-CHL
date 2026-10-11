# 03 — Temporal memory

## Implementation brief

**Hand this file to Claude Code and say: "implement this in our repo."**

**Task.** Add an append-only claim store with supersession, and wire the agent to it.

**You need.** Python 3 and a shell. No services, no keys, no database.

**Steps.**
1. Create the store script from the reference implementation below. Pick a path that is
   backed up with the repo, not a temp directory.
2. Reject `--supersedes` without `--reason`. This is not optional; it is what makes the
   chain readable later.
3. Add an `export` command that writes a readable file into wherever the team already
   reads notes (Obsidian, a wiki, a `docs/` file). Export, do not integrate.
4. Add to `CLAUDE.md`: *"When a conclusion is reached, record it. When one is overturned,
   use `--supersedes <id> --reason '...'`. Never edit or delete an entry."*

**Done when.** `history <id>` prints a readable chain, and a conclusion overturned twice is
still fully reconstructible.

**Adapt.** Any language. The design is the file format and the two rules, not the code.

---


## The problem

Yesterday the agent concluded X. Today the evidence says not-X. Both get written down.
Next week it retrieves X and acts on it.

Standard memory tools store facts. They have no concept of a fact being **superseded**,
which is the normal state of affairs in any research project.

## The decision

We evaluated a graph-based temporal memory system. It required Neo4j, an OpenAI key, and
roughly a gigabyte of dependencies.

We took the idea and wrote **130 lines of Python with zero external dependencies**.

> Prefer taking the idea without the dependency when the cost is disproportionate.

That line is now in `CLAUDE.md` as a standing rule.

## The data model

An append-only JSONL file. Nothing is ever deleted or edited.

```json
{"id": 47, "when": "2026-10-08T19:12:03", "text": "...", "tags": ["reversal"],
 "supersedes": 41, "reason": "matched null on leg B"}
```

Four operations:

```bash
claims.py add "..." --supersedes 41 --reason "why"   # record, optionally retiring one
claims.py list                                       # only live claims
claims.py list --all                                 # including superseded
claims.py history 41                                 # the full chain
claims.py md                                         # export to the notes vault
```

## Why supersession matters more than storage

A real example from this project, three claims over six hours:

| | Claim | Outcome |
|---|---|---|
| #41 | Leg B adds genuine alpha | superseded by #48 |
| #48 | Matched null: leg B is not an event | superseded by #49 |
| #49 | Spanning test: leg B does add | superseded by #50 |
| #50 | Replication: a simpler rule captures two thirds of it | live |

Without the chain this is four contradictory notes and no way to tell which one is
current. With the chain it is a visible **line of reasoning**, and `history 41` shows
exactly why each step was retired.

The chain also protects against a specific agent failure: confidently citing a conclusion
that was overturned, because it appeared in the notes.

## Design choices that mattered

- **Append-only.** Overwriting loses the thing that makes it useful.
- **Mandatory reason.** `--supersedes` without `--reason` is rejected. A retirement with
  no stated cause is indistinguishable from an error.
- **Plain text, one file.** Greppable, diffable, survives any tooling change.
- **Export, not integration.** A `md` command writes to the notes vault. The vault never
  becomes a dependency.


## Reference implementation

The whole thing, minus argument parsing. No dependencies beyond the standard library.

```python
import json, os, datetime as dt

STORE = os.path.expanduser("~/claims.jsonl")

def _load():
    if not os.path.exists(STORE): return []
    return [json.loads(l) for l in open(STORE) if l.strip()]

def add(text, supersedes=None, reason=None, tags=()):
    rows = _load()
    if supersedes is not None and not reason:
        raise SystemExit("--supersedes requires --reason")
    rec = {"id": len(rows) + 1,
           "when": dt.datetime.now().isoformat(timespec="seconds"),
           "text": text, "tags": list(tags),
           "supersedes": supersedes, "reason": reason}
    with open(STORE, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["id"]

def live():
    rows = _load()
    retired = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r["id"] not in retired]

def history(cid):
    rows = {r["id"]: r for r in _load()}
    chain, cur = [], cid
    while cur in rows:                       # walk backwards through what it replaced
        chain.append(rows[cur]); cur = rows[cur].get("supersedes")
    forward = {r["supersedes"]: r for r in rows.values() if r.get("supersedes")}
    cur = cid
    while cur in forward:                    # then forwards through what replaced it
        chain.insert(0, forward[cur]); cur = forward[cur]["id"]
    return chain
```

`live()` is the only function the agent calls when recalling. It returns the current state
of knowledge. `history()` is for humans asking how we got here.

### Wiring it to the agent

One line in `CLAUDE.md` is enough:

> When a conclusion is reached, record it with `claims.py add`. When a conclusion is
> overturned, use `--supersedes <id> --reason "..."`. Never edit or delete an entry.

No tool integration, no MCP server, no schema negotiation. The agent already has a shell.

### Cost

130 lines, one file, zero dependencies, and it has survived every change to the rest of
the stack. The graph-database alternative we rejected would have required a running
service, an API key, and a migration path for each of those changes.

## The rule

> When a claim is overturned, record the **supersession**, never a correction. The wrong
> conclusion and the reason it fell are part of the result.
