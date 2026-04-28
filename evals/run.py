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


SKILL_NAME = "tensorlake"
FILE_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
FILES_MAX_BYTES = 200_000
FILES_TOTAL_MAX_BYTES = 1_000_000


def iter_assistant_tool_uses(stream_lines):
    """Yield (name, input) for every assistant tool_use block in the stream."""
    for line in stream_lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        for block in obj.get("message", {}).get("content", []) or []:
            if block.get("type") != "tool_use":
                continue
            yield block.get("name"), block.get("input") or {}


def detect_skill_trigger(stream_lines: list[str]) -> dict:
    """Scan stream-json output for a Skill tool_use that loads the tensorlake skill.

    Returns {"skill_triggered": bool, "skill_invocations": [...]}.
    """
    invocations = [
        inp.get("skill", "")
        for name, inp in iter_assistant_tool_uses(stream_lines)
        if name == "Skill"
    ]
    triggered = any(SKILL_NAME in s.lower() for s in invocations)
    return {"skill_triggered": triggered, "skill_invocations": invocations}


def extract_final_text(stream_lines: list[str]) -> str:
    """Pull the final result text from a stream-json transcript."""
    for line in reversed(stream_lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result" and obj.get("subtype") == "success":
            return obj.get("result", "") or ""
    return ""


def collect_written_files(stream_lines: list[str]) -> dict[str, str]:
    """Snapshot files the assistant wrote/edited during the run.

    Scans the stream for Write/Edit-family tool_uses, collects the unique paths,
    then reads the final on-disk state of each. Used by the grader so the judge
    can score artifacts the model put in a file rather than in output.md.
    """
    paths: list[str] = []
    seen: set[str] = set()
    for name, inp in iter_assistant_tool_uses(stream_lines):
        if name not in FILE_WRITE_TOOLS:
            continue
        fp = inp.get("file_path") or inp.get("notebook_path")
        if not fp or fp in seen:
            continue
        seen.add(fp)
        paths.append(fp)

    out: dict[str, str] = {}
    total = 0
    for p in paths:
        path = Path(p)
        try:
            size = path.stat().st_size
        except OSError as exc:
            out[p] = f"<unreadable: {exc.__class__.__name__}>"
            continue
        try:
            if size > FILES_MAX_BYTES:
                content = path.read_text()[:FILES_MAX_BYTES] + "\n... [truncated]"
            else:
                content = path.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            out[p] = f"<unreadable: {exc.__class__.__name__}>"
            continue
        total += len(content)
        if total > FILES_TOTAL_MAX_BYTES:
            out[p] = "<omitted: total snapshot size exceeded>"
            break
        out[p] = content
    return out


def run_eval(eval_obj: dict, out_dir: Path, timeout: int, model: str | None) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "claude", "-p", eval_obj["prompt"],
        "--output-format", "stream-json", "--verbose",
        "--dangerously-skip-permissions",
    ]
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
    stream_lines = result.stdout.splitlines()
    (out_dir / "stream.jsonl").write_text(result.stdout)
    (out_dir / "output.md").write_text(extract_final_text(stream_lines))
    (out_dir / "trigger.json").write_text(json.dumps(detect_skill_trigger(stream_lines), indent=2))
    (out_dir / "files.json").write_text(json.dumps(collect_written_files(stream_lines), indent=2))
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
    iter_dir.mkdir(parents=True, exist_ok=True)
    model_label = args.model or "harness default"
    (iter_dir / "run_meta.json").write_text(json.dumps({"executor_model": model_label}))
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
