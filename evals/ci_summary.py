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


def trigger_cell(run: dict) -> str:
    triggered = run.get("skill_triggered")
    if triggered is True:
        return "✅ yes"
    if triggered is False:
        return "❌ no"
    return "—"


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
    print("| Eval | Name | Passed | Skill triggered |")
    print("|---|---|---|---|")
    for r in runs:
        res = r["result"]
        passed_cell = f"{res['passed']}/{res['total']}"
        if r.get("skill_triggered") is False:
            passed_cell += " _(skipped)_"
        print(
            f"| {r['eval_id']} | {r['eval_name']} | {passed_cell} | {trigger_cell(r)} |"
        )

    print()
    print("## Skill trigger rate")
    print()
    triggered = summary.get("skill_triggered")
    trigger_total = summary.get("skill_trigger_total")
    rate = summary.get("skill_trigger_rate")
    if trigger_total:
        rate_str = "n/a" if rate is None else f"{rate}"
        print(
            f"**{triggered}/{trigger_total} runs triggered the skill** "
            f"(trigger rate {rate_str})"
        )
    else:
        print("_No trigger detection data available._")
    print()
    print("| Eval | Name | Triggered | Skill invocations |")
    print("|---|---|---|---|")
    for r in runs:
        invocations = r.get("skill_invocations") or []
        invo_cell = ", ".join(f"`{s}`" for s in invocations) if invocations else "—"
        print(
            f"| {r['eval_id']} | {r['eval_name']} | {trigger_cell(r)} | {invo_cell} |"
        )


if __name__ == "__main__":
    main()
