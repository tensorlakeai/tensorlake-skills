#!/usr/bin/env python3
"""Print a markdown summary of the latest benchmark.json.

Usage:
    python evals/ci_summary.py path/to/benchmark.json

Designed to be piped into $GITHUB_STEP_SUMMARY in CI. Always exits 0 —
eval results are informational, not a PR gate.
"""
import json
import sys
from pathlib import Path


def main() -> None:
    benchmark = json.loads(Path(sys.argv[1]).read_text())
    summary = benchmark["run_summary"]["with_skill"]
    runs = benchmark["runs"]

    print("## Eval results")
    print()
    print(
        f"**{summary['total_passed']}/{summary['total']} expectations passed** "
        f"(pass rate {summary['pass_rate']})"
    )
    print()
    print("| Eval | Name | Passed |")
    print("|---|---|---|")
    for r in runs:
        res = r["result"]
        print(f"| {r['eval_id']} | {r['eval_name']} | {res['passed']}/{res['total']} |")


if __name__ == "__main__":
    main()
