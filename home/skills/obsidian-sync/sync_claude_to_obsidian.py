#!/usr/bin/env python
"""Mirror every Claude Code session, Cowork session, memory file and skill on this PC into an
Obsidian vault as linked markdown notes.

Usage:
    python sync_claude_to_obsidian.py [--vault PATH] [--force] [--quiet]

Sources (all read-only):
    ~/.claude/projects/<cwd-slug>/<session>.jsonl            Claude Code transcripts
    ~/.claude/projects/<cwd-slug>/memory/*.md                 per-project memory
    %APPDATA%/Claude/claude-code-sessions/*/*/local_*.json    app titles, ids, archive flag
    %APPDATA%/Claude/local-agent-mode-sessions/*/*/local_*.json + <id8>/.claude/projects/session/*.jsonl
                                                              Cowork (desktop chat, agent mode)
    ~/.claude/skills/*/SKILL.md, ~/.claude/CLAUDE.md          skills and global instructions

Output (inside the vault):
    Claude/Claude.md                      hub
    Claude/Timeline.md                    every session by date
    Claude/Claude Code/Projects/*.md      one note per project folder
    Claude/Claude Code/Sessions/*.md      one note per transcript
    Claude/Claude Code/Memory/<project>/  copies of the memory files (wikilinks preserved)
    Claude/Claude Code/Skills/*.md        copies of SKILL.md
    Claude/Cowork/Sessions/*.md           one note per Cowork transcript
    Claude/Claude Chat/                   written by import_claude_chat_export.py, linked from the hub

Unchanged transcripts are skipped using Claude/.sync-state.json; --force rebuilds everything.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HOME = Path.home()
APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
CLAUDE_HOME = HOME / ".claude"
APP_DIR = APPDATA / "Claude"
SYNC_VERSION = 5  # bump when the note format changes so --force is implied

ROOT = "Claude"
CC_DIR = f"{ROOT}/Claude Code"
COWORK_DIR = f"{ROOT}/Cowork"
CHAT_DIR = f"{ROOT}/Claude Chat"

PERSON = "Charlie"


# ----------------------------------------------------------------------------- helpers
def log(msg: str) -> None:
    if not ARGS.quiet:
        print(msg)


def find_vault() -> Path:
    if ARGS.vault:
        return Path(ARGS.vault)
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env)
    cfg = APPDATA / "obsidian" / "obsidian.json"
    if cfg.exists():
        vaults = json.loads(cfg.read_text(encoding="utf-8")).get("vaults", {})
        opened = [v for v in vaults.values() if v.get("open")] or list(vaults.values())
        if opened:
            return Path(opened[0]["path"])
    sys.exit("No Obsidian vault found: pass --vault PATH")


def safe_name(s: str, limit: int = 90) -> str:
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', "-", s)
    s = re.sub(r"\s+", " ", s).strip(" .-")
    return (s[:limit].rstrip(" .-")) or "untitled"


def local_dt(iso: str | None) -> dt.datetime | None:
    if not iso:
        return None
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone()


def fmt_dt(d: dt.datetime | None, with_time: bool = True) -> str:
    if not d:
        return ""
    return d.strftime("%Y-%m-%d %H:%M") if with_time else d.strftime("%Y-%m-%d")


def ms_to_dt(ms) -> dt.datetime | None:
    if not ms:
        return None
    return dt.datetime.fromtimestamp(ms / 1000).astimezone()


def file_url(p: str | Path) -> str:
    s = str(p).replace("\\", "/")
    if not s.startswith("/"):
        s = "/" + s
    from urllib.parse import quote
    return "file://" + quote(s, safe="/:")


def demote_headings(text: str) -> str:
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^#{1,6}\s", line):
            line = "##" + line
            line = re.sub(r"^#{7,}", "######", line)
        out.append(line)
    return "\n".join(out)


def yaml_str(s) -> str:
    if s is None:
        return '""'
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


TAG_STRIP = [
    (re.compile(r"<system-reminder>.*?</system-reminder>", re.S), ""),
    (re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.S), ""),
    (re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.S), ""),
    (re.compile(r"<command-message>.*?</command-message>", re.S), ""),
    (re.compile(r"<uploaded_files>.*?</uploaded_files>", re.S), "[uploaded files]"),
    (re.compile(r"</?pasted_content[^>]*>"), ""),
]


def clean_user_text(t: str) -> str:
    m = re.search(r"<command-name>(.*?)</command-name>", t, re.S)
    if m:
        args = re.search(r"<command-args>(.*?)</command-args>", t, re.S)
        cmd = m.group(1).strip()
        if args and args.group(1).strip():
            cmd += " " + args.group(1).strip()
        return f"`{cmd}`"
    for rx, rep in TAG_STRIP:
        t = rx.sub(rep, t)
    t = t.strip()
    if t.startswith("Base directory for this skill:"):
        return ""
    # a message that is nothing but one XML-style wrapper is machine traffic (task
    # notifications, CI events, hook output), not something the person typed
    if re.fullmatch(r"<([A-Za-z_][\w-]*)[^>]*>.*</\1>", t, re.S) or re.fullmatch(r"<[A-Za-z_][\w-]*[^>]*/?>", t):
        return ""
    return t


def tool_summary(name: str, inp: dict) -> str:
    short = re.sub(r"^mcp__[^_]+(?:_[^_]+)*?__", "", name) if name.startswith("mcp__") else name
    if name.startswith("mcp__"):
        parts = name.split("__")
        short = parts[-1]
        if len(parts) >= 3 and not re.fullmatch(r"[0-9a-f-]{20,}", parts[1]):
            short = f"{parts[1]}:{parts[-1]}"
    inp = inp or {}

    def first(*keys):
        for k in keys:
            v = inp.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    desc = first("description", "file_path", "notebook_path", "pattern", "url", "query", "skill", "prompt", "command", "title", "path")
    if not desc:
        for v in inp.values():
            if isinstance(v, str) and v.strip():
                desc = v.strip()
                break
    desc = desc.splitlines()[0] if desc else ""
    if len(desc) > 110:
        desc = desc[:107] + "..."
    desc = desc.replace("|", "\\|")
    return f"**{short}** {desc}".rstrip()


# ----------------------------------------------------------------------------- app metadata
def load_app_sessions() -> dict[str, dict]:
    """cliSessionId -> app record (Claude Code sessions)."""
    out = {}
    for f in glob.glob(str(APP_DIR / "claude-code-sessions" / "*" / "*" / "local_*.json")):
        try:
            o = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        cli = o.get("cliSessionId")
        if cli:
            out[cli] = o
    return out


def load_cowork_sessions() -> list[tuple[dict, Path]]:
    """(app record, transcript path) for each Cowork session that has a transcript."""
    out = []
    for f in glob.glob(str(APP_DIR / "local-agent-mode-sessions" / "*" / "*" / "local_*.json")):
        try:
            o = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = o.get("sessionId", "")
        id8 = sid.replace("local_", "")[:8]
        cli = o.get("cliSessionId")
        if not cli:
            continue
        t = Path(f).parent / id8 / ".claude" / "projects" / "session" / f"{cli}.jsonl"
        if t.exists():
            out.append((o, t))
    return out


# ----------------------------------------------------------------------------- transcript parsing
class Session:
    def __init__(self, path: Path, kind: str, app: dict | None):
        self.path = path
        self.kind = kind  # "claude-code" | "cowork"
        self.app = app or {}
        self.id = path.stem
        self.id8 = self.id[:8]
        self.title = self.app.get("title") or ""
        self.cwd = self.app.get("cwd") or ""
        self.branches: list[str] = []
        self.models: set[str] = set()
        self.first_ts: dt.datetime | None = None
        self.last_ts: dt.datetime | None = None
        self.cost: dict = {}
        self.prompts: list[str] = []
        self.turns: list = []  # ("user", ts, text) | ("assistant", ts, text, [tools]) | ("compact", ts, summary)
        self.tool_calls = 0
        self.files_touched: dict[str, int] = defaultdict(int)
        self.artifacts: dict[str, str] = {}
        self.sidechain_records = 0
        self.root_uuid = ""
        self.compactions = 0
        self.version = ""

    # -- parse
    def parse(self) -> None:
        cur_assist = None
        with open(self.path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = o.get("type")
                if t == "custom-title" and o.get("customTitle"):
                    self.title = self.title or o["customTitle"]
                    if not self.app:
                        self.title = o["customTitle"]
                elif t == "agent-name" and not self.title:
                    self.title = o.get("agentName") or ""
                elif t == "cost-state":
                    self.cost = o
                elif t == "frame-link":
                    if o.get("frameUrl"):
                        self.artifacts[o["frameUrl"]] = o.get("title") or o["frameUrl"]
                if t not in ("user", "assistant", "system"):
                    continue
                if o.get("isSidechain"):
                    self.sidechain_records += 1
                    continue
                ts = local_dt(o.get("timestamp"))
                if ts:
                    self.first_ts = self.first_ts or ts
                    self.last_ts = ts
                if o.get("cwd") and not self.cwd:
                    self.cwd = o["cwd"]
                gb = o.get("gitBranch")
                if gb and gb not in self.branches:
                    self.branches.append(gb)
                if o.get("version"):
                    self.version = o["version"]

                if t == "system":
                    if o.get("subtype") == "compact_boundary":
                        self.compactions += 1
                        self.turns.append(("compact", ts, ""))
                        cur_assist = None
                    continue

                msg = o.get("message") or {}
                content = msg.get("content")
                if t == "user":
                    if not self.root_uuid and o.get("uuid"):
                        self.root_uuid = o["uuid"]
                    if o.get("isMeta"):
                        continue
                    texts = []
                    if isinstance(content, str):
                        texts.append(clean_user_text(content))
                    elif isinstance(content, list):
                        for b in content:
                            bt = b.get("type")
                            if bt == "text":
                                texts.append(clean_user_text(b.get("text", "")))
                            elif bt == "image":
                                texts.append("*[image attached]*")
                            elif bt == "document":
                                texts.append("*[document attached]*")
                    text = "\n\n".join(x for x in texts if x).strip()
                    if not text:
                        continue
                    if o.get("isCompactSummary"):
                        if self.turns and self.turns[-1][0] == "compact":
                            self.turns[-1] = ("compact", ts, text)
                        else:
                            self.turns.append(("compact", ts, text))
                        cur_assist = None
                        continue
                    self.prompts.append(text)
                    self.turns.append(("user", ts, text))
                    cur_assist = None
                elif t == "assistant":
                    if msg.get("model"):
                        self.models.add(msg["model"])
                    if cur_assist is None:
                        cur_assist = ["assistant", ts, [], []]
                        self.turns.append(cur_assist)
                    if isinstance(content, list):
                        for b in content:
                            bt = b.get("type")
                            if bt == "text" and b.get("text", "").strip():
                                cur_assist[2].append(b["text"].strip())
                            elif bt == "tool_use":
                                self.tool_calls += 1
                                name = b.get("name", "")
                                inp = b.get("input") or {}
                                cur_assist[3].append(tool_summary(name, inp))
                                fp = inp.get("file_path") or inp.get("notebook_path")
                                if name in ("Edit", "Write", "NotebookEdit", "MultiEdit") and fp:
                                    self.files_touched[fp] += 1
                    elif isinstance(content, str) and content.strip():
                        cur_assist[2].append(content.strip())
        if not self.title:
            self.title = (self.prompts[0].splitlines()[0][:60] if self.prompts else "untitled")
        self.title = re.sub(r"\s+", " ", self.title).strip()

    # -- derived
    @property
    def project(self) -> str:
        if self.kind == "cowork":
            return "Cowork"
        c = self.cwd.replace("/", "\\")
        if "scratch-workspaces" in c:
            return "Scratch workspaces"
        return c.rstrip("\\").split("\\")[-1] or "Unknown"

    @property
    def date(self) -> str:
        d = ms_to_dt(self.app.get("createdAt")) or self.first_ts
        return fmt_dt(d, with_time=False) or "undated"

    @property
    def note_name(self) -> str:
        return safe_name(f"{self.date} {self.title} ({self.id8})")

    @property
    def link(self) -> str:
        return f"[[{self.note_name}]]"

    @property
    def app_link(self) -> str:
        sid = self.app.get("sessionId")
        return f"claude://claude.ai/epitaxy/{sid}" if sid else ""

    def summary(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "title": self.title, "project": self.project,
            "date": self.date, "note": self.note_name, "start": fmt_dt(self.first_ts),
            "end": fmt_dt(self.last_ts), "prompts": len(self.prompts), "tool_calls": self.tool_calls,
            "cost": round(self.cost.get("totalCostUSD", 0) or 0, 2), "archived": bool(self.app.get("isArchived")),
            "app_link": self.app_link, "root_uuid": self.root_uuid, "cwd": self.cwd,
            "files": sorted(self.files_touched, key=lambda k: -self.files_touched[k])[:40],
            "artifacts": self.artifacts, "models": sorted(self.models), "source": str(self.path),
        }

    # -- render
    def render(self, siblings: list[str]) -> str:
        s = self.summary()
        tags = ["claude", "claude-code" if self.kind == "claude-code" else "cowork", "project/" + safe_name(self.project).lower().replace(" ", "-")]
        fm = [
            "---",
            f"title: {yaml_str(self.title)}",
            f"type: {'claude-code-session' if self.kind == 'claude-code' else 'cowork-session'}",
            f"project: {yaml_str('[[' + safe_name(self.project) + ']]')}",
            f"date: {self.date}",
            f"started: {yaml_str(s['start'])}",
            f"ended: {yaml_str(s['end'])}",
            f"prompts: {s['prompts']}",
            f"tool_calls: {s['tool_calls']}",
            f"compactions: {self.compactions}",
            f"cost_usd: {s['cost'] if s['cost'] else ''}",
            f"model: {yaml_str(', '.join(s['models']))}",
            f"git_branch: {yaml_str(', '.join(self.branches))}",
            f"session_id: {self.id}",
            f"app_session_id: {yaml_str(self.app.get('sessionId', ''))}",
            f"archived: {str(s['archived']).lower()}",
            f"cwd: {yaml_str(self.cwd)}",
            f"source: {yaml_str(self.path)}",
            f"last_synced: {yaml_str(fmt_dt(dt.datetime.now().astimezone()))}",
            "tags: [" + ", ".join(tags) + "]",
            "---",
        ]
        head = [f"# {self.title}", ""]
        meta = [f"Project: [[{safe_name(self.project)}]]  ·  {self.date}  ·  {s['prompts']} prompts, {s['tool_calls']} tool calls"]
        if self.app_link:
            meta.append(f"[Open in Claude app]({self.app_link})")
        meta.append(f"[Transcript on disk]({file_url(self.path)})")
        head.append("  ·  ".join(meta))
        if s["cost"]:
            head.append(f"\nAPI cost recorded by the app: USD {s['cost']:.2f} (from the transcript's cost-state line; the app's own figure, not audited).")
        if siblings:
            head.append("\nShares its opening history with (resumed or forked session): " + ", ".join(f"[[{x}]]" for x in siblings))
        if self.sidechain_records:
            head.append(f"\nSub-agent traffic omitted: {self.sidechain_records} records.")

        body = ["", "## Prompts", ""]
        for i, p in enumerate(self.prompts, 1):
            first = p.strip().splitlines()[0]
            if len(first) > 140:
                first = first[:137] + "..."
            body.append(f"{i}. {first}")

        if self.files_touched:
            body += ["", "## Files written or edited", ""]
            for fp in s["files"]:
                body.append(f"- [{fp}]({file_url(fp)}) ×{self.files_touched[fp]}")
        if self.artifacts:
            body += ["", "## Artifacts", ""]
            for url, title in self.artifacts.items():
                body.append(f"- [{title}]({url})")

        body += ["", "## Transcript", "", "Tool results, thinking and sub-agent traffic are left out; the full record is the transcript on disk.", ""]
        n = 0
        for turn in self.turns:
            kind, ts = turn[0], turn[1]
            tstr = ts.strftime("%H:%M") if ts else ""
            if kind == "user":
                n += 1
                body += [f"## {n}. {PERSON} — {tstr}", "", demote_headings(turn[2]), ""]
            elif kind == "assistant":
                texts, tools = turn[2], turn[3]
                body += [f"### Claude — {tstr}", ""]
                if tools:
                    body.append(f"> [!tools]- {len(tools)} tool call{'s' if len(tools) != 1 else ''}")
                    for tl in tools:
                        body.append(f"> - {tl}")
                    body.append("")
                if texts:
                    body += [demote_headings("\n\n".join(texts)), ""]
            elif kind == "compact":
                body.append("> [!abstract]- Context compacted here" + (" — summary carried forward" if turn[2] else ""))
                for ln in (turn[2] or "").splitlines():
                    body.append("> " + ln)
                body.append("")
        return "\n".join(fm + head + body).rstrip() + "\n"


# ----------------------------------------------------------------------------- vault writers
def write_if_changed(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def copy_memory(vault: Path) -> dict[str, list[str]]:
    """Copy memory folders; returns project -> list of memory note names."""
    out: dict[str, list[str]] = {}
    for mdir in sorted(glob.glob(str(CLAUDE_HOME / "projects" / "*" / "memory"))):
        mdir = Path(mdir)
        slug = mdir.parent.name
        if "scratch-workspaces" in slug:
            proj = "Scratch workspaces"
            sub = slug.rsplit("-scratch-", 1)[-1] if "-scratch-" in slug else slug[-20:]
            target = vault / CC_DIR / "Memory" / proj / sub
        else:
            proj = slug.split("--", 1)[-1] if "--" in slug else slug
            target = vault / CC_DIR / "Memory" / proj
        files = sorted(mdir.glob("*.md"))
        if not files:
            continue
        for f in files:
            write_if_changed(target / f.name, f.read_text(encoding="utf-8", errors="replace"))
        out.setdefault(proj, []).extend(str((target / f.name).relative_to(vault / CC_DIR / "Memory")) for f in files)
    return out


def copy_skills(vault: Path) -> list[str]:
    names = []
    for f in sorted(glob.glob(str(CLAUDE_HOME / "skills" / "*" / "SKILL.md"))):
        name = Path(f).parent.name
        text = Path(f).read_text(encoding="utf-8", errors="replace")
        notice = f"\n> Copy of `{f}`. Edit the original, not this note.\n"
        end = text.find("\n---", 3) if text.startswith("---") else -1
        if end != -1:
            text = text[: end + 4] + notice + text[end + 4 :]
        else:
            text = notice.lstrip("\n") + "\n" + text
        write_if_changed(vault / CC_DIR / "Skills" / f"{name}.md", text)
        names.append(name)
    g = CLAUDE_HOME / "CLAUDE.md"
    if g.exists():
        write_if_changed(vault / CC_DIR / "Global instructions (CLAUDE.md).md",
                         f"> Copy of `{g}`. Edit the original, not this note.\n\n" + g.read_text(encoding="utf-8", errors="replace"))
    return names


def copy_agents(vault: Path) -> list[str]:
    names = []
    for f in sorted(glob.glob(str(CLAUDE_HOME / "agents" / "*.md"))):
        name = Path(f).stem
        text = Path(f).read_text(encoding="utf-8", errors="replace")
        notice = f"\n> Copy of `{f}`. Edit the original, not this note.\n"
        end = text.find("\n---", 3) if text.startswith("---") else -1
        text = text[: end + 4] + notice + text[end + 4 :] if end != -1 else notice.lstrip("\n") + "\n" + text
        write_if_changed(vault / CC_DIR / "Agents" / f"{name}.md", text)
        names.append(name)
    return names


def copy_docs(vault: Path) -> list[tuple[str, str]]:
    """Reference documents in ~/.claude/docs -> Claude/Reference. Returns (note name, title)."""
    out = []
    for f in sorted(glob.glob(str(CLAUDE_HOME / "docs" / "*.md"))):
        text = Path(f).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else Path(f).stem
        note = safe_name(title)
        fm = ["---", f"title: {yaml_str(title)}", "type: reference", f"source: {yaml_str(f)}",
              f"last_synced: {yaml_str(fmt_dt(dt.datetime.now().astimezone()))}", "tags: [claude, reference]", "---", ""]
        write_if_changed(vault / ROOT / "Reference" / f"{note}.md", "\n".join(fm) + text)
        out.append((note, title))
    return out


def export_claims(vault: Path, cwds: set[str]) -> list[tuple[str, str]]:
    """Render every claim store (per repo docs/claims.jsonl, plus the general one) via the claims skill.
    Returns (project name, note name)."""
    sys.path.insert(0, str(CLAUDE_HOME / "skills" / "claims"))
    try:
        import claims  # noqa: WPS433
    except ImportError:
        return []
    stores = [Path(c) / "docs" / "claims.jsonl" for c in sorted(cwds) if c and "scratch-workspaces" not in c]
    stores.append(CLAUDE_HOME / "claims.jsonl")
    out = []
    for st in stores:
        if st.exists():
            target = claims.export_md(st, vault)
            out.append((claims.store_name(st), target.stem))
            log(f"  claims   {target.name}")
    return out


def repo_docs(cwd: str) -> list[tuple[str, str]]:
    """Markdown/HTML/PDF documents inside a project folder worth linking (docs/, README, CLAUDE.md)."""
    if not cwd or "scratch-workspaces" in cwd:
        return []
    root = Path(cwd)
    if not root.exists():
        return []
    out = []
    for name in ("README.md", "CLAUDE.md"):
        if (root / name).exists():
            out.append((name, str(root / name)))
    docs = root / "docs"
    if docs.exists():
        for f in sorted(docs.rglob("*")):
            if f.suffix.lower() in (".md", ".html", ".pdf") and f.is_file():
                out.append((str(f.relative_to(root)).replace("\\", "/"), str(f)))
    return out[:300]


def write_project_notes(vault: Path, sessions: list[dict], memory: dict[str, list[str]], claims: list[tuple[str, str]] = ()) -> list[str]:
    claim_notes = dict(claims)
    by_proj: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        by_proj[s["project"]].append(s)
    for proj in memory:
        by_proj.setdefault(proj, [])
    names = []
    for proj, ss in sorted(by_proj.items()):
        ss.sort(key=lambda x: x["date"], reverse=True)
        cwds = sorted({s["cwd"] for s in ss if s["cwd"]})
        kind = "cowork" if proj == "Cowork" else "claude-code"
        lines = ["---", f"title: {yaml_str(proj)}", "type: project", f"sessions: {len(ss)}",
                 f"last_activity: {yaml_str(ss[0]['end'] if ss else '')}",
                 f"last_synced: {yaml_str(fmt_dt(dt.datetime.now().astimezone()))}",
                 f"tags: [claude, project, {kind}]", "---", f"# {proj}", ""]
        if proj == "Cowork":
            lines.append("Chats run in the Claude desktop app with agent mode (Cowork). Transcripts live under the app's local-agent-mode-sessions folder.")
        elif proj == "Scratch workspaces":
            lines.append("Sessions started without a project folder. Each has its own throwaway workspace; anything worth keeping was moved elsewhere.")
        else:
            for c in cwds:
                lines.append(f"Folder: [{c}]({file_url(c)})")
        if ss:
            total_cost = sum(s["cost"] for s in ss)
            lines += ["", "## Sessions", "", "| Date | Session | Prompts | Tool calls | Cost (USD) | |", "|---|---|---:|---:|---:|---|"]
            for s in ss:
                flag = "archived" if s["archived"] else ""
                cost = f"{s['cost']:.2f}" if s["cost"] else ""
                lines.append(f"| {s['date']} | [[{s['note']}]] | {s['prompts']} | {s['tool_calls']} | {cost} | {flag} |")
            lines.append(f"\nCost column is the app's own running total per transcript (blank where the app recorded none), summed here to {total_cost:.2f}; it is a usage figure, not an audited one.")
        if proj in claim_notes:
            lines += ["", "## Claims", "", f"Research conclusions and the line of reasoning behind them: [[{claim_notes[proj]}]]."]
        if proj in memory:
            lines += ["", "## Memory", "", "Facts, feedback and decisions Claude keeps between sessions for this project (copies; the originals are in the Claude memory folder).", ""]
            for rel in sorted(memory[proj]):
                stem = Path(rel).stem
                lines.append(f"- [[{stem}]]" if stem != "MEMORY" else f"- [[{CC_DIR}/Memory/{rel[:-3].replace(os.sep, '/')}|Memory index]]")
        # files touched across sessions
        touched: dict[str, int] = defaultdict(int)
        for s in ss:
            for f in s["files"]:
                touched[f] += 1
        if touched:
            lines += ["", "## Files Claude wrote or edited", ""]
            for f, n in sorted(touched.items(), key=lambda kv: (-kv[1], kv[0]))[:60]:
                lines.append(f"- [{f}]({file_url(f)}) ({n} session{'s' if n != 1 else ''})")
        docs = []
        for c in cwds:
            docs += repo_docs(c)
        if docs:
            lines += ["", "## Documents in the repo", "", "Links to the repo's own docs (decision log, plans, handovers). The repo is the source of truth; nothing is copied.", ""]
            for rel, full in docs:
                lines.append(f"- [{rel}]({file_url(full)})")
        arts = {}
        for s in ss:
            arts.update(s["artifacts"])
        if arts:
            lines += ["", "## Artifacts published", ""]
            for url, title in arts.items():
                lines.append(f"- [{title}]({url})")
        write_if_changed(vault / CC_DIR / "Projects" / f"{safe_name(proj)}.md", "\n".join(lines) + "\n")
        names.append(proj)
    return names


def write_hub(vault: Path, sessions: list[dict], projects: list[str], memory: dict[str, list[str]], skills: list[str],
              agents: list[str] = (), docs: list[tuple[str, str]] = (), claims: list[tuple[str, str]] = ()) -> None:
    now = fmt_dt(dt.datetime.now().astimezone())
    cc = [s for s in sessions if s["kind"] == "claude-code"]
    cw = [s for s in sessions if s["kind"] == "cowork"]
    recent = sorted(sessions, key=lambda s: s["end"] or s["date"], reverse=True)[:15]
    chat_index = vault / CHAT_DIR / "Claude Chat.md"
    lines = ["---", "title: Claude", "type: hub", f"last_synced: {yaml_str(now)}", "tags: [claude, hub]", "---",
             "# Claude", "",
             f"Everything done with Claude on this PC, mirrored into the vault. Last sync {now}.",
             "Generated notes; re-run the sync rather than editing them. See [[How this folder is kept in sync]].", "",
             "## Projects", ""]
    for p in sorted(projects):
        n = sum(1 for s in sessions if s["project"] == p)
        lines.append(f"- [[{safe_name(p)}]] — {n} session{'s' if n != 1 else ''}")
    lines += ["", "## Recent sessions", "", "| When | Session | Project | Kind |", "|---|---|---|---|"]
    for s in recent:
        lines.append(f"| {s['end'] or s['date']} | [[{s['note']}]] | [[{safe_name(s['project'])}]] | {s['kind']} |")
    lines += ["", f"All {len(cc)} Claude Code sessions and {len(cw)} Cowork sessions are listed by date in [[Timeline]].", ""]
    lines += ["## Claude chat (claude.ai)", ""]
    if chat_index.exists():
        lines.append(f"Imported conversations: [[Claude Chat]].")
    else:
        lines.append("Not imported yet. Web and mobile chats are not stored on this PC. Request the export in claude.ai under Settings → Privacy → Export data, then run the importer on the emailed zip (see [[How this folder is kept in sync]]).")
    lines += ["", "## Claims", "", "Research conclusions with their supersession chains (the `claims` skill)."]
    if claims:
        for p, note in claims:
            lines.append(f"- [[{note}|{p}]]")
    else:
        lines.append("No claim store yet. One appears at `docs/claims.jsonl` in a repo the first time a conclusion is recorded.")
    lines += ["", "## Memory", "", "What Claude carries between sessions, per project.", ""]
    for p, files in sorted(memory.items()):
        idx = [f for f in files if Path(f).name == "MEMORY.md"]
        n = len([f for f in files if Path(f).name != "MEMORY.md"])
        if not idx:
            lines.append(f"- [[{safe_name(p)}]] — {n} memor{'ies' if n != 1 else 'y'}")
            continue
        for i in idx:
            label = p if len(idx) == 1 else f"{p} / {Path(i).parent.name}"
            lines.append(f"- [[{CC_DIR}/Memory/{i[:-3].replace(os.sep, '/')}|{label}]] — index")
        lines[-1] += f" ({n} memor{'ies' if n != 1 else 'y'} in total)" if len(idx) > 1 else f" ({n} memor{'ies' if n != 1 else 'y'})"
    lines += ["", "## Skills and instructions", "", f"- [[{CC_DIR}/Global instructions (CLAUDE.md)|Global instructions (CLAUDE.md)]]"]
    for sk in skills:
        lines.append(f"- [[{CC_DIR}/Skills/{sk}|{sk}]]")
    if agents:
        lines += ["", "## Agents", "", "Subagent definitions Claude can delegate to."]
        for a in agents:
            lines.append(f"- [[{CC_DIR}/Agents/{a}|{a}]]")
    if docs:
        lines += ["", "## Reference", ""]
        for note, title in docs:
            lines.append(f"- [[{ROOT}/Reference/{note}|{title}]]")
    write_if_changed(vault / ROOT / "Claude.md", "\n".join(lines) + "\n")


def write_timeline(vault: Path, sessions: list[dict]) -> None:
    ss = sorted(sessions, key=lambda s: (s["date"], s["start"]), reverse=True)
    lines = ["---", "title: Timeline", "type: timeline", f"last_synced: {yaml_str(fmt_dt(dt.datetime.now().astimezone()))}",
             "tags: [claude, timeline]", "---", "# Timeline", "", "Every session, newest first. Dates are local time; a session's date is when it was created.", ""]
    month = None
    for s in ss:
        m = s["date"][:7]
        if m != month:
            month = m
            lines += ["", f"## {m}", "", "| Date | Session | Project | Kind | Prompts |", "|---|---|---|---|---:|"]
        lines.append(f"| {s['date']} | [[{s['note']}]] | [[{safe_name(s['project'])}]] | {s['kind']} | {s['prompts']} |")
    write_if_changed(vault / ROOT / "Timeline.md", "\n".join(lines) + "\n")


def write_howto(vault: Path) -> None:
    script = Path(__file__).resolve()
    importer = script.parent / "import_claude_chat_export.py"
    text = f"""---
