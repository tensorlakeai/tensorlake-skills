#!/usr/bin/env python3
"""Run the with_skill config of the eval set against the current skill.

For each eval in evals.json, spawns `claude -p` headlessly from the repo root
(so the tensorlake skill is auto-discovered) and writes the response to
evals/workspace/iteration-N/eval-X-name/with_skill/output.md.
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_JSON = REPO / "evals" / "evals.json"
WORKSPACE = REPO / "evals" / "workspace"


def next_iteration() -> int:
    existing = []
    for p in WORKSPACE.glob("iteration-*"):
        suffix = p.name.split("-", 1)[1]
        if suffix.isdigit():
            existing.append(int(suffix))
    return max(existing, default=0) + 1


def run_eval(eval_obj: dict, out_dir: Path, timeout: int, model: str | None) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", eval_obj["prompt"], "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    result = subprocess.run(
        cmd,
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "SKILL_EVAL_RUNNING": "1"},
    )
    (out_dir / "output.md").write_text(result.stdout)
    if result.returncode != 0:
        (out_dir / "stderr.log").write_text(result.stderr)
        return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evals", help="comma-separated eval ids; default all")
    ap.add_argument("--iteration", type=int, help="iteration number; default next free")
    ap.add_argument("--timeout", type=int, default=600, help="per-eval timeout in seconds")
    ap.add_argument("--model", help="model id to pass to `claude -p --model`; default uses harness default")
    ap.add_argument("--workers", type=int, default=1, help="parallel worker count; default 1 (sequential)")
    args = ap.parse_args()

    evals = json.loads(EVALS_JSON.read_text())["evals"]
    if args.evals:
        wanted = {int(x) for x in args.evals.split(",")}
        evals = [e for e in evals if e["id"] in wanted]

    iteration = args.iteration or next_iteration()
    iter_dir = WORKSPACE / f"iteration-{iteration}"
    model_label = args.model or "harness default"
    print(f"→ iteration {iteration}: {len(evals)} evals, with_skill, model={model_label}, workers={args.workers}", flush=True)

    def submit(e):
        slug = f"eval-{e['id']}-{e['name']}"
        out = iter_dir / slug / "with_skill"
        try:
            ok = run_eval(e, out, args.timeout, args.model)
        except subprocess.TimeoutExpired:
            return slug, out, "timeout"
        return slug, out, "ok" if ok else "fail"

    failures = 0
    workers = max(1, args.workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(submit, e): e for e in evals}
        for fut in as_completed(futures):
            slug, out, status = fut.result()
            if status == "ok":
                print(f"  ✓ {slug}", flush=True)
            elif status == "timeout":
                print(f"  ✗ {slug}: timeout after {args.timeout}s", flush=True)
                failures += 1
            else:
                print(f"  ✗ {slug}: non-zero exit; see {out}/stderr.log", flush=True)
                failures += 1

    print(f"✓ outputs in {iter_dir} ({len(evals) - failures}/{len(evals)} ok)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
