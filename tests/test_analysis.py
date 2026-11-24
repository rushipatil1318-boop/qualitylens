"""Unit tests: diff parsing, AST analysis, input generation, dependencies, scoring."""
import textwrap

from qualitylens.codemap import analyse_module, complexity, functions_touching
from qualitylens.deps import build_graph, impact
from qualitylens.gitutils import parse_unified_diff
from qualitylens.inputs import generate_cases, pool_for
from qualitylens.score import WEIGHTS, components, score

DIFF = textwrap.dedent("""\
    diff --git a/pkg/a.py b/pkg/a.py
    --- a/pkg/a.py
    +++ b/pkg/a.py
    @@ -3 +3 @@ def f(x):
    -    return x + 1
    +    return x + 2
    @@ -10,0 +11,2 @@ def g():
    +    y = 1
    +    return y
    diff --git a/pkg/new.py b/pkg/new.py
    --- /dev/null
    +++ b/pkg/new.py
    @@ -0,0 +1 @@
    +X = 1
    """)


def test_parse_unified_diff_lines_and_status():
    files = parse_unified_diff(DIFF)
    assert files["pkg/a.py"].status == "M"
    assert files["pkg/a.py"].added == {3, 11, 12}
    assert files["pkg/a.py"].removed == {3}
    assert files["pkg/new.py"].status == "A" and files["pkg/new.py"].added == {1}


def test_functions_and_metrics(sample_root):
    funcs = {f.name: f for f in analyse_module(sample_root, "shopcalc/pricing.py")}
    assert set(funcs) >= {"apply_discount", "tax_for", "bulk_discount_rate", "line_total"}
    bulk = funcs["bulk_discount_rate"]
    assert bulk.metrics["complexity"] == 4
    assert [p.name for p in funcs["apply_discount"].params] == ["price", "code"]
    hit = functions_touching(list(funcs.values()), {bulk.start + 3})
    assert [f.name for f in hit] == ["bulk_discount_rate"]


def test_literal_mining_prioritises_comparisons(sample_root):
    funcs = {f.name: f for f in analyse_module(sample_root, "shopcalc/shipping.py")}
    nums = funcs["shipping_cost"].literals["num"]
    # thresholds used in comparisons come before other numbers; membership on a dict uses its keys only
    assert nums.index(75.0) < nums.index(1.5)
    assert 4.9 not in nums[:4]
    assert "domestic" in funcs["shipping_cost"].literals["str"]


def test_input_pool_contains_boundaries(sample_root):
    funcs = {f.name: f for f in analyse_module(sample_root, "shopcalc/pricing.py")}
    pool = pool_for(funcs["bulk_discount_rate"].params[0], funcs["bulk_discount_rate"])
    assert {49, 50, 51, 99, 100, 101}.issubset(set(pool))
    assert len(generate_cases(funcs["apply_discount"])) > 20


def test_complexity_counts_branches():
    import ast
    fn = ast.parse("def f(a, b):\n    if a and b:\n        return 1\n    for i in range(3):\n        pass\n"
                   "    return 0\n").body[0]
    assert complexity(fn) == 4


def test_dependency_impact(sample_root):
    g = build_graph(sample_root)
    res = impact(g, ["shopcalc.pricing:bulk_discount_rate"])
    assert "shopcalc.pricing:line_total" in res["callers"]
    assert "shopcalc.orders:order_total" in res["callers"]
    assert any("test_bulk_rate" in t for t in res["tests"])


def test_score_weights_and_ranges():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    clean = score({"comparable_functions": 1, "changed_line_coverage": 1.0, "mutation_score": 1.0})
    assert clean["quality_score"] == 100.0 and clean["grade"] == "A"
    risky = score({"new_failures": 1, "comparable_functions": 1, "unacknowledged_changes": 1,
                   "changed_line_coverage": 0.0, "mutation_score": 0.0, "churn": 100})
    assert risky["quality_score"] < 20 and risky["reasons"][0]["signal"] == "failing_tests"
    assert components({"mutation_score": None})["weak_tests"] == 0.0
