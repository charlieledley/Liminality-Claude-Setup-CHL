"""Keep the live Claude Code setup (~/.claude) and this repo's home/ folder in step.

Usage (from the repo folder, any shell):

    python tools/sync_setup.py            # show what differs, change nothing
    python tools/sync_setup.py to-repo    # copy ~/.claude  ->  home/   (after editing a skill in place)
    python tools/sync_setup.py to-home    # copy home/      ->  ~/.claude (on a new machine, or after git pull)

Only the files Claude Code reads are synced: CLAUDE.md, settings.json, skills/, hooks/.
Caches (__pycache__, *.pyc) are skipped. `to-repo` mirrors exactly, so a skill deleted
from ~/.claude is deleted from home/ too (git keeps the history). `to-home` only adds
and overwrites; it never deletes anything in ~/.claude.
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent / "home"
HOME = Path.home() / ".claude"
ITEMS = ["CLAUDE.md", "settings.json", "skills", "hooks"]
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def files_under(root: Path) -> dict[str, Path]:
    """Relative path -> absolute path for every synced file below root."""
    out: dict[str, Path] = {}
    for item in ITEMS:
        p = root / item
        if p.is_file():
            out[item] = p
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and not (SKIP_DIRS & set(f.parts)) and f.suffix not in SKIP_SUFFIXES:
                    out[f.relative_to(root).as_posix()] = f
    return out


def plan(src: Path, dst: Path):
    s, d = files_under(src), files_under(dst)
    added = sorted(k for k in s if k not in d)
    removed = sorted(k for k in d if k not in s)
    changed = sorted(k for k in s if k in d and not filecmp.cmp(s[k], d[k], shallow=False))
    return s, added, removed, changed


def show(label_src: str, label_dst: str, added, removed, changed) -> bool:
    if not (added or removed or changed):
        print(f"{label_src} and {label_dst} are identical.")
        return False
    for k in added:
        print(f"  only in {label_src}: {k}")
    for k in removed:
        print(f"  only in {label_dst}: {k}")
    for k in changed:
        print(f"  differs:          {k}")
    return True


def copy(src_files: dict[str, Path], dst_root: Path, keys) -> None:
    for k in keys:
        target = dst_root / k
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_files[k], target)
        print(f"  copied  {k}")


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "diff"
    if mode == "diff":
        _, added, removed, changed = plan(HOME, REPO)
        show("~/.claude", "home/", added, removed, changed)
        return 0
    if mode == "to-repo":
        s, added, removed, changed = plan(HOME, REPO)
        if not show("~/.claude", "home/", added, removed, changed):
            return 0
        copy(s, REPO, added + changed)
        for k in removed:
            (REPO / k).unlink()
            print(f"  removed {k}")
        return 0
    if mode == "to-home":
        s, added, removed, changed = plan(REPO, HOME)
        if not show("home/", "~/.claude", added, removed, changed):
            return 0
        copy(s, HOME, added + changed)
        for k in removed:
            print(f"  left in place (not deleted): ~/.claude/{k}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
