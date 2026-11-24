"""Input generation: type-aware value pools plus boundary values mined from the code."""
from __future__ import annotations

import itertools
import random

from .codemap import FunctionInfo, Param

BASE_POOLS = {
    "int": [0, 1, -1, 2, 10, 100],
    "float": [0.0, 1.0, -1.0, 0.5, 9.99, 100.0, 1000.0],
    "str": ["", "x"],
    "bool": [False, True],
    "list": [[], [1], [1, 2, 3]],
    "dict": [{}, {"a": 1}],
    "any": [0, 1, -1, 0.5, "", "x", None],
}
MAX_POOL = 16
MAX_CASES = 240


def _kind(annotation: str | None) -> tuple[str, bool]:
    """Return (kind, optional) from an annotation string."""
    if not annotation:
        return "any", False
    a = annotation.replace(" ", "")
    optional = "None" in a or a.startswith("Optional[")
    for kind in ("bool", "int", "float", "str", "list", "dict"):
        if a == kind or a.startswith(f"{kind}[") or a.startswith(f"Optional[{kind}") or a.startswith(f"{kind}|") \
                or a.endswith(f"|{kind}") or a.lower().startswith(f"{kind}"):
            return kind, optional
    if a.startswith(("List[", "Sequence[", "tuple[", "Tuple[")):
        return "list", optional
    if a.startswith(("Dict[", "Mapping[")):
        return "dict", optional
    return "any", optional


def _boundaries(nums: list, as_float: bool) -> list:
    out = []
    for n in nums:
        if as_float:
            n = float(n)
            out += [round(n - 0.01, 2), n, round(n + 0.01, 2)]
        else:
            if isinstance(n, float) and not n.is_integer():
                continue
            n = int(n)
            out += [n - 1, n, n + 1]
    return out


def pool_for(param: Param, fn: FunctionInfo) -> list:
    kind, optional = _kind(param.annotation)
    mined_nums = [n for n in fn.literals.get("num", []) if abs(n) < 1e6]
    mined_strs = list(fn.literals.get("str", []))
    if kind == "int":
        values = _boundaries(mined_nums, False)[:12] + BASE_POOLS["int"]
    elif kind == "float":
        values = _boundaries(mined_nums, True)[:12] + BASE_POOLS["float"]
    elif kind == "str":
        values = mined_strs + BASE_POOLS["str"] + [s.lower() for s in mined_strs if s.lower() != s][:2]
    elif kind == "any":
        values = mined_strs[:4] + _boundaries(mined_nums, False)[:6] + BASE_POOLS["any"]
    else:
        values = list(BASE_POOLS[kind])
    if param.has_default and param.default is not ...:
        values = [param.default] + values
    if optional:
        values.append(None)
    seen, uniq = set(), []
    for v in values:
        key = (type(v).__name__, repr(v))
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    # keep mined boundary values first; cap pool size
    return uniq[:MAX_POOL]


def _typical(param: Param, pool: list):
    if param.has_default and param.default is not ...:
        return param.default
    kind, _ = _kind(param.annotation)
    for v in pool:
        if kind in ("int", "float") and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return v
        if kind == "str" and isinstance(v, str) and v:
            return v
    return pool[0] if pool else None


def generate_cases(fn: FunctionInfo, seed: int = 7) -> list[list]:
    """Full combinations when small, else one-factor-at-a-time plus seeded random combinations."""
    params = [p for p in fn.params if not (fn.is_method and p.name in ("self", "cls"))]
    if not params:
        return [[]]
    pools = [pool_for(p, fn) for p in params]
    total = 1
    for p in pools:
        total *= max(1, len(p))
    if total <= MAX_CASES:
        return [list(c) for c in itertools.product(*pools)]
    base = [_typical(p, pool) for p, pool in zip(params, pools)]
    cases = [list(base)]
    for i, pool in enumerate(pools):
        for v in pool:
            c = list(base)
            c[i] = v
            cases.append(c)
    # pairwise-ish: vary two parameters at a time for the first two string/enum-like parameters
    rng = random.Random(seed)
    while len(cases) < MAX_CASES:
        cases.append([rng.choice(pool) for pool in pools])
    uniq, seen = [], set()
    for c in cases:
        key = repr(c)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq[:MAX_CASES]