title: How this folder is kept in sync
type: reference
tags: [claude, reference]
---
# How this folder is kept in sync

Decided 2026-10-10. The `Claude/` folder is generated by a script; nothing in it is hand-written except this note's source.

## What is mirrored

- **Claude Code sessions** from the transcript files under the Claude home folder. One note per transcript with the prompts, Claude's replies and a collapsed list of tool calls. Tool output, thinking and sub-agent traffic are left out because they are bulk, not record. Each note links to the transcript on disk and opens the session in the app.
- **Cowork sessions** (desktop chat with agent mode) from the app's local-agent-mode folder, same format.
- **Memory** files, copied per project with their wikilinks intact. The originals are the source of truth.
- **Skills** and the global `CLAUDE.md`, copied.
- **Project notes** that gather sessions, memory, files Claude edited, and links to the repo's own docs. Repo files are linked, never copied, so there is one version of each decision log.
- **Claude chat** (claude.ai web and mobile). Those conversations are not on this PC. Request the export in claude.ai under Settings → Privacy → Export data; a zip arrives by email. Then run the importer on it (below). Re-running on a newer export updates the notes in place.

## Re-running

The sync is a personal skill. In any Claude Code session type `/obsidian-sync`, or run from a terminal:

```
python "{script}"
```

Add `--force` to rebuild every note (needed after the script's note format changes). Unchanged transcripts are skipped by comparing size and modification time, recorded in `Claude/.sync-state.json`.

To import a claude.ai export:

```
python "{importer}" "C:\\path\\to\\data-export.zip"
```

## Conventions

- Note name: `YYYY-MM-DD Title (first 8 characters of the session id)`. The date is the session's creation date in local time.
- Project name: the folder name of the working directory. Sessions without a folder are grouped under *Scratch workspaces*; desktop chats under *Cowork*.
- A resumed or forked session produces a second transcript that repeats the earlier history; both are kept and cross-linked rather than merged, so nothing is dropped.
- Cost figures are the app's own running totals and are shown as usage, not as audited numbers.
"""
    write_if_changed(vault / ROOT / "How this folder is kept in sync.md", text)


# ----------------------------------------------------------------------------- main
def main() -> None:
    vault = find_vault()
    if not vault.exists():
        sys.exit(f"Vault folder does not exist: {vault}")
    state_path = vault / ROOT / ".sync-state.json"
    state = {}
    if state_path.exists() and not ARGS.force:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    if state.get("version") != SYNC_VERSION:
        state = {"version": SYNC_VERSION, "sessions": {}}
    cache: dict[str, dict] = state.setdefault("sessions", {})

    app = load_app_sessions()
    sources: list[tuple[Path, str, dict | None]] = []
    for f in glob.glob(str(CLAUDE_HOME / "projects" / "*" / "*.jsonl")):
        p = Path(f)
        sources.append((p, "claude-code", app.get(p.stem)))
    for rec, p in load_cowork_sessions():
        sources.append((p, "cowork", rec))

    sessions: list[dict] = []
    parsed: dict[str, Session] = {}
    changed = 0
    for path, kind, rec in sources:
        st = path.stat()
        key = str(path)
        sig = {"mtime": st.st_mtime, "size": st.st_size, "title": (rec or {}).get("title"), "archived": (rec or {}).get("isArchived")}
        old = cache.get(key)
        note_dir = vault / (CC_DIR if kind == "claude-code" else COWORK_DIR) / "Sessions"
        if old and old.get("sig") == sig and (note_dir / (old["summary"]["note"] + ".md")).exists():
            sessions.append(old["summary"])
            continue
        s = Session(path, kind, rec)
        s.parse()
        parsed[key] = s
        cache[key] = {"sig": sig, "summary": s.summary()}
        sessions.append(cache[key]["summary"])
        changed += 1

    # lineage: sessions sharing the first user uuid
    by_root: dict[str, list[str]] = defaultdict(list)
    for s in sessions:
        if s["root_uuid"]:
            by_root[s["root_uuid"]].append(s["note"])

    # render changed sessions; also drop stale notes whose name changed (title edits)
    for key, s in parsed.items():
        sibs = [n for n in by_root.get(s.root_uuid, []) if n != s.note_name]
        folder = vault / (CC_DIR if s.kind == "claude-code" else COWORK_DIR) / "Sessions"
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob(f"* ({s.id8}).md"):
            if old.stem != s.note_name:
                old.unlink()
        write_if_changed(folder / f"{s.note_name}.md", s.render(sibs))
        log(f"  session  {s.note_name}")

    memory = copy_memory(vault)
    skills = copy_skills(vault)
    agents = copy_agents(vault)
    docs = copy_docs(vault)
    claims = export_claims(vault, {s["cwd"] for s in sessions})
    projects = write_project_notes(vault, sessions, memory, claims)
    write_timeline(vault, sessions)
    write_howto(vault)
    write_hub(vault, sessions, projects, memory, skills, agents, docs, claims)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
    log(f"Synced {len(sessions)} sessions ({changed} re-rendered), {sum(len(v) for v in memory.values())} memory files, {len(skills)} skills into {vault / ROOT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", help="vault folder (default: the open vault in obsidian.json)")
    ap.add_argument("--force", action="store_true", help="re-render every session")
    ap.add_argument("--quiet", action="store_true")
    ARGS = ap.parse_args()
    main()
