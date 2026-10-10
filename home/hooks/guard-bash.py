#!/usr/bin/env python
"""PreToolUse hook for Bash and PowerShell: blocks commands that the working rules forbid.

Deterministic policy, so the rules hold whatever the prompt says. Exit 2 blocks the call and
feeds the reason back to Claude, which then has to ask Charlie or do it another way. Charlie
can always run the command himself from the Terminal panel.

Blocked:
  - git push with --force / -f / --force-with-lease, and any push that deletes a remote branch
  - git push to a remote that is not in Charlie's personal GitHub account (charlieledley)
  - git commit / push with --no-verify (the pre-commit hook runs the figure pins)
  - whole-tree discards: git reset --hard, git checkout -- . , git restore . , git clean -f,
    git stash drop / clear, git branch -D
  - recursive deletes (rm -r, Remove-Item -Recurse, rmdir /s) outside Temp or scratch folders
  - pip install into a project .venv without --target

Not a security boundary (a determined command can dodge the regexes); it is a seat belt for
the rules that have actually bitten. Reads the hook JSON on stdin.
"""
import json
import os
import re
import subprocess
import sys

PERSONAL_GITHUB = "github.com/charlieledley/"
SCRATCH_MARKERS = ("\\temp\\", "/temp/", "/tmp/", "$env:temp", "$env:tmp", "%temp%", "%tmp%", "scratchpad", "scratch-workspaces", "\\.claude\\worktrees", "/.claude/worktrees")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd.strip():
        return 0
    cwd = data.get("cwd") or os.getcwd()
    reasons = []

    flat = " ".join(cmd.split())
    segments = re.split(r"\s*(?:&&|\|\||;|\|)\s*|\n", cmd)

    for seg in segments:
        s = " ".join(seg.split())
        if not s:
            continue
        low = s.lower()

        m = re.search(r"\bgit\b(?:\s+-C\s+(\S+))?(?:\s+-c\s+\S+)*\s+push\b(.*)$", s)
        if m:
            args = m.group(2)
            if re.search(r"(^|\s)(--force|-f|--force-with-lease)(\s|=|$)", args):
                reasons.append("force push")
            if re.search(r"(^|\s)(--delete|-d)(\s|$)|(^|\s):\S", args):
                reasons.append("push that deletes a remote branch")
            if "--no-verify" in args:
                reasons.append("git push --no-verify")
            tokens = [t for t in args.split() if not t.startswith("-")]
            remote = tokens[0] if tokens else "origin"
            url = remote if ("://" in remote or "@" in remote) else remote_url(m.group(1) or cwd, remote)
            if url and PERSONAL_GITHUB not in url.lower():
                reasons.append(f"push to remote '{remote}' ({url}); pushes go only to Charlie's personal GitHub unless he says otherwise for this push")

        if re.search(r"\bgit\b.*\bcommit\b.*--no-verify", s):
            reasons.append("git commit --no-verify (the pre-commit hook runs the figure pins; a skip proves nothing)")
        if re.search(r"\bgit\b.*\breset\s+(--hard|--merge)\b", s):
            reasons.append("git reset --hard")
        if re.search(r"\bgit\b.*\bcheckout\s+(--\s+)?\.(\s|$)", s) or re.search(r"\bgit\b.*\brestore\s+(--staged\s+|--worktree\s+)*(--\s+)?\.(\s|$)", s):
            reasons.append("whole-tree discard (git checkout/restore .); look at what is there and discard by path")
        if re.search(r"\bgit\b.*\bclean\b.*\s-[a-zA-Z]*f", s):
            reasons.append("git clean -f")
        if re.search(r"\bgit\b.*\bstash\s+(drop|clear)\b", s):
            reasons.append("git stash drop/clear")
        if re.search(r"\bgit\b.*\bbranch\b.*(\s-D\b|--delete\s+--force|-df\b|-fd\b)", s):
            reasons.append("forced branch delete")

        rm = re.search(r"(^|\s)rm\s+((?:-[a-zA-Z]+\s+)+)(.+)$", s)
        if rm and "r" in rm.group(2):
            targets = [t for t in rm.group(3).split() if not t.startswith("-")]
            if not targets or not all(is_scratch(t) for t in targets):
                reasons.append(f"recursive delete outside a scratch folder: {s[:120]}")
        if re.search(r"remove-item\b.*-recurse", low) and not any(is_scratch(t) for t in s.split()):
            reasons.append(f"recursive Remove-Item outside a scratch folder: {s[:120]}")
        if re.search(r"\brmdir\b.*\s/s\b", low) and not any(is_scratch(t) for t in s.split()):
            reasons.append(f"rmdir /s outside a scratch folder: {s[:120]}")

        if re.search(r"\.venv[\\/](scripts|bin)[\\/](python(\.exe)?\s+-m\s+pip|pip\d*(\.exe)?)\s+install\b", low) and "--target" not in low:
            reasons.append("pip install into a project .venv; use pip install --target=<scratch>/pylibs with PYTHONPATH")

    if not reasons:
        return 0
    sys.stderr.write(
        "Blocked by ~/.claude/hooks/guard-bash.py (working rules): "
        + "; ".join(dict.fromkeys(reasons))
        + ". Ask Charlie; he can run it himself from the Terminal panel, or say explicitly that this specific command is wanted, in which case tell him the hook needs disabling for it.\n"
    )
    return 2


def remote_url(repo_dir: str, remote: str) -> str:
    try:
        out = subprocess.run(["git", "-C", repo_dir, "remote", "get-url", remote], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def is_scratch(token: str) -> bool:
    t = token.strip("\"'").replace("\\\\", "\\")
    t = os.path.expanduser(t) if t.startswith("~") else t
    t = os.path.expandvars(t).lower()
    return any(mk in t for mk in SCRATCH_MARKERS) or t.startswith("$t") or t.startswith("$s") or t.startswith("$tmp")


if __name__ == "__main__":
    sys.exit(main())
