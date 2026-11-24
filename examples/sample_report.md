## QualityLens report `main..feature`

**Quality score: 57.8/100 (grade C)**

Learned defect probability: **92%** (driven by: untested_behaviour_change, weak_tests, dependency_impact)

Main risks:
- Behaviour changed without a matching test update (-25.0 points)
- Tests do not detect faults in the changed lines (-15.0 points)
- Change size (-1.2 points)
- Other functions depend on the changed code (-1.0 points)

| Signal | Before | With generated tests |
|---|---|---|
| Changed-line coverage | 100% | 100% |
| Mutation score on changed lines (2 mutants) | 0% | 100% |
| Failing existing tests | 0 | |

### Changed functions

| Function | Lines | Tests | Behaviour vs base | Complexity |
|---|---|---|---|---|
| `shopcalc.pricing:bulk_discount_rate` | 1 | 2 | changed on 1/13 inputs | 4 (+0) |

### Behaviour changes to review

- `bulk_discount_rate(50,): 0.1 -> 0.05`

### Untested change points (surviving mutants)

- shopcalc/pricing.py line 34: `>` -> `>=`
- shopcalc/pricing.py line 34: `50` -> `51`

### Generated tests

- `tests/generated_by_qualitylens/test_ql_shopcalc_pricing_bulk_discount_rate.py`: 12 cases for `shopcalc.pricing:bulk_discount_rate` (deterministic)

Callers affected: `shopcalc.orders:order_total`, `shopcalc.pricing:line_total`

_Analysed in about 3 s._
