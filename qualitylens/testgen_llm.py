"""LLM test generation with execution-based validation and one repair round.

Generated code is checked before it runs (allowed imports, no file/network/process access), executed
in a copy of the head tree, and only passing tests are kept. Failing LLM expectations are reported
as disagreements: either the test is wrong or the code is, so a human should look.
"""
from __future__ import annotations

import ast
import shutil
import tempfile
from pathlib import Path

from .codemap import FunctionInfo
from .llm_client import LLMClient, extract_code
from .runner import run_tests
from .testgen import GeneratedTests, supported

SYSTEM = ("You are a senior Python test engineer. Write focused pytest unit tests that check the intended "
          "behaviour of a function, including boundary values and error cases. Reply with one ```python code "
          "block only. Do not read files, use the network, start processes or use randomness.")
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input"}
FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "requests", "urllib", "random"}


def build_prompt(fn: FunctionInfo, context: dict) -> str:
    parts = [f"Module: `{fn.module}` (import it as `from {fn.module} import {fn.name}`)",
             f"Function under test (changed lines: {sorted(context.get('changed_lines', []))}):",
             f"```python\n{fn.source}\n```"]
    for callee in context.get("callee_sources", [])[:3]:
        parts.append(f"It calls:\n```python\n{callee}\n```")
    if context.get("example_test"):
        parts.append(f"Existing test style in this project:\n```python\n{context['example_test'][:1500]}\n```")
    if context.get("observations"):
        obs = "\n".join(context["observations"][:8])
        parts.append(f"Observed calls on the current code (may contain bugs, do not copy blindly):\n{obs}")
    parts.append("Write 6-12 tests. Use pytest.approx for floats and pytest.raises for errors.")
    return "\n\n".join(parts)


def check_safety(code: str, allowed_roots: set[str]) -> list[str]:
    problems = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                root = name.split(".")[0]
                if root in FORBIDDEN_MODULES or (root not in allowed_roots and root not in {"pytest", "math",
                                                                                          "decimal"}):
                    problems.append(f"import not allowed: {name}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            problems.append(f"call not allowed: {node.func.id}()")
    if not any(isinstance(n, ast.FunctionDef) and n.name.startswith("test") for n in ast.walk(tree)):
        problems.append("no test functions found")
    return problems


def keep_tests(code: str, keep: set[str]) -> str:
    tree = ast.parse(code)
    tree.body = [n for n in tree.body
                 if not (isinstance(n, ast.FunctionDef) and n.name.startswith("test")) or n.name in keep]
    return ast.unparse(tree) + "\n"


def run_candidate(head_root, filename: str, code: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "head"
        shutil.copytree(head_root, work)
        target = work / "tests" / "_ql_candidate" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code)
        res = run_tests(work, [str(target.relative_to(work))], timeout=60)
    outcomes: dict[str, str] = {}
    for nodeid, entry in res["tests"].items():
        func = nodeid.split("::")[-1].split("[")[0]
        prev = outcomes.get(func, "passed")
        outcomes[func] = entry.get("outcome", "error") if prev == "passed" else prev
    return {"outcomes": outcomes, "output": res.get("output", "")}


class LLMGenerator:
    name = "llm"

    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    def generate(self, root, fn: FunctionInfo, context: dict | None = None) -> GeneratedTests | None:
        if not supported(fn):
            return None
        context = context or {}
        allowed = {fn.module.split(".")[0]}
        fname = f"test_ql_llm_{fn.module.replace('.', '_')}_{fn.name}.py"
        prompt = build_prompt(fn, context)
        notes: list[str] = []
        code = extract_code(self.client.chat(SYSTEM, prompt))
        for attempt in range(2):
            problems = check_safety(code, allowed)
            if not problems:
                result = run_candidate(root, fname, code)
                passed = {t for t, o in result["outcomes"].items() if o == "passed"}
                failed = {t for t, o in result["outcomes"].items() if o != "passed"}
                if passed or attempt == 1:
                    final = keep_tests(code, passed) if passed else ""
                    return GeneratedTests(function=fn.qualname, filename=fname, code=final, n_tests=len(passed),
                                          backend=self.name, notes=notes + [f"{len(passed)} passed, "
                                                                           f"{len(failed)} rejected"],
                                          disagreements=sorted(failed)) if passed else None
                problems = [f"all tests failed or errored:\n{result['output'][-1500:]}"]
            notes.append(f"attempt {attempt + 1} rejected: {problems[0][:200]}")
            if attempt == 0:
                repair = (prompt + "\n\nYour previous answer was rejected:\n" + "\n".join(problems)[:2000]
                          + "\nReturn a corrected test file.")
                code = extract_code(self.client.chat(SYSTEM, repair))
        return None
