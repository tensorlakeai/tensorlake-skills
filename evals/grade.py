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
JUDGE_MODEL = "claude-opus-4-7"

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

{{"results": [{{"passed": true|false, "evidence": "<short citation or 'not present'>"}}]}}

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


def grade_one(eval_obj: dict, output_md: str, timeout: int) -> list[dict]:
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
        ["claude", "-p", prompt, "--output-format", "text", "--model", JUDGE_MODEL],
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
        jobs.append((eval_id, eval_obj, out_path))

    def grade_job(job):
        eval_id, eval_obj, out_path = job
        try:
            results = grade_one(eval_obj, out_path.read_text(), args.timeout)
        except Exception as exc:
            return eval_id, eval_obj, None, str(exc)
        return eval_id, eval_obj, results, None

    runs = []
    workers = max(1, args.workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(grade_job, j) for j in jobs]
        for fut in as_completed(futures):
            eval_id, eval_obj, results, err = fut.result()
            if err is not None:
                print(f"  ✗ eval {eval_id} ({eval_obj['name']}): judge failed: {err}", file=sys.stderr)
                continue
            passed = sum(1 for r in results if r.get("passed"))
            total = len(results)
            print(f"  ✓ eval {eval_id} ({eval_obj['name']}): {passed}/{total}", flush=True)
            runs.append({
                "eval_id": eval_id,
                "eval_name": eval_obj["name"],
                "configuration": "with_skill",
                "result": {
                    "pass_rate": round(passed / total, 2) if total else 0,
                    "passed": passed,
                    "total": total,
                },
                "expectations": [
                    {
                        "text": eval_obj["expectations"][i],
                        "passed": bool(r.get("passed")),
                        "evidence": r.get("evidence", ""),
                    }
                    for i, r in enumerate(results)
                ],
            })
    runs.sort(key=lambda r: r["eval_id"])

    total_passed = sum(r["result"]["passed"] for r in runs)
    total = sum(r["result"]["total"] for r in runs)
    summary = {
        "total_passed": total_passed,
        "total": total,
        "pass_rate": round(total_passed / total, 2) if total else 0,
    }

    benchmark = {
        "metadata": {
            "skill_name": evals_data["skill_name"],
            "skill_path": str(REPO),
            "executor_model": "default (claude -p)",
            "analyzer_model": JUDGE_MODEL,
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
