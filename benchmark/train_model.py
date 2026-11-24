"""Train and evaluate the learned defect-probability model on benchmark results.

Evaluations (all AUCs are on data the model was not trained on):
  1. Cross-project: train on one project, test on the other.
  2. Repeated stratified 5-fold cross-validation on both projects together.
  3. Held-out generated bugs (if results/holdout.json exists): share of bugs with probability >= 0.5.
The final model is trained on all labelled cases and written to qualitylens/models/risk_model.json.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from qualitylens.learned import FEATURES, MODEL_PATH, fit, predict  # noqa: E402
from run_benchmark import auc  # noqa: E402


def rule_risk(r):
    return 100 - r["quality_score"]


def main() -> None:
    data = json.loads((HERE / "results" / "results.json").read_text())
    rows = data["cases"]
    projects = sorted({r["project"] for r in rows})
    report = {"cross_project": {}, "cv": {}, "holdout": None}

    for test_p in projects:
        train = [r for r in rows if r["project"] != test_p]
        test = [r for r in rows if r["project"] == test_p]
        model = fit(train)
        probs = [predict(model, r["components"])["defect_probability"] for r in test]
        labels = [r["label"] for r in test]
        report["cross_project"][f"train_{'+'.join(sorted({r['project'] for r in train}))}_test_{test_p}"] = {
            "learned_auc": round(auc(probs, labels), 3),
            "rule_auc": round(auc([rule_risk(r) for r in test], labels), 3),
            "learned_recall_at_0.5": round(sum(p >= 0.5 for p, y in zip(probs, labels) if y) / sum(labels), 3),
            "learned_false_alarms_at_0.5": sum(p >= 0.5 for p, y in zip(probs, labels) if not y),
        }

    from sklearn.model_selection import RepeatedStratifiedKFold
    labels = [r["label"] for r in rows]
    learned, rule = [], []
    for tr, te in RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=0).split(rows, labels):
        model = fit([rows[i] for i in tr])
        te_rows = [rows[i] for i in te]
        y = [r["label"] for r in te_rows]
        learned.append(auc([predict(model, r["components"])["defect_probability"] for r in te_rows], y))
        rule.append(auc([rule_risk(r) for r in te_rows], y))
    report["cv"] = {"folds": len(learned), "learned_auc_mean": round(statistics.mean(learned), 3),
                    "learned_auc_sd": round(statistics.stdev(learned), 3),
                    "rule_auc_mean": round(statistics.mean(rule), 3), "rule_auc_sd": round(statistics.stdev(rule), 3)}

    final = fit(rows)
    hold_path = HERE / "results" / "holdout.json"
    if hold_path.exists():
        hold = json.loads(hold_path.read_text())["cases"]
        probs = [predict(final, r["components"])["defect_probability"] for r in hold]
        report["holdout"] = {"bugs": len(hold), "learned_flagged_at_0.5": sum(p >= 0.5 for p in probs),
                             "rule_flagged_below_70": sum(r["quality_score"] < 70 for r in hold)}

    cross = [v["learned_auc"] for v in report["cross_project"].values()]
    final.update({"version": 1, "trained_on": f"{len(rows)} labelled changes ({', '.join(projects)})",
                  "trained": date.today().isoformat(), "cross_project_auc": round(statistics.mean(cross), 3),
                  "evaluation": report})
    MODEL_PATH.parent.mkdir(exist_ok=True)
    MODEL_PATH.write_text(json.dumps(final, indent=2))
    (HERE / "results" / "model_evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print("coefficients:", dict(zip(FEATURES, final["coef"])), "intercept", final["intercept"])


if __name__ == "__main__":
    main()
