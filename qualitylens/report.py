"""Markdown report, suitable for a pull-request comment or a CI job summary."""
from __future__ import annotations


def _pct(v) -> str:
    return "n/a" if v is None else f"{100 * v:.0f}%"


def to_markdown(r: dict) -> str:
    s = r["score"]
    out = [f"## QualityLens report `{r['base']}..{r['head']}`", "",
           f"**Quality score: {s['quality_score']}/100 (grade {s['grade']})**", ""]
    if s.get("learned"):
        lr = s["learned"]
        out += [f"Learned defect probability: **{100 * lr['defect_probability']:.0f}%**"
                + (f" (driven by: {', '.join(lr['top_factors'])})" if lr["top_factors"] else ""), ""]
    if s["reasons"]:
        out.append("Main risks:")
        for reason in s["reasons"][:4]:
            out.append(f"- {reason['label']} (-{reason['points_lost']} points)")
        out.append("")
    cov, mut, tests = r["coverage"], r["mutation"], r["tests"]
    out += ["| Signal | Before | With generated tests |", "|---|---|---|",
            f"| Changed-line coverage | {_pct(cov['before'])} | {_pct(cov['after'])} |",
            f"| Mutation score on changed lines ({mut['total']} mutants) | {_pct(mut['before'])} | "
            f"{_pct(mut['after'])} |",
            f"| Failing existing tests | {len(tests['new_failures'])} | |", ""]
    if r["functions"]:
        out += ["### Changed functions", "", "| Function | Lines | Tests | Behaviour vs base | Complexity |",
                "|---|---|---|---|---|"]
        for f in r["functions"]:
            b = f["behaviour"]
            if b.get("new"):
                beh = "new function"
            elif not b["comparable"]:
                beh = "signature changed"
            elif b["changed"]:
                beh = f"changed on {b['changed']}/{b['cases']} inputs" + (" (tests updated)" if
                                                                           b["acknowledged_by_test_update"] else "")
            else:
                beh = f"same on {b['cases']} inputs"
            rv = f["review"]
            out.append(f"| `{f['function']}` | {len(f['changed_lines'])} | {len(f['tests'])} | {beh} | "
                       f"{rv['complexity']} ({rv['complexity_delta']:+d}) |")
        out.append("")
        examples = [e for f in r["functions"] for e in f["behaviour"].get("examples", [])]
        if examples:
            out += ["### Behaviour changes to review", ""] + [f"- `{e}`" for e in examples[:6]] + [""]
        findings = [(f["function"], x) for f in r["functions"] for x in f["review"]["findings"]]
        if findings:
            out += ["### Code findings", ""] + [f"- `{fn}` line {x['line']}: {x['message']}" for fn, x in findings] + [""]
    if mut["survived_before"]:
        out += ["### Untested change points (surviving mutants)", ""] + [f"- {m}" for m in mut["survived_before"][:6]]
        out.append("")
    if tests["generated"]:
        out += ["### Generated tests", ""]
        for g in tests["generated"]:
            out.append(f"- `{g['file']}`: {g['tests']} cases for `{g['function']}` ({g['backend']})")
        out.append("")
    if r["dependencies"]["callers"]:
        out += [f"Callers affected: {', '.join('`' + c + '`' for c in r['dependencies']['callers'][:8])}", ""]
    out.append(f"_Analysed in {r['seconds']} s._")
    return "\n".join(out) + "\n"
