"""Run pytest and the call harness in subprocesses with timeouts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PKG_PARENT = str(Path(__file__).resolve().parent.parent)


def _env(root: str | Path, **extra: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([PKG_PARENT, str(root)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["QL_ROOT"] = str(Path(root).resolve())
    env.update(extra)
    return env


def run_tests(root: str | Path, targets: list[str] | None = None, timeout: int = 120) -> dict:
    """Run pytest with the tracing plugin; returns {"tests": {nodeid: {outcome, lines}}, "exitstatus"}."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out_path = tf.name
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "qualitylens.pytest_plugin", "-p", "no:cacheprovider",
           "--no-header", "-rN", *(targets or [])]
    try:
        proc = subprocess.run(cmd, cwd=root, env=_env(root, QL_TRACE_OUT=out_path), capture_output=True,
                              text=True, timeout=timeout)
        try:
            data = json.loads(Path(out_path).read_text() or "{}")
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data.setdefault("tests", {})
        data["returncode"] = proc.returncode
        data["output"] = (proc.stdout + proc.stderr)[-4000:]
        return data
    except subprocess.TimeoutExpired:
        return {"tests": {}, "returncode": -1, "output": "timeout"}
    finally:
        Path(out_path).unlink(missing_ok=True)


def tests_pass(root: str | Path, targets: list[str], timeout: int = 30) -> bool:
    """True when every selected test passes (used for mutation testing)."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--no-header", *targets]
    try:
        proc = subprocess.run(cmd, cwd=root, env=_env(root), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


def call_harness(root: str | Path, module: str, func: str, cases: list[list], trace_file: str | None = None,
                 timeout: int = 60) -> list[dict]:
    payload = json.dumps({"module": module, "func": func, "cases": cases, "trace_file": trace_file})
    try:
        proc = subprocess.run([sys.executable, "-m", "qualitylens.harness"], input=payload, cwd=root,
                              env=_env(root), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [{"status": "timeout"} for _ in cases]
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return [{"status": "harness-error", "detail": proc.stderr[-500:]} for _ in cases]
