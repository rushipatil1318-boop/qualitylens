"""Run QualityLens on every labelled benchmark change and measure how well the score separates bugs.

Usage:
  python benchmark/run_benchmark.py                 # all projects -> results/results.json, results.md, scores.png
  python benchmark/run_benchmark.py --holdout       # fresh generated bugs not seen before -> results/holdout.json

Each project in benchmark/projects/<name>/ has: project/ (code + partial tests), oracle_test.py (hidden spec)
and cases.py (labelled changes). Generated bugs are single-line operator/constant edits kept only when the
hidden oracle fails.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from qualitylens.codemap import analyse_module  # noqa: E402
from qualitylens.deps import is_test_file, python_files  # noqa: E402
from qualitylens.pipeline import Options, analyze  # noqa: E402

PROJECTS = ["shopcalc", "gradekit"]
GIT = ["git", "-c", "user.email=bench@qualitylens", "-c", "user.name=bench"]
TEXT_MUTATIONS = [(" >= ", " > "), (" <= ", " < "), (" > ", " >= "), (" < ", " <= "), (" + ", " - "),
                  (" - ", " + "), (" * ", " / "), (" == ", " != "), ("// 2", "// 4")]
DEV_SEED, EARLIER_HOLDOUT_SEED, HOLDOUT_SEED = 11, 23, 37


def project(name: str) -> dict:
    base = HERE / "projects" / name
    spec = importlib.util.spec_from_file_location(f"cases_{name}", base / "cases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"name": name, "root": base / "project", "oracle": base / "oracle_test.py", "cases": mod.CASES,
            "append": mod.APPEND}


def apply_edits(root: Path, edits) -> None:
    for rel, old, new in edits:
        path = root / rel
        if old is None:
            path.write_text((path.read_text() if path.exists() else "") + new)
            continue
        text = path.read_text()
        if old not in text:
            raise ValueError(f"edit target not found in {rel}: {old[:60]!r}")
        path.write_text(text.replace(old, new, 1))


def oracle_passes(root: Path, oracle: Path) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(root, work, ignore=shutil.ignore_patterns(".git"))
        (work / "oracle_test.py").write_text(oracle.read_text())
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "oracle_test.py"],
                           cwd=work, capture_output=True, text=True,
                           env={"PYTHONPATH": str(work), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
        return r.returncode == 0


def generated_bugs(name: str, n: int, seed: int) -> list:
    """Single-line operator/constant bugs on random function lines; kept only if the hidden oracle fails."""
    p = project(name)
    rng = random.Random(seed)
    candidates = []
    for rel in python_files(p["root"]):
        if is_test_file(rel) or rel.endswith("__init__.py"):
            continue
        lines = (p["root"] / rel).read_text().splitlines()
        for fn in analyse_module(p["root"], rel):
            for ln in sorted(fn.exec_lines):
                text = lines[ln - 1]
                for old, new in TEXT_MUTATIONS:
                    if old in text:
                        candidates.append((rel, text, text.replace(old, new, 1), fn.name))
                for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", text):
                    num = m.group(1)
                    bumped = str(int(num) + 1) if "." not in num else f"{float(num) + 0.05:.2f}"
                    candidates.append((rel, text, text[:m.start()] + bumped + text[m.end():], fn.name))
    rng.shuffle(candidates)
    chosen, used = [], {}
    prefix = name[0].upper()
    for rel, old, new, fn in candidates:
        if used.get(fn, 0) >= 2 or len(chosen) >= n:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "p"
            shutil.copytree(p["root"], work)
            apply_edits(work, [(rel, old, new)])
            if oracle_passes(work, p["oracle"]):
                continue  # equivalent or outside the spec: not a real bug
        used[fn] = used.get(fn, 0) + 1
        chosen.append((f"{prefix}G{len(chosen) + 1:02d}", "bug", f"generated: {old.strip()} -> {new.strip()}",
                       [(rel, old, new)]))
    return chosen


def run_case(job) -> dict:
    name, (cid, kind, title, edits) = job
    p = project(name)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(p["root"], repo)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True)
        subprocess.run(GIT + ["commit", "-qm", "base"], cwd=repo, check=True)
        apply_edits(repo, edits)
        subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True)
        subprocess.run(GIT + ["commit", "-qm", title], cwd=repo, check=True)
        oracle_ok = oracle_passes(repo, p["oracle"])
        report = analyze(repo, "HEAD~1", "HEAD", Options())
    s = report["score"]
    return {"project": name, "id": cid, "kind": kind, "title": title, "label": int(kind == "bug"),
            "oracle_passes": oracle_ok, "quality_score": s["quality_score"], "grade": s["grade"],
            "components": s["components"], "signals": report["signals"],
            "coverage_before": report["coverage"]["before"], "coverage_after": report["coverage"]["after"],
            "mutation_before": report["mutation"]["before"], "mutation_after": report["mutation"]["after"],
            "mutants": report["mutation"]["total"],
            "generated_tests": sum(g["tests"] for g in report["tests"]["generated"]),
            "generated_pass_rate": report["tests"]["generated_pass_rate"],
            "behaviour_examples": [e for f in report["functions"] for e in f["behaviour"].get("examples", [])][:2],
            "seconds": report["seconds"]}


def auc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def average_precision(scores, labels) -> float:
    hits, ap = 0, 0.0
    for i, (_, y) in enumerate(sorted(zip(scores, labels), key=lambda x: -x[0]), 1):
        if y:
            hits += 1
            ap += hits / i
    return ap / max(1, sum(labels))


def summarise(rows: list[dict], threshold: float = 70) -> dict:
    labels = [r["label"] for r in rows]
    risk = [100 - r["quality_score"] for r in rows]
    comp = lambda key: [r["components"][key] for r in rows]  # noqa: E731
    bugs = [r for r in rows if r["label"]]
    safe = [r for r in rows if not r["label"]]
    silent = [r for r in bugs if r["signals"]["new_failures"] == 0]
    mean = lambda xs: round(statistics.mean(xs), 3) if xs else None  # noqa: E731
    with_mut = [r for r in rows if r["mutants"]]
    with_cov = [r for r in rows if r["coverage_before"] is not None]
    return {
        "cases": len(rows), "bugs": len(bugs), "safe": len(safe),
        "roc_auc": round(auc(risk, labels), 3), "average_precision": round(average_precision(risk, labels), 3),
        "baselines_auc": {k: round(auc(comp(c), labels), 3) for k, c in [
            ("churn_only", "churn"), ("uncovered_lines_only", "uncovered_changed_lines"),
            ("mutation_only", "weak_tests"), ("failing_tests_only", "failing_tests"),
            ("behaviour_change_only", "untested_behaviour_change")]},
        "threshold": threshold,
        "bugs_flagged": sum(r["quality_score"] < threshold for r in bugs),
        "safe_flagged": sum(r["quality_score"] < threshold for r in safe),
        "silent_bugs": len(silent), "silent_bugs_flagged": sum(r["quality_score"] < threshold for r in silent),
        "silent_bugs_full_coverage": sum(r["coverage_before"] == 1.0 for r in silent),
        "mean_score_bugs": mean([r["quality_score"] for r in bugs]),
        "mean_score_safe": mean([r["quality_score"] for r in safe]),
        "coverage_before": mean([r["coverage_before"] for r in with_cov]),
        "coverage_after": mean([r["coverage_after"] for r in with_cov]),
        "mutation_before": mean([r["mutation_before"] for r in with_mut]),
        "mutation_after": mean([r["mutation_after"] for r in with_mut]),
        "generated_tests": sum(r["generated_tests"] for r in rows),
        "generated_pass_rate": mean([r["generated_pass_rate"] for r in rows if r["generated_pass_rate"] is not None]),
        "median_seconds": statistics.median(r["seconds"] for r in rows),
        "oracle_consistency": all(r["oracle_passes"] != bool(r["label"]) for r in rows if r["kind"] != "feature"),
    }


def plot(rows: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    kinds = [("refactor", "refactor"), ("test", "test only"), ("feature", "feature + test"), ("bug", "bug")]
    colors = {"shopcalc": "#0e7c86", "gradekit": "#c2410c"}
    fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=150)
    for pi, proj in enumerate(PROJECTS):
        for i, (k, _) in enumerate(kinds):
            ys = [r["quality_score"] for r in rows if r["kind"] == k and r["project"] == proj]
            off = -0.17 if pi == 0 else 0.17
            xs = [i + off + random.Random(j * 7 + pi).uniform(-0.1, 0.1) for j in range(len(ys))]
            ax.scatter(xs, ys, s=18, color=colors[proj], alpha=0.85, edgecolors="none",
                       label=proj if i == 0 else None)
    ax.axhline(70, color="#14284b", lw=0.8, ls="--")
    ax.text(3.45, 71.5, "flag below 70", fontsize=7, color="#14284b", ha="right")
    ax.set_xticks(range(4), [k[1] for k in kinds], fontsize=8)
    ax.set_ylabel("Quality score", fontsize=8)
    ax.set_ylim(0, 105)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("QualityLens score per change, two benchmark projects", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--generated", type=int, default=12, help="generated bugs per project")
    ap.add_argument("--holdout", action="store_true")
    args = ap.parse_args()
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    jobs = []
    if args.holdout:
        for name in PROJECTS:
            seen = {c[3][0][2] for s in (DEV_SEED, EARLIER_HOLDOUT_SEED) for c in generated_bugs(name, 20, s)}
            fresh = [c for c in generated_bugs(name, 25, HOLDOUT_SEED) if c[3][0][2] not in seen]
            jobs += [(name, c) for c in fresh]
    else:
        for name in PROJECTS:
            p = project(name)
            jobs += [(name, c) for c in p["cases"]] + [(name, c) for c in generated_bugs(name, args.generated, DEV_SEED)]
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_case, jobs))
    if args.holdout:
        res = {"bugs": len(rows), "flagged": sum(r["quality_score"] < 70 for r in rows),
               "by_project": {n: {"bugs": sum(r["project"] == n for r in rows),
                                  "flagged": sum(r["project"] == n and r["quality_score"] < 70 for r in rows)}
                              for n in PROJECTS}, "cases": rows}
        (out / "holdout.json").write_text(json.dumps(res, indent=2))
        print(json.dumps({k: v for k, v in res.items() if k != "cases"}, indent=2))
        return
    summary = {"all": summarise(rows), **{n: summarise([r for r in rows if r["project"] == n]) for n in PROJECTS}}
    (out / "results.json").write_text(json.dumps({"summary": summary, "cases": rows}, indent=2))
    pct = lambda v: "-" if v is None else f"{100 * v:.0f}%"  # noqa: E731
    lines = ["| Project | Case | Kind | Change | Score | Coverage before -> after | Mutation before -> after |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['project']} | {r['id']} | {r['kind']} | {r['title']} | {r['quality_score']} | "
                     f"{pct(r['coverage_before'])} -> {pct(r['coverage_after'])} | "
                     f"{pct(r['mutation_before'])} -> {pct(r['mutation_after'])} |")
    (out / "results.md").write_text("\n".join(lines) + "\n")
    plot(rows, out / "scores.png")
    print(json.dumps(summary["all"], indent=2))
    for n in PROJECTS:
        s = summary[n]
        print(n, "AUC", s["roc_auc"], "bugs flagged", s["bugs_flagged"], "/", s["bugs"], "safe flagged",
              s["safe_flagged"], "/", s["safe"])


if __name__ == "__main__":
    main()
