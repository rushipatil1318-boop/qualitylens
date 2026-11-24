"""Learned defect-probability model on top of the score signals.

Training (benchmark/train_model.py) fits a class-balanced logistic regression with scikit-learn and stores
the coefficients as JSON. Inference here is a dot product + sigmoid, so the package does not need
scikit-learn at runtime. The hand-weighted score stays the primary, fully explainable output; the
learned probability is reported next to it with its per-signal contributions.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .score import WEIGHTS

FEATURES = list(WEIGHTS)
MODEL_PATH = Path(__file__).resolve().parent / "models" / "risk_model.json"


def load_model(path: str | Path | None = None) -> dict | None:
    p = Path(path) if path else MODEL_PATH
    if not p.exists():
        return None
    model = json.loads(p.read_text())
    if model.get("features") != FEATURES:
        return None  # trained on a different signal set
    return model


def predict(model: dict, components: dict) -> dict:
    contributions = {f: model["coef"][i] * components.get(f, 0.0) for i, f in enumerate(model["features"])}
    z = model["intercept"] + sum(contributions.values())
    p = 1 / (1 + math.exp(-z))
    top = sorted(((v, k) for k, v in contributions.items() if v > 0), reverse=True)[:3]
    return {"defect_probability": round(p, 3), "top_factors": [k for _, k in top],
            "model": {k: model.get(k) for k in ("version", "trained_on", "cross_project_auc")}}


def fit(rows: list[dict], c: float = 1.0) -> dict:
    """rows: [{"components": {...}, "label": 0|1}] -> JSON-serialisable model."""
    from sklearn.linear_model import LogisticRegression

    x = [[r["components"][f] for f in FEATURES] for r in rows]
    y = [r["label"] for r in rows]
    clf = LogisticRegression(C=c, class_weight="balanced", max_iter=1000)
    clf.fit(x, y)
    return {"features": FEATURES, "coef": [round(float(v), 5) for v in clf.coef_[0]],
            "intercept": round(float(clf.intercept_[0]), 5)}
