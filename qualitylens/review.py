"""Code quality analysis of the changed functions: static metrics, rule checks and optional LLM review.

LLM findings are only kept when they cite a line that the change actually touched, so the model
cannot report issues about code it was not shown or invent line numbers.
"""
from __future__ import annotations

from .codemap import FunctionInfo
from .llm_client import LLMClient, extract_json

REVIEW_SYSTEM = ("You review Python code changes for correctness and maintainability risks. Reply with a JSON "
                 "list of objects {\"line\": int, \"severity\": \"high\"|\"medium\"|\"low\", \"message\": str}. "
                 "Only report concrete problems on the changed lines. Reply [] if there are none.")


def static_review(head_fn: FunctionInfo, base_fn: FunctionInfo | None, changed_lines: set[int]) -> dict:
    m = head_fn.metrics
    # a brand-new function counts its whole complexity above the minimum of 1 as added complexity
    delta = m["complexity"] - (base_fn.metrics["complexity"] if base_fn else 1)
    findings = [f for f in m.get("findings", []) if f["line"] in changed_lines]
    if m["complexity"] > 10:
        findings.append({"line": head_fn.start, "rule": "high-complexity",
                         "message": f"Cyclomatic complexity {m['complexity']} (> 10)."})
    if m["length"] > 60:
        findings.append({"line": head_fn.start, "rule": "long-function", "message": f"{m['length']} lines long."})
    if m["nesting"] > 3:
        findings.append({"line": head_fn.start, "rule": "deep-nesting", "message": f"Nesting depth {m['nesting']}."})
    if head_fn.is_public and not m["has_docstring"] and base_fn is None:
        findings.append({"line": head_fn.start, "rule": "missing-docstring", "message": "New public function "
                                                                                       "without docstring."})
    return {"complexity": m["complexity"], "complexity_delta": delta, "nesting": m["nesting"],
            "length": m["length"], "findings": findings}


def llm_review(client: LLMClient, fn: FunctionInfo, changed_lines: set[int]) -> list[dict]:
    numbered = "\n".join(f"{fn.start + i:>4} {line}" for i, line in enumerate(fn.source.splitlines()))
    prompt = (f"Function `{fn.qualname}` (changed lines: {sorted(changed_lines)}):\n```python\n{numbered}\n```")
    try:
        items = extract_json(client.chat(REVIEW_SYSTEM, prompt))
    except Exception:  # noqa: BLE001 - a failed review must not break the analysis
        return []
    verified = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        line = it.get("line")
        if isinstance(line, int) and line in changed_lines and it.get("severity") in {"high", "medium", "low"}:
            verified.append({"line": line, "rule": f"llm-{it['severity']}", "message": str(it.get("message"))[:300]})
    return verified
