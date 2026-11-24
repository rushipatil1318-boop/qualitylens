"""Self-contained HTML dashboard for an analysis or a hotspot report (no JavaScript, no external files)."""
from __future__ import annotations

from html import escape

from .score import LABELS, WEIGHTS

CSS = """
:root{--navy:#14284b;--teal:#0e7c86;--grey:#5b6573;--line:#d5dce6;--bg:#f6f8fb;--red:#c2410c;--amber:#b7791f;
--green:#2f855a}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1e2430;
background:var(--bg)}main{max-width:1040px;margin:0 auto;padding:28px 20px 48px}
h1{font-size:22px;color:var(--navy);margin:0 0 2px}h2{font-size:15px;color:var(--navy);margin:28px 0 10px;
padding-bottom:6px;border-bottom:1px solid var(--line)}.sub{color:var(--grey);margin:0 0 20px}
.grid{display:grid;grid-template-columns:220px 1fr;gap:20px}.card{background:#fff;border:1px solid var(--line);
border-radius:10px;padding:16px}.big{font-size:40px;font-weight:700;color:var(--navy);line-height:1}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.kpi .v{font-size:22px;font-weight:650;color:var(--navy)}
.kpi .l{color:var(--grey);font-size:12px}.bar{height:8px;background:#e8edf3;border-radius:4px;overflow:hidden}
.bar>span{display:block;height:100%}table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
border-radius:10px;overflow:hidden}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);
vertical-align:top}th{font-size:12px;color:var(--grey);font-weight:600;background:#fbfcfe}code{font:12.5px ui-monospace,
SFMono-Regular,Menlo,monospace;background:#eef2f7;padding:1px 4px;border-radius:4px}ul{margin:6px 0 0;padding-left:18px}
details{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:8px}
pre{white-space:pre-wrap;font:12px ui-monospace,Menlo,monospace;margin:10px 0 0}.pill{display:inline-block;padding:1px 8px;
border-radius:999px;font-size:12px;font-weight:600;color:#fff}.muted{color:var(--grey)}
@media(max-width:720px){.grid{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}}
"""


def _color(score: float) -> str:
    return "var(--green)" if score >= 85 else "var(--teal)" if score >= 70 else "var(--amber)" if score >= 55 \
        else "var(--red)"


def _pct(v) -> str:
    return "n/a" if v is None else f"{100 * v:.0f}%"


def _ring(score: float) -> str:
    r, c = 52, 2 * 3.14159 * 52
    dash = c * score / 100
    return (f'<svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="Quality score {score}">'
            f'<circle cx="70" cy="70" r="{r}" fill="none" stroke="#e8edf3" stroke-width="12"/>'
            f'<circle cx="70" cy="70" r="{r}" fill="none" stroke="{_color(score)}" stroke-width="12" '
            f'stroke-linecap="round" stroke-dasharray="{dash:.1f} {c:.1f}" transform="rotate(-90 70 70)"/>'
            f'<text x="70" y="76" text-anchor="middle" font-size="30" font-weight="700" fill="#14284b">'
            f'{score:.0f}</text><text x="70" y="96" text-anchor="middle" font-size="11" fill="#5b6573">'
            f'of 100</text></svg>')


def _page(title: str, body: str) -> str:
    return (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>{escape(title)}</title><style>{CSS}</style>"
            f"</head><body><main>{body}</main></body></html>")


