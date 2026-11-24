"""End-to-end analysis of one change (base..head)."""
from __future__ import annotations

import ast
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from .codemap import FunctionInfo, analyse_module, functions_touching
from .deps import build_graph, impact, is_test_file, python_files
from .differential import behaviour_diff
from .gitutils import diff_files, export_tree, git
from .learned import load_model, predict
from .mutation import mutation_score
from .review import llm_review, static_review
from .runner import run_tests
from .score import score
from .testgen import DeterministicGenerator

GEN_DIR = "tests/generated_by_qualitylens"


@dataclass
class Options:
    backend: str = "deterministic"   # or "llm"
    mutation: bool = True
    mutation_cap: int = 10
    llm_review: bool = False
    generate: bool = True
    llm_client: object = None
    model_path: str | None = None    # learned model JSON; defaults to the packaged model


@dataclass
class ChangedFunction:
    head: FunctionInfo
    base: FunctionInfo | None
    lines: set[int]                       # target lines: changed executable lines (+ uses of changed constants)
    via: str = "edit"
    tests: list[str] = field(default_factory=list)


def _module_names_at(path: Path, lines: set[int]) -> set[str]:
    if not lines or not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and any(node.lineno <= ln <= node.end_lineno for ln in lines):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def _lines_using(path: Path, fn: FunctionInfo, names: set[str]) -> set[int]:
    if not names:
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.lineno for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in names
            and fn.start <= n.lineno <= fn.end}


def find_changed_functions(base_root: Path, head_root: Path, diffs: dict) -> list[ChangedFunction]:
    out: list[ChangedFunction] = []
    for path, d in diffs.items():
        if not path.endswith(".py") or is_test_file(path) or d.status == "D":
            continue
        head_funcs = analyse_module(head_root, path)
        base_funcs = analyse_module(base_root, path) if (base_root / path).exists() else []
        base_by = {f.name: f for f in base_funcs}
        touched: dict[str, tuple[FunctionInfo, str]] = {f.name: (f, "edit") for f in
                                                        functions_touching(head_funcs, d.added)}
        for bf in functions_touching(base_funcs, d.removed):
            hf = next((f for f in head_funcs if f.name == bf.name), None)
            if hf and hf.name not in touched:
                touched[hf.name] = (hf, "edit")
        outside_head = {ln for ln in d.added if not any(f.start <= ln <= f.end for f in head_funcs)}
        outside_base = {ln for ln in d.removed if not any(f.start <= ln <= f.end for f in base_funcs)}
        names = _module_names_at(head_root / path, outside_head) | _module_names_at(base_root / path, outside_base)
        for f in head_funcs:
            if f.name not in touched and _lines_using(head_root / path, f, names):
                touched[f.name] = (f, "constant " + ", ".join(sorted(names)))
        for name, (hf, via) in touched.items():
            lines = (d.added & hf.exec_lines) | _lines_using(head_root / path, hf, names)
            added_inside = any(hf.start <= ln <= hf.end for ln in d.added)
            if not lines and via == "edit" and not added_inside:  # pure deletion inside the function
                lines = set(hf.exec_lines)
            out.append(ChangedFunction(head=hf, base=base_by.get(name), lines=lines, via=via))
    return out


def _tests_touching(cov: dict, path: str, lines: set[int]) -> list[str]:
    return sorted(t for t, e in cov.items() if set(e.get("lines", {}).get(path, [])) & lines)


