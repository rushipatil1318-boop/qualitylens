"""Command line: python -m qualitylens analyze --repo . --base origin/main --head HEAD"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import Options, analyze
from .report import to_markdown
from .report_html import hotspots_html, to_html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="qualitylens", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="score a change and generate tests for it")
    a.add_argument("--repo", default=".")
    a.add_argument("--base", default="HEAD~1")
    a.add_argument("--head", default="HEAD")
    a.add_argument("--backend", choices=["deterministic", "llm"], default="deterministic")
    a.add_argument("--llm-review", action="store_true", help="add LLM code review (needs QL_LLM_* settings)")
    a.add_argument("--no-mutation", action="store_true")
    a.add_argument("--mutants", type=int, default=10, help="mutants per changed file")
    a.add_argument("--out", default="qualitylens-report", help="output folder for report and tests")
    a.add_argument("--fail-under", type=float, default=None, help="exit 1 if the quality score is lower")
    a.add_argument("--model", default=None, help="learned model JSON (default: packaged model)")
    h = sub.add_parser("hotspots", help="rank files by change frequency x complexity from git history")
    h.add_argument("--repo", default=".")
    h.add_argument("--since", default=None, help='e.g. "6 months ago"')
    h.add_argument("--top", type=int, default=10)
    h.add_argument("--out", default="qualitylens-report")
    args = ap.parse_args(argv)

    if args.cmd == "hotspots":
        from .history import hotspots, to_markdown as hotspots_md
        res = hotspots(args.repo, args.since, args.top)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "hotspots.json").write_text(json.dumps(res, indent=2))
        (out / "hotspots.html").write_text(hotspots_html(res))
        md = hotspots_md(res)
        (out / "hotspots.md").write_text(md)
        print(md)
        return 0

    client = None
    if args.backend == "llm" or args.llm_review:
        from .llm_client import LLMClient
        client = LLMClient()
    opts = Options(backend=args.backend, mutation=not args.no_mutation, mutation_cap=args.mutants,
                   llm_review=args.llm_review, llm_client=client, model_path=args.model)
    report = analyze(args.repo, args.base, args.head, opts)
    out = Path(args.out)
    (out / "generated_tests").mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(to_html(report))
    for rel, code in report.pop("generated_files").items():
        (out / "generated_tests" / Path(rel).name).write_text(code)
    (out / "report.json").write_text(json.dumps(report, indent=2))
    md = to_markdown(report)
    (out / "report.md").write_text(md)
    print(md)
    if args.fail_under is not None and report["score"]["quality_score"] < args.fail_under:
        print(f"Quality score {report['score']['quality_score']} is below {args.fail_under}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
