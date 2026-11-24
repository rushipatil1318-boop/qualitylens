"""Differential behaviour check: run the base and head versions of a changed function on the same inputs."""
from __future__ import annotations

import copy

from .codemap import FunctionInfo
from .harness import same_outcome
from .inputs import generate_cases
from .runner import call_harness

IGNORE = {"TypeError", "AttributeError"}


def _describe(res: dict) -> str:
    if res.get("status") == "return":
        return res.get("repr", "?")
    if res.get("status") == "raise":
        return f"raises {res.get('exc')}"
    return res.get("status", "?")


def behaviour_diff(base_root, head_root, base_fn: FunctionInfo, head_fn: FunctionInfo, max_examples: int = 3) -> dict:
    if [p.name for p in base_fn.params] != [p.name for p in head_fn.params] or head_fn.is_method \
            or "<locals>" in head_fn.name:
        return {"comparable": False, "cases": 0, "changed": 0, "examples": []}
    merged = copy.copy(head_fn)
    merged.literals = {k: list(dict.fromkeys(base_fn.literals.get(k, []) + head_fn.literals.get(k, [])))
                       for k in ("num", "str")}
    cases = generate_cases(merged)
    rb = call_harness(base_root, base_fn.module, base_fn.name, cases)
    rh = call_harness(head_root, head_fn.module, head_fn.name, cases)
    changed = []
    for args, a, b in zip(cases, rb, rh):
        if a.get("exc") in IGNORE and b.get("exc") in IGNORE:
            continue
        if not same_outcome(a, b):
            changed.append((args, a, b))
    examples = [f"{head_fn.name}{tuple(args)!r}: {_describe(a)} -> {_describe(b)}" for args, a, b in changed]
    return {"comparable": True, "cases": len(cases), "changed": len(changed), "examples": examples[:max_examples]}