def analyze(repo: str | Path, base: str, head: str, options: Options | None = None) -> dict:
    options = options or Options()
    t0 = time.time()
    repo = Path(repo)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base_root = export_tree(repo, base, tmp / "base")
        head_root = export_tree(repo, head, tmp / "head")
        diffs = diff_files(repo, base, head)
        py_diffs = {p: d for p, d in diffs.items() if p.endswith(".py")}
        test_files_changed = sorted(p for p in py_diffs if is_test_file(p))
        churn = sum(d.churn for p, d in py_diffs.items() if not is_test_file(p))
        changed = find_changed_functions(base_root, head_root, py_diffs)

        # existing tests at base and head (outcomes + per-test coverage)
        head_run = run_tests(head_root)
        base_run = run_tests(base_root)
        head_tests = head_run["tests"]
        new_failures = sorted(t for t, e in head_tests.items() if e.get("outcome") != "passed"
                              and base_run["tests"].get(t, {}).get("outcome", "passed") == "passed")

        for cf in changed:
            body = set(range(cf.head.start, cf.head.end + 1))
            cf.tests = _tests_touching(head_tests, cf.head.path, body)

        # coverage of changed lines by existing tests
        target = {(cf.head.path, ln) for cf in changed for ln in cf.lines}
        covered_before = {(p, ln) for e in head_tests.values() for p, lns in e.get("lines", {}).items() for ln in lns}
        cov_before = len(target & covered_before) / len(target) if target else None

        # dependency impact
        graph = build_graph(head_root)
        dep = impact(graph, [cf.head.qualname for cf in changed])

        # behaviour change (base vs head) and static review
        functions = []
        comparable = unacknowledged = 0
        complexity_delta = 0
        llm = options.llm_client
        for cf in changed:
            beh = (behaviour_diff(base_root, head_root, cf.base, cf.head) if cf.base
                   else {"comparable": False, "cases": 0, "changed": 0, "examples": [], "new": True})
            acknowledged = any(t.split("::")[0] in test_files_changed for t in cf.tests)
            if beh["comparable"]:
                comparable += 1
                if beh["changed"] and not acknowledged:
                    unacknowledged += 1
            rev = static_review(cf.head, cf.base, cf.lines)
            if options.llm_review and llm is not None:
                rev["findings"] += llm_review(llm, cf.head, cf.lines)
            complexity_delta += rev["complexity_delta"]
            functions.append({"function": cf.head.qualname, "path": cf.head.path, "via": cf.via,
                              "changed_lines": sorted(cf.lines), "tests": cf.tests,
                              "behaviour": {**beh, "acknowledged_by_test_update": acknowledged},
                              "review": rev})

        # test generation
        generated = []
        gen_files: dict[str, str] = {}
        if options.generate and changed:
            if options.backend == "llm":
                from .testgen_llm import LLMGenerator
                generator = LLMGenerator(llm) if llm is not None else LLMGenerator()
            else:
                generator = DeterministicGenerator()
            example_test = ""
            for p in python_files(head_root):
                if is_test_file(p) and Path(p).name.startswith("test_"):
                    example_test = (head_root / p).read_text(encoding="utf-8")
                    break
            for cf in changed:
                callee_src = []
                if cf.head.qualname in graph:
                    for callee in list(graph.successors(cf.head.qualname))[:3]:
                        mod, name = callee.split(":", 1)
                        rel = mod.replace(".", "/") + ".py"
                        for f in analyse_module(head_root, rel) if (head_root / rel).exists() else []:
                            if f.name == name:
                                callee_src.append(f.source)
                ctx = {"changed_lines": cf.lines, "callee_sources": callee_src, "example_test": example_test}
                g = generator.generate(head_root, cf.head, ctx)
                if g and g.n_tests:
                    rel = f"{GEN_DIR}/{g.filename}"
                    gen_files[rel] = g.code
                    generated.append({"function": g.function, "file": rel, "tests": g.n_tests,
                                      "backend": g.backend, "notes": g.notes, "disagreements": g.disagreements})

        # run generated tests: pass rate and coverage after
        cov_after = cov_before
        gen_pass = None
        if gen_files:
            work = tmp / "head_gen"
            shutil.copytree(head_root, work)
            for rel, code in gen_files.items():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_text(code)
            gen_run = run_tests(work, [GEN_DIR])
            outcomes = [e.get("outcome") for e in gen_run["tests"].values()]
            gen_pass = sum(o == "passed" for o in outcomes) / len(outcomes) if outcomes else None
            covered_gen = {(p, ln) for e in gen_run["tests"].values() for p, lns in e.get("lines", {}).items()
                           for ln in lns}
            cov_after = len(target & (covered_before | covered_gen)) / len(target) if target else None

        # mutation testing on changed lines
        mut = {"before": None, "after": None, "total": 0, "survived_before": [], "survived_after": []}
        if options.mutation and changed:
            tot = kb = ka = 0
            for path, d in py_diffs.items():
                if is_test_file(path) or d.status == "D" or not d.added:
                    continue
                file_funcs = [cf for cf in changed if cf.head.path == path]
                existing = sorted({t for cf in file_funcs for t in cf.tests})
                gens = [g["file"] for g in generated if any(g["function"] == cf.head.qualname for cf in file_funcs)]
                res = mutation_score(head_root, path, set(d.added),
                                     {"before": existing, "after": existing + gens},
                                     extra_files=gen_files, cap=options.mutation_cap)
                tot += res["before"]["total"]
                kb += res["before"]["killed"]
                ka += res["after"]["killed"]
                mut["survived_before"] += [f"{path} {s}" for s in res["before"]["survived"]]
                mut["survived_after"] += [f"{path} {s}" for s in res["after"]["survived"]]
            mut["total"] = tot
            if tot:
                mut["before"], mut["after"] = kb / tot, ka / tot

        signals = {"new_failures": len(new_failures), "comparable_functions": comparable,
                   "unacknowledged_changes": unacknowledged, "changed_line_coverage": cov_before,
                   "mutation_score": mut["before"], "complexity_delta": max(0, complexity_delta),
                   "callers": len(dep["callers"]), "churn": churn}
        result = score(signals) if changed else {**score({}), "quality_score": 100.0, "grade": "A",
                                                 "reasons": []}
        model = load_model(options.model_path)
        if model is not None and changed:
            result["learned"] = predict(model, result["components"])
        try:
            head_sha = git(repo, "rev-parse", "--short", head).strip()
            base_sha = git(repo, "rev-parse", "--short", base).strip()
        except RuntimeError:
            head_sha, base_sha = head, base
        return {
            "base": base_sha, "head": head_sha, "seconds": round(time.time() - t0, 1),
            "files_changed": sorted(py_diffs), "test_files_changed": test_files_changed, "churn": churn,
            "functions": functions, "dependencies": dep,
            "tests": {"existing": len(head_tests), "new_failures": new_failures, "generated": generated,
                      "generated_pass_rate": gen_pass},
            "coverage": {"before": cov_before, "after": cov_after, "target_lines": len(target)},
            "mutation": mut, "signals": signals, "score": result, "generated_files": gen_files,
        }
