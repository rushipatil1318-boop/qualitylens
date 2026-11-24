"""Explainable change-risk score. Each signal is normalised to 0..1 (1 = risky) and weighted.

Weights were set by hand from the signal definitions before running the benchmark, not fitted to it.
Quality score = 100 * (1 - risk).
"""
from __future__ import annotations

import math

WEIGHTS = {
    "failing_tests": 0.30,             # existing tests that now fail
    "untested_behaviour_change": 0.25, # behaviour changed vs base and no updated test covers it
    "uncovered_changed_lines": 0.15,   # changed lines no existing test executes
    "weak_tests": 0.15,                # mutants on changed lines that existing tests do not catch
    "complexity_increase": 0.05,
    "dependency_impact": 0.05,         # how many other functions call the changed code
    "churn": 0.05,
}

LABELS = {
    "failing_tests": "Existing tests fail",
    "untested_behaviour_change": "Behaviour changed without a matching test update",
    "uncovered_changed_lines": "Changed lines not covered by tests",
    "weak_tests": "Tests do not detect faults in the changed lines",
    "complexity_increase": "Complexity increased",
    "dependency_impact": "Other functions depend on the changed code",
    "churn": "Change size",
}


def components(signals: dict) -> dict[str, float]:
    """signals: raw measurements collected by the pipeline."""
    c = {}
    c["failing_tests"] = 1.0 if signals.get("new_failures", 0) > 0 else 0.0
    comparable = signals.get("comparable_functions", 0)
    c["untested_behaviour_change"] = (signals.get("unacknowledged_changes", 0) / comparable) if comparable else 0.0
    cov = signals.get("changed_line_coverage")
    c["uncovered_changed_lines"] = 0.0 if cov is None else 1.0 - cov
    ms = signals.get("mutation_score")
    c["weak_tests"] = 0.0 if ms is None else 1.0 - ms  # no mutants on the changed lines: no evidence
    c["complexity_increase"] = min(1.0, max(0, signals.get("complexity_delta", 0)) / 5)
    c["dependency_impact"] = min(1.0, signals.get("callers", 0) / 10)
    churn = signals.get("churn", 0)
    c["churn"] = min(1.0, math.log1p(churn) / math.log1p(100))
    return {k: round(v, 4) for k, v in c.items()}


def score(signals: dict) -> dict:
    comp = components(signals)
    risk = sum(WEIGHTS[k] * v for k, v in comp.items())
    quality = round(100 * (1 - risk), 1)
    grade = "A" if quality >= 85 else "B" if quality >= 70 else "C" if quality >= 55 else "D" if quality >= 40 else "E"
    contrib = sorted(((WEIGHTS[k] * v, k) for k, v in comp.items() if v > 0), reverse=True)
    reasons = [{"signal": k, "label": LABELS[k], "value": comp[k], "points_lost": round(100 * w, 1)}
               for w, k in contrib]
    return {"quality_score": quality, "risk": round(risk, 4), "grade": grade, "components": comp,
            "reasons": reasons}
