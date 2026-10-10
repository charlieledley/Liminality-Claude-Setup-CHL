#!/usr/bin/env python
"""Import a claude.ai data export (web/mobile chats) into the Obsidian vault.

Usage:
    python import_claude_chat_export.py PATH [--vault VAULT]

PATH is the zip claude.ai emails after Settings → Privacy → Export data, or an unzipped
folder, or conversations.json itself. projects.json next to it is used when present.

Output (inside the vault):
    Claude/Claude Chat/Claude Chat.md                index of every conversation
    Claude/Claude Chat/Conversations/<date> <name> (<id8>).md
    Claude/Claude Chat/Projects/<name>.md            claude.ai Projects (instructions + docs)

Re-running on a newer export rewrites changed conversations and leaves the rest alone.
Then run sync_claude_to_obsidian.py so the hub links to the index.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_claude_to_obsidian as sync  # reuse vault discovery and helpers

CHAT_DIR = sync.CHAT_DIR
PERSON = sync.PERSON


def load_export(path: Path) -> tuple[list, list]:
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="claude-export-"))
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        path = tmp
    if path.is_file():
        convs = json.loads(path.read_text(encoding="utf-8"))
        proj_file = path.parent / "projects.json"
    else:
        found = list(path.rglob("conversations.json"))
        if not found:
            sys.exit(f"No conversations.json under {path}")
        convs = json.loads(found[0].read_text(encoding="utf-8"))
        proj_file = found[0].parent / "projects.json"
    projects = json.loads(proj_file.read_text(encoding="utf-8")) if proj_file.exists() else []
    return convs, projects


def msg_text(m: dict) -> str:
    parts = []
    content = m.get("content")
    if isinstance(content, list) and content:
        for b in content:
            bt = b.get("type")
            if bt == "text" and b.get("text"):
                parts.append(b["text"])
            elif bt == "tool_use":
                parts.append(f"> [!tools]- tool call: **{b.get('name', '')}**")
            elif bt == "tool_result":
                continue
            elif bt and b.get("text"):
                parts.append(b["text"])
    elif m.get("text"):
        parts.append(m["text"])
    for a in m.get("attachments") or []:
        name = a.get("file_name") or "attachment"
        parts.append(f"*[attachment: {name}]*")
    for f in m.get("files") or []:
        name = f.get("file_name") or "file"
        parts.append(f"*[file: {name}]*")
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def render_conversation(c: dict) -> tuple[str, str, dict]:
    name = (c.get("name") or "").strip() or "Untitled chat"
    uuid = c.get("uuid", "")
    created = sync.local_dt(c.get("created_at"))
    updated = sync.local_dt(c.get("updated_at"))
    date = sync.fmt_dt(created, with_time=False) or "undated"
    note = sync.safe_name(f"{date} {name} ({uuid[:8]})")
    msgs = sorted(c.get("chat_messages") or [], key=lambda m: m.get("created_at") or "")
    prompts = [msg_text(m) for m in msgs if m.get("sender") == "human"]
    prompts = [p for p in prompts if p]
    fm = ["---", f"title: {sync.yaml_str(name)}", "type: claude-chat", f"date: {date}",
          f"created: {sync.yaml_str(sync.fmt_dt(created))}", f"updated: {sync.yaml_str(sync.fmt_dt(updated))}",
          f"messages: {len(msgs)}", f"prompts: {len(prompts)}", f"conversation_id: {uuid}",
          f"url: https://claude.ai/chat/{uuid}", "tags: [claude, claude-chat]", "---",
          f"# {name}", "", f"claude.ai conversation  ·  {date}  ·  {len(msgs)} messages  ·  [Open on claude.ai](https://claude.ai/chat/{uuid})", "",
          "## Prompts", ""]
    for i, p in enumerate(prompts, 1):
        first = p.splitlines()[0]
        fm.append(f"{i}. {first[:137] + '...' if len(first) > 140 else first}")
    fm += ["", "## Transcript", ""]
    n = 0
    for m in msgs:
        t = msg_text(m)
        if not t:
            continue
        ts = sync.local_dt(m.get("created_at"))
        tstr = ts.strftime("%H:%M") if ts else ""
        if m.get("sender") == "human":
            n += 1
            fm += [f"## {n}. {PERSON} — {tstr}", "", sync.demote_headings(t), ""]
        else:
            fm += [f"### Claude — {tstr}", "", sync.demote_headings(t), ""]
    summary = {"note": note, "name": name, "date": date, "updated": sync.fmt_dt(updated), "messages": len(msgs), "uuid": uuid}
    return note, "\n".join(fm).rstrip() + "\n", summary


def render_project(p: dict) -> tuple[str, str]:
    name = (p.get("name") or "Untitled project").strip()
    created = sync.local_dt(p.get("created_at"))
    lines = ["---", f"title: {sync.yaml_str(name)}", "type: claude-chat-project",
             f"created: {sync.yaml_str(sync.fmt_dt(created))}", f"project_id: {p.get('uuid', '')}",
             "tags: [claude, claude-chat, project]", "---", f"# {name}", ""]
    if p.get("description"):
        lines += [p["description"].strip(), ""]
    if p.get("prompt_template"):
        lines += ["## Instructions", "", sync.demote_headings(p["prompt_template"].strip()), ""]
    docs = p.get("docs") or []
    if docs:
        lines += ["## Project knowledge", ""]
        for d in docs:
            lines += [f"### {d.get('filename') or 'document'}", "", sync.demote_headings((d.get('content') or '').strip()), ""]
    return sync.safe_name(name), "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--vault")
    args = ap.parse_args()
    sync.ARGS = argparse.Namespace(vault=args.vault, force=False, quiet=False)
    vault = sync.find_vault()
    convs, projects = load_export(Path(args.path))

    out = vault / CHAT_DIR
    summaries = []
    written = 0
    for c in convs:
        note, text, summary = render_conversation(c)
        folder = out / "Conversations"
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob(f"* ({summary['uuid'][:8]}).md"):
            if old.stem != note:
                old.unlink()
        written += sync.write_if_changed(folder / f"{note}.md", text)
        summaries.append(summary)
    proj_names = []
    for p in projects:
        name, text = render_project(p)
        sync.write_if_changed(out / "Projects" / f"{name}.md", text)
        proj_names.append(name)

    summaries.sort(key=lambda s: s["date"], reverse=True)
    now = sync.fmt_dt(dt.datetime.now().astimezone())
    lines = ["---", "title: Claude Chat", "type: index", f"last_imported: {sync.yaml_str(now)}",
             f"conversations: {len(summaries)}", "tags: [claude, claude-chat, index]", "---", "# Claude Chat", "",
             f"claude.ai web and mobile conversations from the data export, imported {now}. Source: `{args.path}`.", ""]
    if proj_names:
        lines += ["## Projects", ""] + [f"- [[{n}]]" for n in sorted(proj_names)] + [""]
    lines += ["## Conversations", "", "| Date | Conversation | Messages | Updated |", "|---|---|---:|---|"]
    for s in summaries:
        lines.append(f"| {s['date']} | [[{s['note']}]] | {s['messages']} | {s['updated']} |")
    sync.write_if_changed(out / "Claude Chat.md", "\n".join(lines) + "\n")
    print(f"Imported {len(summaries)} conversations ({written} written or updated) and {len(proj_names)} projects into {out}")
    print("Now run sync_claude_to_obsidian.py so the hub links to the index.")


if __name__ == "__main__":
    main()
