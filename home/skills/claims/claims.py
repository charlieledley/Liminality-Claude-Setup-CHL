#!/usr/bin/env python
"""Append-only store of research conclusions, with supersession.

A claim is a conclusion drawn from evidence ("the 12m expiry earns 14% more gross than 6m on
2007-2026"). When later evidence overturns it, the new conclusion is added with
--supersedes <id> --reason "...". Nothing is ever edited or deleted, so the line of reasoning
stays readable and an overturned conclusion can never be cited as current by accident.

Usage (standard library only):
    python claims.py add "text" [--supersedes ID --reason "why"] [--tag T ...]
    python claims.py list [--all] [--tag T]        live claims; --all marks superseded ones
    python claims.py history ID                     the full chain through ID, oldest first
    python claims.py show ID
    python claims.py md [--vault PATH]              export to the Obsidian vault (Claude/Claims/)
    python claims.py where                          print the store path in use

Store: <git root>/docs/claims.jsonl when run inside a repo (tracked, backed up with it);
otherwise ~/.claude/claims.jsonl. Override with --store PATH or the CLAIMS_STORE variable.
Decisions and conventions still live in docs/decisions/; a claim that becomes one names its
decision file in the text.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = "Claude"


# ----------------------------------------------------------------------------- store
def find_store(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("CLAIMS_STORE")
    if env:
        return Path(env)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()) / "docs" / "claims.jsonl"
    except Exception:
        pass
    return Path.home() / ".claude" / "claims.jsonl"


def load(store: Path) -> list[dict]:
    if not store.exists():
        return []
    rows = []
    with open(store, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def add(store: Path, text: str, supersedes: int | None = None, reason: str | None = None, tags=()) -> dict:
    text = " ".join(text.split())
    if not text:
        raise SystemExit("claims: empty text")
    rows = load(store)
    if supersedes is not None:
        if not reason or not reason.strip():
            raise SystemExit("claims: --supersedes requires --reason")
        by_id = {r["id"]: r for r in rows}
        if supersedes not in by_id:
            raise SystemExit(f"claims: no claim #{supersedes} in {store}")
        retired_by = {r["supersedes"]: r["id"] for r in rows if r.get("supersedes")}
        if supersedes in retired_by:
            head = supersedes
            while head in retired_by:
                head = retired_by[head]
            raise SystemExit(f"claims: #{supersedes} is already superseded; the live end of that chain is #{head}, supersede that one")
    rec = {
        "id": (max((r["id"] for r in rows), default=0) + 1),
        "when": dt.datetime.now().isoformat(timespec="seconds"),
        "text": text,
        "tags": sorted({t.strip() for t in tags if t.strip()}),
        "supersedes": supersedes,
        "reason": " ".join(reason.split()) if reason else None,
    }
    store.parent.mkdir(parents=True, exist_ok=True)
    with open(store, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def live(rows: list[dict]) -> list[dict]:
    retired = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r["id"] not in retired]


def history(rows: list[dict], cid: int) -> list[dict]:
    """The whole chain that passes through cid, oldest first."""
    by_id = {r["id"]: r for r in rows}
    if cid not in by_id:
        return []
    forward = {r["supersedes"]: r for r in rows if r.get("supersedes")}
    chain, cur = [], cid
    while cur in by_id:  # backwards through what it replaced
        chain.append(by_id[cur])
        cur = by_id[cur].get("supersedes")
    chain.reverse()
    cur = cid
    while cur in forward:  # forwards through what replaced it
        chain.append(forward[cur])
        cur = forward[cur]["id"]
    return chain


# ----------------------------------------------------------------------------- output
def fmt(r: dict, retired_by: dict | None = None) -> str:
    tags = f"  [{', '.join(r['tags'])}]" if r.get("tags") else ""
    sup = f"  (supersedes #{r['supersedes']}: {r['reason']})" if r.get("supersedes") else ""
    gone = f"  -> superseded by #{retired_by[r['id']]}" if retired_by and r["id"] in retired_by else ""
    return f"#{r['id']}  {r['when'][:16].replace('T', ' ')}  {r['text']}{tags}{sup}{gone}"


def render_md(rows: list[dict], name: str, store: Path) -> str:
    retired_by = {r["supersedes"]: r["id"] for r in rows if r.get("supersedes")}
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    lv = live(rows)
    q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'
    out = ["---", f"title: {q('Claims: ' + name)}", "type: claims", f"store: {q(store)}", f"live: {len(lv)}",
           f"total: {len(rows)}", f"last_exported: {q(now)}", "tags: [claude, claims]", "---",
           f"# Claims: {name}", "",
           "Append-only record of research conclusions. A superseded claim stays here with the reason it fell; "
           "only the live ones are current knowledge. Exported from the claim store, not edited here.", "",
           "## Live claims", ""]
    if not lv:
        out.append("None yet.")
    for r in reversed(lv):
        tags = f" `{'` `'.join(r['tags'])}`" if r.get("tags") else ""
        sup = f" (supersedes #{r['supersedes']}: {r['reason']})" if r.get("supersedes") else ""
        out.append(f"- **#{r['id']}** {r['when'][:10]} — {r['text']}{tags}{sup}")
    chains = []
    for r in rows:
        if r.get("supersedes") is None and r["id"] in retired_by:
            chains.append(history(rows, r["id"]))
    if chains:
        out += ["", "## Lines of reasoning", "", "Each chain oldest first; the last entry is the live conclusion."]
        for ch in chains:
            out.append("")
            for i, r in enumerate(ch):
                arrow = "" if i == 0 else f"   ↳ because: {r['reason']}\n"
                out.append(f"{arrow}- #{r['id']} {r['when'][:10]} — {r['text']}" + ("" if r["id"] not in retired_by else "  *(superseded)*"))
    out += ["", "## Every entry, newest first", "", "| id | when | status | claim | supersedes | reason |", "|---|---|---|---|---|---|"]
    for r in reversed(rows):
        status = f"superseded by #{retired_by[r['id']]}" if r["id"] in retired_by else "live"
        cell = lambda s: str(s or "").replace("|", "\\|").replace("\n", " ")
        out.append(f"| {r['id']} | {r['when'][:16].replace('T', ' ')} | {status} | {cell(r['text'])} | {('#' + str(r['supersedes'])) if r.get('supersedes') else ''} | {cell(r.get('reason'))} |")
    return "\n".join(out) + "\n"


def find_vault(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env)
    cfg = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "obsidian" / "obsidian.json"
    if cfg.exists():
        vaults = json.loads(cfg.read_text(encoding="utf-8")).get("vaults", {})
        opened = [v for v in vaults.values() if v.get("open")] or list(vaults.values())
        if opened:
            return Path(opened[0]["path"])
    raise SystemExit("claims: no Obsidian vault found; pass --vault PATH")


def store_name(store: Path) -> str:
    if store.parent.name == "docs":
        return store.parent.parent.name
    if store.parent == Path.home() / ".claude":
        return "General"
    return store.parent.name


def export_md(store: Path, vault: Path) -> Path:
    rows = load(store)
    name = store_name(store)
    safe = re.sub(r'[\\/:*?"<>|#^\[\]]', "-", name).strip(" .-") or "claims"
    target = vault / ROOT / "Claims" / f"Claims - {safe}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = render_md(rows, name, store)
    if not target.exists() or target.read_text(encoding="utf-8") != text:
        target.write_text(text, encoding="utf-8", newline="\n")
    return target


# ----------------------------------------------------------------------------- cli
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", help="claim store path (default: <git root>/docs/claims.jsonl, else ~/.claude/claims.jsonl)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="record a conclusion")
    a.add_argument("text")
    a.add_argument("--supersedes", type=int, metavar="ID")
    a.add_argument("--reason", help="why the superseded claim fell (required with --supersedes)")
    a.add_argument("--tag", action="append", default=[], metavar="T")
    l = sub.add_parser("list", help="live claims")
    l.add_argument("--all", action="store_true")
    l.add_argument("--tag")
    h = sub.add_parser("history", help="the chain through a claim")
    h.add_argument("id", type=int)
    s = sub.add_parser("show", help="one claim")
    s.add_argument("id", type=int)
    m = sub.add_parser("md", help="export to the Obsidian vault")
    m.add_argument("--vault")
    sub.add_parser("where", help="print the store path")
    args = ap.parse_args(argv)

    store = find_store(args.store)
    if args.cmd == "where":
        print(store)
        return 0
    if args.cmd == "add":
        rec = add(store, args.text, args.supersedes, args.reason, args.tag)
        print(f"recorded #{rec['id']} in {store}")
        return 0
    rows = load(store)
    retired_by = {r["supersedes"]: r["id"] for r in rows if r.get("supersedes")}
    if args.cmd == "list":
        sel = rows if args.all else live(rows)
        if args.tag:
            sel = [r for r in sel if args.tag in r.get("tags", [])]
        if not sel:
            print(f"no claims in {store}")
        for r in sel:
            print(fmt(r, retired_by))
        return 0
    if args.cmd == "show":
        r = next((r for r in rows if r["id"] == args.id), None)
        if not r:
            raise SystemExit(f"claims: no claim #{args.id}")
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "history":
        chain = history(rows, args.id)
        if not chain:
            raise SystemExit(f"claims: no claim #{args.id} in {store}")
        for i, r in enumerate(chain):
            if i:
                print(f"    because: {r['reason']}")
            print(fmt(r, retired_by))
        return 0
    if args.cmd == "md":
        target = export_md(store, find_vault(args.vault))
        print(f"exported {len(rows)} claims to {target}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
