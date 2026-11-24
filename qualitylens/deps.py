"""Static dependency analysis: which functions and tests can be affected by a change."""
from __future__ import annotations

import ast
from pathlib import Path

import networkx as nx

from .codemap import module_name


def python_files(root: str | Path) -> list[str]:
    root = Path(root)
    skip = {".git", ".venv", "venv", "__pycache__", "build", "dist", ".tox"}
    return sorted(str(p.relative_to(root)) for p in root.rglob("*.py")
                  if not any(part in skip for part in p.relative_to(root).parts))


def is_test_file(rel_path: str) -> bool:
    p = Path(rel_path)
    return p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts or p.name == "conftest.py"


def _import_aliases(tree: ast.Module, current_module: str) -> dict[str, str]:
    """Map local names to the qualified target they refer to (module or module:function)."""
    alias: dict[str, str] = {}
    pkg = current_module.rsplit(".", 1)[0] if "." in current_module else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                alias[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = current_module.split(".")
                base = ".".join(parts[:len(parts) - node.level] + ([base] if base else []))
            for a in node.names:
                alias[a.asname or a.name] = f"{base}:{a.name}"
                alias.setdefault(f"__module__{a.asname or a.name}", f"{base}.{a.name}")
    _ = pkg
    return alias


def build_graph(root: str | Path) -> nx.DiGraph:
    """Nodes are 'module:function'; edge caller -> callee. Test functions are tagged test=True."""
    g = nx.DiGraph()
    root = Path(root)
    defs: dict[str, set[str]] = {}
    trees = {}
    for rel in python_files(root):
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        mod = module_name(rel)
        trees[rel] = (mod, tree)
        defs[mod] = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        defs[mod].add(f"{n.name}.{m.name}")

    for rel, (mod, tree) in trees.items():
        alias = _import_aliases(tree, mod)
        test = is_test_file(rel)

        def resolve(call: ast.Call) -> str | None:
            f = call.func
            if isinstance(f, ast.Name):
                if f.id in defs.get(mod, set()):
                    return f"{mod}:{f.id}"
                target = alias.get(f.id)
                if target and ":" in target:
                    tmod, tname = target.split(":", 1)
                    if tname in defs.get(tmod, set()):
                        return target
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                target = alias.get(f.value.id)
                if target:
                    tmod = target.replace(":", ".") if ":" in target else target
                    if f.attr in defs.get(tmod, set()):
                        return f"{tmod}:{f.attr}"
            return None

        def walk_fn(fn: ast.AST, qual: str):
            node_id = f"{mod}:{qual}"
            g.add_node(node_id, test=test and qual.split(".")[-1].startswith("test"), path=rel)
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call):
                    callee = resolve(sub)
                    if callee and callee != node_id:
                        g.add_edge(node_id, callee)

        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk_fn(n, n.name)
            elif isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        walk_fn(m, f"{n.name}.{m.name}")
    return g


def impact(g: nx.DiGraph, changed: list[str]) -> dict:
    """Callers (transitively) of the changed functions, split into code and tests."""
    callers: set[str] = set()
    for c in changed:
        if c in g:
            callers |= nx.ancestors(g, c)
    tests = sorted(n for n in callers if g.nodes[n].get("test"))
    code = sorted(n for n in callers if not g.nodes[n].get("test"))
    direct = {c: sorted(p for p in g.predecessors(c) if not g.nodes[p].get("test")) for c in changed if c in g}
    return {"callers": code, "tests": tests, "direct_callers": direct}
