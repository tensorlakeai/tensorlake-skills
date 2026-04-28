#!/usr/bin/env python3
"""Grade the latest with_skill outputs against the expectations in evals.json.

For each (eval, output.md) pair under evals/workspace/iteration-N/, spawns a
`claude -p` judge that returns pass/fail per expectation. Results are aggregated
into evals/workspace/iteration-N/benchmark.json.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_JSON = REPO / "evals" / "evals.json"
WORKSPACE = REPO / "evals" / "workspace"
DEFAULT_JUDGE_MODEL = "claude-opus-4-7"

JUDGE_PROMPT = """You are grading a model's response to a Tensorlake skill eval.

EVAL PROMPT:
{prompt}

EXPECTED BEHAVIOR (high-level):
{expected}

EXPECTATIONS (each must independently pass or fail; numbered 1..N):
{expectations}

MODEL RESPONSE:
---
{output}
---

For each expectation in order, decide pass/fail strictly from the response.
Reply with ONLY a JSON object of this shape (no prose, no markdown fences):

{{"results": [{{"passed": true|false, "evidence": "<short citation or 'not present'>", "reason": "<one sentence explaining why this passed or failed>"}}]}}

The "results" array MUST have exactly {n} entries, one per numbered expectation, in order.
"""


def latest_iteration() -> int:
    nums = []
    for p in WORKSPACE.glob("iteration-*"):
        suffix = p.name.split("-", 1)[1]
        if suffix.isdigit():
            nums.append(int(suffix))
    if not nums:
        sys.exit("no iterations found in evals/workspace/")
    return max(nums)


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of arbitrary judge text."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object found in judge output:\n{text[:500]}")
    return json.loads(m.group(0))


def grade_one(eval_obj: dict, output_md: str, timeout: int, judge_model: str) -> list[dict]:
    expectations = eval_obj["expectations"]
    numbered = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(expectations))
    prompt = JUDGE_PROMPT.format(
        prompt=eval_obj["prompt"],
        expected=eval_obj["expected_output"],
        expectations=numbered,
        n=len(expectations),
        output=output_md,
    )
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text", "--model", judge_model],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "SKILL_EVAL_RUNNING": "1"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"judge exit {result.returncode}: {result.stderr[:500]}")
    parsed = extract_json(result.stdout)
    results = parsed.get("results")
    if not isinstance(results, list) or len(results) != len(expectations):
        raise ValueError(
            f"judge returned {len(results) if isinstance(results, list) else 'non-list'} "
            f"items, expected {len(expectations)}"
        )
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iteration", type=int, help="iteration to grade; default latest")
    ap.add_argument("--timeout", type=int, default=600, help="per-eval judge timeout in seconds")
    ap.add_argument("--workers", type=int, default=1, help="parallel judge workers; default 1")
    ap.add_argument("--model", default=DEFAULT_JUDGE_MODEL, help=f"judge model id; default {DEFAULT_JUDGE_MODEL}")
    args = ap.parse_args()

    iteration = args.iteration or latest_iteration()
    iter_dir = WORKSPACE / f"iteration-{iteration}"
    print(f"→ grading iteration {iteration}", flush=True)

    evals_data = json.loads(EVALS_JSON.read_text())
    by_id = {e["id"]: e for e in evals_data["evals"]}

    jobs = []
    for slug_dir in sorted(iter_dir.iterdir(), key=lambda p: int(p.name.split("-")[1]) if p.name.startswith("eval-") else 0):
        if not slug_dir.is_dir() or not slug_dir.name.startswith("eval-"):
            continue
        eval_id = int(slug_dir.name.split("-")[1])
        eval_obj = by_id.get(eval_id)
        if not eval_obj:
            continue
        out_path = slug_dir / "with_skill" / "output.md"
        if not out_path.exists():
            print(f"  • eval {eval_id}: no output.md, skipping", file=sys.stderr)
            continue
        trigger_path = slug_dir / "with_skill" / "trigger.json"
        jobs.append((eval_id, eval_obj, out_path, trigger_path))

    def load_trigger(trigger_path: Path):
        if not trigger_path.exists():
            return None
        try:
            return json.loads(trigger_path.read_text())
        except json.JSONDecodeError:
            return None

    def grade_job(job):
        eval_id, eval_obj, out_path, trigger_path = job
        trigger = load_trigger(trigger_path)
        if trigger is not None and not trigger.get("skill_triggered"):
            return eval_id, eval_obj, None, trigger, None
        try:
            results = grade_one(eval_obj, out_path.read_text(), args.timeout, args.model)
        except Exception as exc:
            return eval_id, eval_obj, None, trigger, str(exc)
        return eval_id, eval_obj, results, trigger, None

    runs = []
    workers = max(1, args.workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(grade_job, j) for j in jobs]
        for fut in as_completed(futures):
            eval_id, eval_obj, results, trigger, err = fut.result()
            if err is not None:
                print(f"  ✗ eval {eval_id} ({eval_obj['name']}): judge failed: {err}", file=sys.stderr)
                continue
            triggered = bool(trigger and trigger.get("skill_triggered"))
            expectations = eval_obj["expectations"]
            if results is None:
                total = len(expectations)
                passed = 0
                expectation_records = [
                    {
                        "text": expectations[i],
                        "passed": False,
                        "evidence": "not present",
                        "reason": "skill not triggered; grading skipped",
                    }
                    for i in range(total)
                ]
                trigger_label = "no-skill (skipped)"
            else:
                passed = sum(1 for r in results if r.get("passed"))
                total = len(results)
                expectation_records = [
                    {
                        "text": expectations[i],
                        "passed": bool(r.get("passed")),
                        "evidence": r.get("evidence", ""),
                        "reason": r.get("reason", ""),
                    }
                    for i, r in enumerate(results)
                ]
                trigger_label = "skill" if triggered else "trigger?"
            print(
                f"  ✓ eval {eval_id} ({eval_obj['name']}): {passed}/{total} [{trigger_label}]",
                flush=True,
            )
            runs.append({
                "eval_id": eval_id,
                "eval_name": eval_obj["name"],
                "configuration": "with_skill",
                "skill_triggered": triggered if trigger is not None else None,
                "skill_invocations": (trigger or {}).get("skill_invocations", []),
                "result": {
                    "pass_rate": round(passed / total, 2) if total else 0,
                    "passed": passed,
                    "total": total,
                },
                "expectations": expectation_records,
            })
    runs.sort(key=lambda r: r["eval_id"])

    total_passed = sum(r["result"]["passed"] for r in runs)
    total = sum(r["result"]["total"] for r in runs)
    triggered_count = sum(1 for r in runs if r.get("skill_triggered") is True)
    triggered_total = sum(1 for r in runs if r.get("skill_triggered") is not None)
    summary = {
        "total_passed": total_passed,
        "total": total,
        "pass_rate": round(total_passed / total, 2) if total else 0,
        "skill_triggered": triggered_count,
        "skill_trigger_total": triggered_total,
        "skill_trigger_rate": (
            round(triggered_count / triggered_total, 2) if triggered_total else None
        ),
    }

    meta_path = iter_dir / "run_meta.json"
    executor_model = "default (claude -p)"
    if meta_path.exists():
        try:
            executor_model = json.loads(meta_path.read_text()).get("executor_model", executor_model)
        except json.JSONDecodeError:
            pass

    benchmark = {
        "metadata": {
            "skill_name": evals_data["skill_name"],
            "skill_path": str(REPO),
            "executor_model": executor_model,
            "analyzer_model": args.model,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "iteration": iteration,
            "evals_run": [r["eval_id"] for r in runs],
            "configurations": ["with_skill"],
            "grading_method": "automated LLM judge against expectations array in evals.json",
        },
        "runs": runs,
        "run_summary": {"with_skill": summary},
    }
    out = iter_dir / "benchmark.json"
    out.write_text(json.dumps(benchmark, indent=2))
    print(f"✓ wrote {out}  —  {total_passed}/{total} passed", flush=True)


if __name__ == "__main__":
    main()
