"""Git helpers: export trees and parse unified diffs into changed line numbers."""
from __future__ import annotations

import io
import re
import subprocess
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def git(repo: str | Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def export_tree(repo: str | Path, ref: str, dest: str | Path) -> Path:
    """Write the files of `ref` into `dest` without touching the working copy."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", ref],
                          capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")
    return dest


@dataclass
class FileDiff:
    path: str                      # path at head (or base path if deleted)
    status: str                    # A, M, D, R
    added: set[int] = field(default_factory=set)    # head line numbers added/modified
    removed: set[int] = field(default_factory=set)  # base line numbers removed/modified
    old_path: str | None = None

    @property
    def churn(self) -> int:
        return len(self.added) + len(self.removed)


def parse_unified_diff(text: str) -> dict[str, FileDiff]:
    files: dict[str, FileDiff] = {}
    current: FileDiff | None = None
    old_line = new_line = 0
    old_path = None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            current = None
            old_path = None
            continue
        if line.startswith("--- "):
            p = line[4:].strip()
            old_path = None if p == "/dev/null" else p[2:] if p.startswith("a/") else p
            continue
        if line.startswith("+++ "):
            p = line[4:].strip()
            new_path = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
            if new_path is None:
                current = FileDiff(path=old_path or "", status="D")
            else:
                status = "A" if old_path is None else ("R" if old_path != new_path else "M")
                current = FileDiff(path=new_path, status=status, old_path=old_path)
            files[current.path] = current
            continue
        m = HUNK_RE.match(line)
        if m and current is not None:
            old_line = int(m.group(1))
            new_line = int(m.group(3))
            continue
        if current is None or not line:
            continue
        if line.startswith("+"):
            current.added.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            current.removed.add(old_line)
            old_line += 1
        elif line.startswith(" "):
            old_line += 1
            new_line += 1
    return files


def diff_files(repo: str | Path, base: str, head: str) -> dict[str, FileDiff]:
    text = git(repo, "diff", "--no-color", "-U0", "--no-renames", base, head)
    return parse_unified_diff(text)
