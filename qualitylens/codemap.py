"""AST view of a Python module: functions, executable lines, static metrics and mined literals."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Param:
    name: str
    annotation: str | None
    default: object = None
    has_default: bool = False


@dataclass
class FunctionInfo:
    module: str            # dotted module name, e.g. shopcalc.pricing
    path: str              # path relative to project root
    name: str              # qualified name inside the module (Class.method or func)
    start: int
    end: int
    source: str
    params: list[Param]
    exec_lines: set[int]   # statement lines inside the body (docstring excluded)
    is_method: bool = False
    metrics: dict = field(default_factory=dict)
    literals: dict = field(default_factory=dict)  # {"num": [...], "str": [...]}

    @property
    def qualname(self) -> str:
        return f"{self.module}:{self.name}"

    @property
    def is_public(self) -> bool:
        return not self.name.split(".")[-1].startswith("_")


def module_name(rel_path: str) -> str:
    parts = Path(rel_path).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _annotation(node: ast.expr | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def _params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Param]:
    args = fn.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    out = []
    for a, d in zip(positional, defaults):
        p = Param(a.arg, _annotation(a.annotation))
        if d is not None:
            try:
                p.default, p.has_default = ast.literal_eval(d), True
            except ValueError:
                p.has_default = True  # non-literal default: let Python use it
                p.default = ...
        out.append(p)
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        p = Param(a.arg, _annotation(a.annotation))
        if d is not None:
            try:
                p.default, p.has_default = ast.literal_eval(d), True
            except ValueError:
                p.has_default, p.default = True, ...
        out.append(p)
    return out


def _exec_lines(fn: ast.AST) -> set[int]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    lines: set[int] = set()
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                     ast.ClassDef)):
                lines.add(node.lineno)
    return lines


def complexity(fn: ast.AST) -> int:
    """McCabe-style cyclomatic complexity."""
    score = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler,
                             ast.Assert, ast.match_case)):
            score += 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
    return score


def max_nesting(fn: ast.AST) -> int:
    nest_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.Try, ast.match_case)

    def depth(node: ast.AST, d: int) -> int:
        best = d
        for child in ast.iter_child_nodes(node):
            nd = d + 1 if isinstance(child, nest_types) else d
            best = max(best, depth(child, nd))
        return best
    return depth(fn, 0)


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            consts[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            consts[node.target.id] = node.value
    return consts


def _collect_constants(node: ast.AST, nums: list, strs: list, docstring_ids: set[int]) -> None:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.JoinedStr, ast.Raise)):
            for v in ast.walk(sub):
                docstring_ids.add(id(v))
        if isinstance(sub, ast.Constant) and id(sub) not in docstring_ids:
            v = sub.value
            if isinstance(v, bool) or v is None:
                continue
            if isinstance(v, (int, float)):
                nums.append(v)
            elif isinstance(v, str) and len(v) <= 30:
                strs.append(v)


def mine_literals(fn: ast.AST, tree: ast.Module) -> dict:
    """Numbers and strings the function compares against, including module constants it uses."""
    nums: list = []
    strs: list = []
    skip: set[int] = set()
    consts = _module_constants(tree)
    # boundary-value analysis: values the code compares against come first
    for cmp in (n for n in ast.walk(fn) if isinstance(n, ast.Compare)):
        membership = any(isinstance(op, (ast.In, ast.NotIn)) for op in cmp.ops)
        for operand in [cmp.left, *cmp.comparators]:
            target = consts.get(operand.id) if isinstance(operand, ast.Name) else operand
            if target is None:
                continue
            if membership and isinstance(target, ast.Dict):
                target = ast.Tuple(elts=[k for k in target.keys if k is not None], ctx=ast.Load())
            _collect_constants(target, nums, strs, set())
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        skip.add(id(body[0].value))
    for stmt in body:
        _collect_constants(stmt, nums, strs, skip)
    used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    for name in used & consts.keys():
        _collect_constants(consts[name], nums, strs, set())
    def uniq(seq):
        seen, out = set(), []
        for x in seq:
            key = (type(x), x)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out
    return {"num": uniq(nums), "str": uniq(strs)}


def rule_findings(fn: ast.AST) -> list[dict]:
    """Lightweight static checks (line, rule, message)."""
    found = []
    for node in ast.walk(fn):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                found.append({"line": node.lineno, "rule": "bare-except", "message": "Bare `except:` hides errors."})
            elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
                found.append({"line": node.lineno, "rule": "broad-except",
                              "message": f"Catching `{node.type.id}` is too broad."})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"print", "eval", "exec"}:
            found.append({"line": node.lineno, "rule": f"call-{node.func.id}",
                          "message": f"`{node.func.id}()` in library code."})
    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for d in fn.args.defaults + [d for d in fn.args.kw_defaults if d is not None]:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                found.append({"line": d.lineno, "rule": "mutable-default", "message": "Mutable default argument."})
    return found


def analyse_module(root: str | Path, rel_path: str) -> list[FunctionInfo]:
    path = Path(root) / rel_path
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()
    mod = module_name(rel_path)
    out: list[FunctionInfo] = []

    def visit(body, prefix: str, in_class: bool):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{node.name}"
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                src = "\n".join(lines[start - 1:node.end_lineno])
                info = FunctionInfo(module=mod, path=rel_path, name=name, start=start, end=node.end_lineno,
                                    source=src, params=_params(node), exec_lines=_exec_lines(node),
                                    is_method=in_class)
                doc = ast.get_docstring(node)
                info.metrics = {"complexity": complexity(node), "nesting": max_nesting(node),
                                "length": node.end_lineno - node.lineno + 1, "params": len(info.params),
                                "has_docstring": doc is not None}
                info.literals = mine_literals(node, tree)
                info.metrics["findings"] = rule_findings(node)
                out.append(info)
                visit(node.body, f"{name}.<locals>.", False)
            elif isinstance(node, ast.ClassDef):
                visit(node.body, f"{prefix}{node.name}.", True)
    visit(tree.body, "", False)
    return out


def functions_touching(funcs: list[FunctionInfo], changed: set[int]) -> list[FunctionInfo]:
    hit = [f for f in funcs if any(f.start <= ln <= f.end for ln in changed)]
    # keep the innermost function when nested functions are touched
    return [f for f in hit if not any(o is not f and o.start >= f.start and o.end <= f.end
                                      and any(o.start <= ln <= o.end for ln in changed) and
                                      all(o.start <= ln <= o.end for ln in changed if f.start <= ln <= f.end)
                                      for o in hit)]