def to_html(r: dict) -> str:
    s, cov, mut, tests = r["score"], r["coverage"], r["mutation"], r["tests"]
    learned = s.get("learned")
    head = [f"<h1>QualityLens report</h1><p class='sub'>Change <code>{escape(r['base'])}..{escape(r['head'])}</code>"
            f" · {len(r['files_changed'])} Python file{'s' if len(r['files_changed']) != 1 else ''} · "
            f"{r['churn']} changed lines · {r['seconds']} s</p>"]
    left = (f"<div class='card' style='text-align:center'>{_ring(s['quality_score'])}"
            f"<div><span class='pill' style='background:{_color(s['quality_score'])}'>Grade {s['grade']}</span></div>")
    if learned:
        left += (f"<p class='muted' style='margin:12px 0 0'>Learned defect probability<br>"
                 f"<b style='font-size:20px;color:var(--navy)'>{100 * learned['defect_probability']:.0f}%</b></p>")
    left += "</div>"
    kpis = (f"<div class='kpis'>"
            f"<div class='card kpi'><div class='v'>{_pct(cov['before'])} → {_pct(cov['after'])}</div>"
            f"<div class='l'>Changed-line coverage (existing → with generated tests)</div></div>"
            f"<div class='card kpi'><div class='v'>{_pct(mut['before'])} → {_pct(mut['after'])}</div>"
            f"<div class='l'>Mutation score on changed lines ({mut['total']} mutants)</div></div>"
            f"<div class='card kpi'><div class='v'>{len(tests['new_failures'])}</div>"
            f"<div class='l'>Existing tests now failing</div></div></div>")
    bars = ["<div class='card' style='margin-top:12px'><b>Where the points went</b>"]
    for key, w in WEIGHTS.items():
        v = s["components"].get(key, 0.0)
        bars.append(f"<div style='display:grid;grid-template-columns:1fr 160px 60px;gap:10px;align-items:center;"
                    f"margin-top:8px'><span>{escape(LABELS[key])}</span><div class='bar'><span style='width:"
                    f"{100 * v:.0f}%;background:{'var(--red)' if v > 0.5 else 'var(--teal)'}'></span></div>"
                    f"<span class='muted'>{f'−{100 * w * v:.1f}' if v else '–'}</span></div>")
    bars.append("</div>")
    body = head + [f"<div class='grid'>{left}<div>{kpis}{''.join(bars)}</div></div>"]

    if r["functions"]:
        rows = []
        for f in r["functions"]:
            b = f["behaviour"]
            beh = ("new function" if b.get("new") else "signature changed" if not b["comparable"] else
                   f"<b style='color:var(--red)'>changed on {b['changed']}/{b['cases']} inputs</b>"
                   + (" (tests updated)" if b["acknowledged_by_test_update"] else "") if b["changed"]
                   else f"same on {b['cases']} inputs")
            ex = "".join(f"<li><code>{escape(e)}</code></li>" for e in b.get("examples", []))
            rv = f["review"]
            rows.append(f"<tr><td><code>{escape(f['function'])}</code>"
                        f"{'<br><span class=muted>via ' + escape(f['via']) + '</span>' if f['via'] != 'edit' else ''}"
                        f"</td><td>{len(f['changed_lines'])}</td><td>{len(f['tests'])}</td><td>{beh}"
                        f"{'<ul>' + ex + '</ul>' if ex else ''}</td><td>{rv['complexity']} ({rv['complexity_delta']:+d})"
                        f"</td></tr>")
        body.append("<h2>Changed functions</h2><table><tr><th>Function</th><th>Changed lines</th><th>Tests</th>"
                    "<th>Behaviour vs base</th><th>Complexity</th></tr>" + "".join(rows) + "</table>")
    findings = [(f["function"], x) for f in r["functions"] for x in f["review"]["findings"]]
    if findings or mut["survived_before"]:
        body.append("<h2>What to look at</h2><div class='card'><ul>")
        body += [f"<li><code>{escape(fn)}</code> line {x['line']}: {escape(x['message'])}</li>" for fn, x in findings]
        body += [f"<li>No test fails if this changes: <code>{escape(m)}</code></li>" for m in mut["survived_before"][:8]]
        body.append("</ul></div>")
    if tests["generated"]:
        body.append("<h2>Generated tests</h2>")
        code = r.get("generated_files", {})
        for g in tests["generated"]:
            src = escape(code.get(g["file"], ""))
            body.append(f"<details><summary><code>{escape(g['file'])}</code> · {g['tests']} cases for "
                        f"<code>{escape(g['function'])}</code> ({g['backend']})</summary><pre>{src}</pre></details>")
    if r["dependencies"]["callers"]:
        body.append("<h2>Affected callers</h2><p>" + ", ".join(f"<code>{escape(c)}</code>"
                                                               for c in r["dependencies"]["callers"]) + "</p>")
    return _page("QualityLens report", "".join(body))


def hotspots_html(h: dict) -> str:
    rows = []
    top = max([r["hotspot"] for r in h["hotspots"]] or [1])
    for r in h["hotspots"]:
        rows.append(f"<tr><td><code>{escape(r['file'])}</code></td><td style='width:180px'><div class='bar'>"
                    f"<span style='width:{100 * r['hotspot'] / top:.0f}%;background:var(--red)'></span></div>"
                    f"<span class='muted'>{r['hotspot']}</span></td><td>{r['commits']}</td>"
                    f"<td>{r['fix_commits']} ({100 * r['fix_ratio']:.0f}%)</td><td>{r['complexity']}</td>"
                    f"<td>{escape(r['most_complex'])}</td><td>{len(r['untested_functions'])} of {r['functions']}</td>"
                    f"<td>{r['authors']}</td></tr>")
    body = (f"<h1>QualityLens hotspots</h1><p class='sub'>{h['files_analysed']} source files"
            f"{' · since ' + escape(h['since']) if h['since'] else ''}. Hotspot = change frequency × complexity "
            f"(0–100).</p><table><tr><th>File</th><th>Hotspot</th><th>Commits</th><th>Bug fixes</th>"
            f"<th>Complexity</th><th>Most complex function</th><th>Untested functions</th><th>Authors</th></tr>"
            + "".join(rows) + "</table>")
    return _page("QualityLens hotspots", body)
