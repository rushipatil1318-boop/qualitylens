"""Tests for test generation (deterministic and LLM with a fake client), mutation testing and the pipeline."""
import json

from qualitylens.codemap import analyse_module
from qualitylens.llm_client import LLMClient, extract_code, extract_json
from qualitylens.mutation import make_mutants, mutation_score
from qualitylens.pipeline import Options, analyze
from qualitylens.report import to_markdown
from qualitylens.review import llm_review
from qualitylens.runner import run_tests
from qualitylens.testgen import DeterministicGenerator
from qualitylens.testgen_llm import LLMGenerator, check_safety


def _fn(root, rel, name):
    return next(f for f in analyse_module(root, rel) if f.name == name)


def fake_client(*answers):
    replies = list(answers)

    def transport(url, headers, body, timeout):
        return {"choices": [{"message": {"content": replies.pop(0)}}]}
    return LLMClient(base_url="http://fake/v1", model="fake", transport=transport, retries=0)


def test_deterministic_tests_pass_and_cover(sample_root):
    fn = _fn(sample_root, "shopcalc/pricing.py", "apply_discount")
    gen = DeterministicGenerator().generate(sample_root, fn)
    assert gen is not None and gen.n_tests >= 5
    target = sample_root / "tests" / gen.filename
    target.write_text(gen.code)
    res = run_tests(sample_root, [f"tests/{gen.filename}"])
    assert res["tests"] and all(e["outcome"] == "passed" for e in res["tests"].values())
    covered = {ln for e in res["tests"].values() for ln in e["lines"].get("shopcalc/pricing.py", [])}
    assert fn.exec_lines <= covered


def test_mutants_only_on_requested_lines():
    src = "def f(x):\n    if x > 1:\n        return x + 1\n    return 0\n"
    muts = make_mutants(src, {2})
    assert muts and all(m.line == 2 for m in muts)
    assert any("`>` -> `>=`" in m.description for m in muts)


def test_mutation_score_separates_weak_and_strong_tests(sample_root):
    fn = _fn(sample_root, "shopcalc/pricing.py", "bulk_discount_rate")
    gen = DeterministicGenerator().generate(sample_root, fn)
    rel = f"tests/generated/{gen.filename}"
    res = mutation_score(sample_root, "shopcalc/pricing.py", {fn.start + 3},
                         {"weak": ["tests/test_pricing.py::test_bulk_rate_small_and_large"],
                          "strong": [rel]}, extra_files={rel: gen.code})
    assert res["weak"]["total"] >= 2
    assert res["strong"]["killed"] > res["weak"]["killed"]


def test_llm_generator_keeps_only_passing_tests(sample_root):
    answer = ("```python\nimport pytest\nfrom shopcalc.pricing import bulk_discount_rate\n\n"
              "def test_tier_50():\n    assert bulk_discount_rate(50) == pytest.approx(0.10)\n\n"
              "def test_wrong_expectation():\n    assert bulk_discount_rate(10) == 0.5\n```")
    gen = LLMGenerator(fake_client(answer)).generate(sample_root, _fn(sample_root, "shopcalc/pricing.py",
                                                                      "bulk_discount_rate"))
    assert gen.n_tests == 1 and "test_tier_50" in gen.code and "test_wrong_expectation" not in gen.code
    assert gen.disagreements == ["test_wrong_expectation"]


def test_llm_generator_repairs_unsafe_answer(sample_root):
    bad = "```python\nimport os\n\ndef test_x():\n    os.remove('x')\n```"
    good = ("```python\nfrom shopcalc.pricing import tax_for\n\ndef test_de():\n"
            "    assert tax_for(100.0, 'DE') == 19.0\n```")
    gen = LLMGenerator(fake_client(bad, good)).generate(sample_root, _fn(sample_root, "shopcalc/pricing.py",
                                                                         "tax_for"))
    assert gen.n_tests == 1 and any("rejected" in n for n in gen.notes)


def test_safety_check_and_parsers():
    assert check_safety("import subprocess\ndef test_a():\n    pass\n", {"shopcalc"})
    assert not check_safety("import pytest\nfrom shopcalc.x import y\ndef test_a():\n    pass\n", {"shopcalc"})
    assert extract_code("text\n```python\nx = 1\n```") == "x = 1\n"
    assert extract_json('```json\n[{"line": 3}]\n```') == [{"line": 3}]


def test_llm_review_drops_unverified_lines(sample_root):
    fn = _fn(sample_root, "shopcalc/pricing.py", "bulk_discount_rate")
    reply = json.dumps([{"line": fn.start + 3, "severity": "high", "message": "boundary"},
                        {"line": 999, "severity": "high", "message": "invented"}])
    found = llm_review(fake_client(reply), fn, {fn.start + 3})
    assert [f["line"] for f in found] == [fn.start + 3]


def test_pipeline_flags_untested_bug(make_change):
    repo = make_change([("shopcalc/pricing.py", "if quantity >= 50:", "if quantity > 50:")])
    report = analyze(repo, "HEAD~1", "HEAD", Options(mutation_cap=4))
    assert report["tests"]["new_failures"] == []          # the existing tests miss this bug
    assert report["score"]["quality_score"] < 70
    assert any("(50,)" in e for f in report["functions"] for e in f["behaviour"]["examples"])
    assert report["coverage"]["after"] == 1.0
    assert "QualityLens report" in to_markdown(report)


def test_pipeline_trusts_safe_refactor(make_change):
    repo = make_change([("shopcalc/utils.py", "def clamp(value: float, low: float, high: float) -> float:\n",
                         'def clamp(value: float, low: float, high: float) -> float:\n    """Limit value."""\n')])
    report = analyze(repo, "HEAD~1", "HEAD", Options(mutation_cap=4))
    assert report["score"]["quality_score"] >= 85
