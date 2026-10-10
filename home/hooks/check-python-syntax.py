#!/usr/bin/env python
"""PostToolUse hook for Edit, Write, MultiEdit and NotebookEdit.

After a Python file is written, parse it. A syntax error or a leftover merge-conflict marker
is reported back to Claude (exit 2) so the broken file is fixed before anything runs it.
Heredoc patches have mangled files here before; this catches them at once. Reads the hook
JSON on stdin; never modifies anything.
"""
import ast
import json
import re
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    inp = data.get("tool_input") or {}
    path = inp.get("file_path") or inp.get("notebook_path") or ""
    if not path:
        return 0
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0
    problems = []
    if re.search(r"^(<<<<<<< |=======$|>>>>>>> )", text, re.M):
        problems.append("merge-conflict markers are still in the file")
    if path.lower().endswith(".py"):
        try:
            ast.parse(text, filename=path)
        except SyntaxError as e:
            problems.append(f"syntax error at line {e.lineno}: {e.msg}")
    if not problems:
        return 0
    sys.stderr.write(f"check-python-syntax hook: {path}: " + "; ".join(problems) + ". Fix the file before running anything that imports it.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
