"""pytest plugin: records per-test outcomes and the source lines each test executes.

Loaded with `-p qualitylens.pytest_plugin`. Output path comes from QL_TRACE_OUT, the project root
from QL_ROOT. Uses sys.settrace, so it needs no third-party coverage package.
"""
from __future__ import annotations

import json
import os
import sys
import threading

import pytest

_ROOT = os.path.realpath(os.environ.get("QL_ROOT", os.getcwd()))
_OUT = os.environ.get("QL_TRACE_OUT")
_results: dict[str, dict] = {}
_current: dict[str, set] | None = None
_inside: dict[str, str | None] = {}


def _rel(filename: str) -> str | None:
    if filename not in _inside:
        real = os.path.realpath(filename)
        ok = (not filename.startswith("<") and filename.endswith(".py")
              and real.startswith(_ROOT + os.sep) and "site-packages" not in real)
        _inside[filename] = os.path.relpath(real, _ROOT) if ok else None
    return _inside[filename]


def _local(frame, event, arg):
    if event == "line" and _current is not None:
        rel = _rel(frame.f_code.co_filename)
        if rel is not None:
            _current.setdefault(rel, set()).add(frame.f_lineno)
    return _local


def _global(frame, event, arg):
    if _rel(frame.f_code.co_filename) is None:
        return None
    return _local


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    global _current
    _current = {}
    threading.settrace(_global)
    sys.settrace(_global)
    try:
        yield
    finally:
        sys.settrace(None)
        threading.settrace(None)
        lines = {k: sorted(v) for k, v in (_current or {}).items()}
        _results.setdefault(item.nodeid, {})["lines"] = lines
        _current = None


def pytest_runtest_logreport(report):
    entry = _results.setdefault(report.nodeid, {})
    if report.when == "call":
        entry["outcome"] = report.outcome
    elif report.failed:
        entry["outcome"] = "error"
    entry.setdefault("lines", {})


def pytest_sessionfinish(session, exitstatus):
    if _OUT:
        with open(_OUT, "w", encoding="utf-8") as fh:
            json.dump({"tests": _results, "exitstatus": int(exitstatus)}, fh)
