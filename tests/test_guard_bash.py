"""Pins the command-guard hook (home/hooks/guard-bash.py): what it blocks and what it lets through.

Run from the repo folder with plain Python (no pytest needed):
    python tests/test_guard_bash.py
or, if pytest is available:
    python -m pytest tests -q

Cases that need a real repo (push-remote resolution) are skipped when that repo is not on
this machine. The hook is a text match, so these cases also document its reach: a forbidden
pattern anywhere in the command text is blocked, even inside a quoted string.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "home" / "hooks" / "guard-bash.py"
PW = r"C:\Liminality-put-writing-strategy"   # remotes: origin (organisation), mine (personal), dashboard-v2 (colleague)
FR = r"C:\Liminality-french-swap-spreads"    # remote: origin (personal)
NOREPO = r"C:\x"


def run(cmd: str, cwd: str = NOREPO, tool: str = "Bash") -> tuple[str, str]:
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd})
    p = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, timeout=30)
    return ("BLOCK" if p.returncode == 2 else "allow"), p.stderr.strip()


class GuardBash(unittest.TestCase):
    def check(self, cmd, want, cwd=NOREPO, tool="Bash", needs_repo=None):
        if needs_repo and not Path(needs_repo).exists():
            self.skipTest(f"{needs_repo} not on this machine")
        got, why = run(cmd, cwd, tool)
        self.assertEqual(got, want, f"{cmd!r} (cwd {cwd}) -> {got}, wanted {want}. {why}")

    # read-only and ordinary commands pass
    def test_plain_commands_allowed(self):
        for cmd in ["git status", "ls -la && git log --oneline -5", "rm -f exports/a.png",
                    "git worktree remove .claude/worktrees/wt", "git checkout -- research/data-validation/a.xlsx",
                    "pip install --target=C:/Temp/pylibs python-pptx", r".venv\Scripts\pip.exe install --target=C:/Temp/pylibs x"]:
            self.check(cmd, "allow")

    # pushes: personal GitHub only
    def test_push_to_personal_remote_allowed(self):
        self.check("git push mine feature/x", "allow", PW, needs_repo=PW)
        self.check("git push -u mine feature/y", "allow", PW, needs_repo=PW)
        self.check("git push origin main", "allow", FR, needs_repo=FR)
        self.check("git push", "allow", FR, needs_repo=FR)

    def test_push_to_other_remotes_blocked(self):
        self.check("git push origin main", "BLOCK", PW, needs_repo=PW)
        self.check("git push dashboard-v2 transfer/x", "BLOCK", PW, needs_repo=PW)
        self.check("git push https://github.com/someone-else/repo.git main", "BLOCK")

    def test_force_push_and_no_verify_blocked(self):
        self.check("git push --force mine main", "BLOCK", PW, needs_repo=PW)
        self.check("git push -f mine main", "BLOCK", PW, needs_repo=PW)
        self.check("git push --force-with-lease mine main", "BLOCK", PW, needs_repo=PW)
        self.check("git commit --no-verify -m x", "BLOCK")
        self.check("git push --no-verify mine main", "BLOCK", PW, needs_repo=PW)

    # whole-tree discards
    def test_destructive_git_blocked(self):
        for cmd in ["git reset --hard HEAD~1", "git checkout -- .", "git checkout .", "git restore .",
                    "git restore --staged .", "git clean -fd", "git stash drop", "git branch -D feature/x"]:
            self.check(cmd, "BLOCK")

    # recursive deletes: scratch folders only
    def test_recursive_delete_in_scratch_allowed(self):
        for cmd in ["rm -rf /c/Users/charlie/AppData/Local/Temp/obsidian-sync-test", 'rm -rf "$T"',
                    r"rm -rf %TEMP%\x", r"rm -rf $TMP/x", "rm -rf /tmp/x", "rm -rf C:/x/scratchpad/y"]:
            self.check(cmd, "allow")
        self.check(r"Remove-Item -Recurse -Force $env:TEMP\x", "allow", tool="PowerShell")

    def test_recursive_delete_outside_scratch_blocked(self):
        self.check("rm -rf C:/Liminality-put-writing-strategy/exports", "BLOCK")
        self.check("rm -r analysis/_cache", "BLOCK")
        self.check(r"Remove-Item -Recurse -Force C:\Liminality-put-writing-strategy\exports", "BLOCK", tool="PowerShell")
        self.check(r"rmdir /s /q C:\Liminality-put-writing-strategy\exports", "BLOCK", tool="PowerShell")

    # project venvs stay untouched
    def test_pip_into_venv_blocked(self):
        self.check(".venv/Scripts/python.exe -m pip install pandas", "BLOCK")
        self.check(r".venv\Scripts\pip.exe install numpy", "BLOCK")

    # other tools are not the hook's business
    def test_other_tools_ignored(self):
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "x.py"}, "cwd": NOREPO})
        p = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    unittest.main(verbosity=2)
