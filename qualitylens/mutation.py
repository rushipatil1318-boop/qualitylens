"""Mutation testing restricted to the changed lines: do the tests notice when those lines are wrong?"""
from __future__ import annotations

import ast
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .runner import tests_pass

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Div,
            ast.Mod: ast.FloorDiv}
SYMBOL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=", ast.In: "in",
          ast.NotIn: "not in", ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
          ast.Mod: "%", ast.And: "and", ast.Or: "or"}


@dataclass
class Mutant:
    line: int
    description: str
    source: str


def _candidates(tree: ast.AST, lines: set[int]) -> list[tuple[int, str]]:
    out = []
    for idx, node in enumerate(ast.walk(tree)):
        line = getattr(node, "lineno", None)
        if line not in lines:
            continue
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMP_SWAP:
            out.append((idx, "cmp"))
        elif isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
            out.append((idx, "bin"))
        elif isinstance(node, ast.BoolOp):
            out.append((idx, "bool"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            out.append((idx, "const"))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            out.append((idx, "not"))
    return out


def _apply(source: str, idx: int, kind: str) -> tuple[str, int, str]:
    tree = ast.parse(source)
    parent_of = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node
    node = list(ast.walk(tree))[idx]
    line = node.lineno
    if kind == "cmp":
        old = type(node.ops[0])
        node.ops[0] = CMP_SWAP[old]()
        desc = f"`{SYMBOL[old]}` -> `{SYMBOL[CMP_SWAP[old]]}`"
    elif kind == "bin":
        old = type(node.op)
        node.op = BIN_SWAP[old]()
        desc = f"`{SYMBOL[old]}` -> `{SYMBOL[BIN_SWAP[old]]}`"
    elif kind == "bool":
        old = type(node.op)
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        desc = f"`{SYMBOL[old]}` -> `{SYMBOL[type(node.op)]}`"
    elif kind == "const":
        old_v = node.value
        node.value = old_v + 1 if isinstance(old_v, int) else round(old_v * 1.1 + 0.01, 4)
        desc = f"`{old_v!r}` -> `{node.value!r}`"
    else:  # not
        parent = parent_of[id(node)]
        for field, value in ast.iter_fields(parent):
            if value is node:
                setattr(parent, field, node.operand)
            elif isinstance(value, list) and node in value:
                value[value.index(node)] = node.operand
        desc = "removed `not`"
    return ast.unparse(tree) + "\n", line, desc


def make_mutants(source: str, lines: set[int], cap: int = 10) -> list[Mutant]:
    cands = _candidates(ast.parse(source), lines)
    # spread the budget over lines: round-robin by line number
    by_line: dict[int, list] = {}
    tree_nodes = list(ast.walk(ast.parse(source)))
    for idx, kind in cands:
        by_line.setdefault(tree_nodes[idx].lineno, []).append((idx, kind))
    order = []
    while any(by_line.values()) and len(order) < cap:
        for ln in sorted(by_line):
            if by_line[ln] and len(order) < cap:
                order.append(by_line[ln].pop(0))
    mutants = []
    for idx, kind in order:
        src, line, desc = _apply(source, idx, kind)
        if src.strip() != ast.unparse(ast.parse(source)).strip():
            mutants.append(Mutant(line, f"line {line}: {desc}", src))
    return mutants


def mutation_score(head_root, rel_path: str, lines: set[int], test_sets: dict[str, list[str]],
                   extra_files: dict[str, str] | None = None, cap: int = 10) -> dict:
    """Score several test selections against the same mutants. test_sets: {label: [pytest targets]}."""
    source = (Path(head_root) / rel_path).read_text(encoding="utf-8")
    mutants = make_mutants(source, lines, cap)
    result = {label: {"total": len(mutants), "killed": 0, "survived": []} for label in test_sets}
    if not mutants:
        return result
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "head"
        shutil.copytree(head_root, work)
        for rel, code in (extra_files or {}).items():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / rel).write_text(code)
        target = work / rel_path
        for m in mutants:
            target.write_text(m.source)
            for label, tests in test_sets.items():
                killed = bool(tests) and not tests_pass(work, tests)
                if killed:
                    result[label]["killed"] += 1
                else:
                    result[label]["survived"].append(m.description)
        target.write_text(source)
    for r in result.values():
        r["score"] = r["killed"] / r["total"] if r["total"] else None
    return result
