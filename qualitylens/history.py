"""Hotspot analysis from Git history: where is the next defect most likely?

Ranks source files by change frequency x complexity (the "hotspot" idea from behavioural code analysis),
and reports for each file how many commits were bug fixes, how many people changed it, and how many of
its functions no test reaches.
"""
from __future__ import annotations

import re
import tempfile
from collections import defaultdict
from pathlib import Path

from .codemap import analyse_module
from .deps import build_graph, is_test_file
from .gitutils import export_tree, git

FIX_RE = re.compile(r"\b(fix(e[sd])?|bug(s|fix)?|defect|hotfix|regression|repair)\b", re.I)
SEP = "\x1f"


def commit_stats(repo: str | Path, since: str | None = None, max_commits: int = 2000) -> dict[str, dict]:
    args = ["log", "--no-merges", f"-n{max_commits}", "--numstat", "--date=short",
            f"--format=@@{SEP}%H{SEP}%an{SEP}%ad{SEP}%s"]
    if since:
        args.append(f"--since={since}")
    out = git(repo, *args)
    stats: dict[str, dict] = defaultdict(lambda: {"commits": 0, "fix_commits": 0, "churn": 0, "authors": set(),
                                                  "last_change": ""})
    is_fix, author, day = False, "", ""
    for line in out.splitlines():
        if line.startswith("@@" + SEP):
            _, _sha, author, day, subject = line.split(SEP, 4)
            is_fix = bool(FIX_RE.search(subject))
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        s = stats[path]
        s["commits"] += 1
        s["fix_commits"] += int(is_fix)
        s["churn"] += (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
        s["authors"].add(author)
        s["last_change"] = max(s["last_change"], day)
    return stats


def hotspots(repo: str | Path, since: str | None = None, top: int = 10) -> dict:
    stats = commit_stats(repo, since)
    with tempfile.TemporaryDirectory() as tmp:
        head = export_tree(repo, "HEAD", Path(tmp) / "head")
        graph = build_graph(head)
        tested = {n for n in graph if not graph.nodes[n].get("test")
                  and any(graph.nodes[a].get("test") for a in graph.predecessors(n))}
        # anything reachable from a test counts as tested
        reach = set()
        for n in graph:
            if graph.nodes[n].get("test"):
                stack = list(graph.successors(n))
                while stack:
                    cur = stack.pop()
                    if cur not in reach:
                        reach.add(cur)
                        stack.extend(graph.successors(cur))
        tested |= reach
        rows = []
        for path, s in stats.items():
            if not path.endswith(".py") or is_test_file(path) or not (head / path).exists():
                continue
            funcs = analyse_module(head, path)
            if not funcs:
                continue
            cx = sum(f.metrics["complexity"] for f in funcs)
            worst = max(funcs, key=lambda f: f.metrics["complexity"])
            untested = [f.name for f in funcs if f.qualname not in tested and f.is_public]
            rows.append({"file": path, "commits": s["commits"], "fix_commits": s["fix_commits"],
                         "fix_ratio": round(s["fix_commits"] / s["commits"], 2), "churn": s["churn"],
                         "authors": len(s["authors"]), "last_change": s["last_change"], "complexity": cx,
                         "most_complex": f"{worst.name} ({worst.metrics['complexity']})",
                         "functions": len(funcs), "untested_functions": untested})
    if rows:
        max_c = max(r["commits"] for r in rows)
        max_x = max(r["complexity"] for r in rows)
        for r in rows:
            r["hotspot"] = round(100 * (r["commits"] / max_c) * (r["complexity"] / max_x), 1)
        rows.sort(key=lambda r: (-r["hotspot"], -r["fix_commits"]))
    return {"since": since, "files_analysed": len(rows), "hotspots": rows[:top]}


def to_markdown(h: dict) -> str:
    out = [f"## QualityLens hotspots{' since ' + h['since'] if h['since'] else ''}", "",
           "Files that change often and are complex are where defects concentrate. Bug-fix commits and untested "
           "functions show where tests would pay off first.", "",
           "| File | Hotspot | Commits | Bug fixes | Complexity | Most complex | Untested functions |",
           "|---|---|---|---|---|---|---|"]
    for r in h["hotspots"]:
        untested = ", ".join(r["untested_functions"][:3]) + ("…" if len(r["untested_functions"]) > 3 else "")
        out.append(f"| `{r['file']}` | {r['hotspot']} | {r['commits']} | {r['fix_commits']} "
                   f"({100 * r['fix_ratio']:.0f}%) | {r['complexity']} | {r['most_complex']} | {untested or '-'} |")
    return "\n".join(out) + "\n"
