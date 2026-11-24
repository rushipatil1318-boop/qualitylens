"""Subprocess harness: call one function with many argument tuples and report each outcome.

Input (stdin JSON): {"module", "func", "cases": [[args...]], "trace_file"}.
Output (last stdout line): list of {"status": "return"|"raise"|"timeout", ...}.
"""
from __future__ import annotations

import ast
import importlib
import json
import math
import os
import signal
import sys


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _literal_ok(value) -> bool:
    try:
        back = ast.literal_eval(repr(value))
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False
    return _same(back, value)


def _same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            return (math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
        return False
    if type(a) is not type(b):
        return False
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    return a == b


def _resolve(obj, dotted: str):
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


def main() -> None:
    req = json.loads(sys.stdin.read())
    sys.path.insert(0, os.getcwd())
    mod = importlib.import_module(req["module"])
    fn = _resolve(mod, req["func"])
    trace_file = os.path.realpath(req["trace_file"]) if req.get("trace_file") else None
    lines: set[int] = set()

    def local(frame, event, arg):
        if event == "line":
            lines.add(frame.f_lineno)
        return local

    def glob(frame, event, arg):
        if trace_file and os.path.realpath(frame.f_code.co_filename) == trace_file:
            return local
        return None

    signal.signal(signal.SIGALRM, _alarm)
    results = []
    for args in req["cases"]:
        lines.clear()
        signal.alarm(2)
        if trace_file:
            sys.settrace(glob)
        try:
            value = fn(*args)
            sys.settrace(None)
            signal.alarm(0)
            results.append({"status": "return", "repr": repr(value), "literal": _literal_ok(value),
                            "type": type(value).__name__, "lines": sorted(lines)})
        except _Timeout:
            sys.settrace(None)
            results.append({"status": "timeout", "lines": sorted(lines)})
        except Exception as exc:  # noqa: BLE001 - we record every exception type
            sys.settrace(None)
            signal.alarm(0)
            results.append({"status": "raise", "exc": type(exc).__name__, "exc_module": type(exc).__module__,
                            "msg": str(exc)[:120], "lines": sorted(lines)})
    print(json.dumps(results))


def same_outcome(a: dict, b: dict) -> bool:
    if a.get("status") != b.get("status"):
        return False
    if a["status"] == "raise":
        return a.get("exc") == b.get("exc")
    if a["status"] == "return":
        if a.get("literal") and b.get("literal"):
            return _same(ast.literal_eval(a["repr"]), ast.literal_eval(b["repr"]))
        return a.get("repr") == b.get("repr")
    return True


if __name__ == "__main__":
    main()
