"""Tests for the learned model, hotspot analysis, HTML reports and the CLI."""
import json
import subprocess

from qualitylens.cli import main
from qualitylens.history import commit_stats, hotspots, to_markdown
from qualitylens.learned import FEATURES, load_model, predict
from qualitylens.report_html import hotspots_html



def _commit(repo, msg, author="dev"):
    subprocess.run(["git", "-c", "user.email=t@q", "-c", f"user.name={author}", "commit", "-qam", msg],
                   cwd=repo, check=True)


def _history_repo(tmp_path, sample_root):
    repo = sample_root
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    _commit(repo, "initial import")
    pricing = repo / "shopcalc" / "pricing.py"
    for i, msg in enumerate(["fix rounding bug in discount", "add voucher", "Fix VIP threshold", "tweak tax"]):
        pricing.write_text(pricing.read_text() + f"\n# change {i}\n")
        _commit(repo, msg, author=f"dev{i % 2}")
    utils = repo / "shopcalc" / "utils.py"
    utils.write_text(utils.read_text() + "\n# docs\n")
    _commit(repo, "docs")
    return repo


def test_packaged_model_predicts_probabilities():
    model = load_model()
    assert model is not None and model["features"] == FEATURES
    risky = predict(model, {"failing_tests": 1.0, "untested_behaviour_change": 1.0, "weak_tests": 1.0})
    safe = predict(model, {})
    assert 0 <= safe["defect_probability"] < 0.5 < risky["defect_probability"] <= 1
    assert risky["top_factors"][0] == "untested_behaviour_change"


def test_commit_stats_counts_fixes(tmp_path, sample_root):
    repo = _history_repo(tmp_path, sample_root)
    stats = commit_stats(repo)
    s = stats["shopcalc/pricing.py"]
    assert s["commits"] == 5 and s["fix_commits"] == 2 and len(s["authors"]) == 3


def test_hotspots_rank_busy_complex_file_first(tmp_path, sample_root):
    repo = _history_repo(tmp_path, sample_root)
    res = hotspots(repo)
    top = res["hotspots"][0]
    assert top["file"] == "shopcalc/pricing.py" and top["hotspot"] == 100.0
    assert "untested_functions" in top and "pricing.py" in to_markdown(res)
    assert "<table>" in hotspots_html(res)


def test_cli_analyze_writes_all_outputs(make_change, tmp_path):
    repo = make_change([("shopcalc/inventory.py", "    return stock <= reorder_point",
                         "    return stock < reorder_point")])
    out = tmp_path / "out"
    code = main(["analyze", "--repo", str(repo), "--out", str(out), "--mutants", "3", "--fail-under", "70"])
    assert code == 1  # the untested boundary bug scores below the gate
    report = json.loads((out / "report.json").read_text())
    assert report["score"]["learned"]["defect_probability"] > 0.5
    html = (out / "report.html").read_text()
    assert "QualityLens report" in html and "reorder_needed" in html
    assert list((out / "generated_tests").glob("test_ql_*.py"))
