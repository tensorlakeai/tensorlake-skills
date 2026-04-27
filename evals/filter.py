#!/usr/bin/env python3
"""Pick eval IDs to run based on a list of changed files.

Usage:
    python evals/filter.py path1 path2 ...

Prints a comma-separated list of eval IDs to stdout (e.g. "1,3,7"), or
nothing at all if no evals need to run. Designed to feed `run.py --evals`.

Rule: for each changed `references/<name>.md`, run every eval whose
`references[]` entry starts with `<name>.md` (the bit before `#`).
Anything else — SKILL.md, AGENTS.md, evals.json, eval scripts, version
bumps, docs — is ignored. Full runs are triggered manually via the
workflow's `workflow_dispatch` entry point.

Today every eval references a `sandbox_*.md` file, so a PR that only
touches `applications_sdk.md` / `documentai_sdk.md` / `integrations.md`
/ `platform.md` / `troubleshooting.md` produces an empty result and the
CI workflow skips the eval job.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_JSON = REPO / "evals" / "evals.json"


def main() -> None:
    changed = {arg.strip() for arg in sys.argv[1:] if arg.strip()}
    evals = json.loads(EVALS_JSON.read_text())["evals"]

    changed_refs = {
        Path(p).name
        for p in changed
        if p.startswith("references/") and p.endswith(".md")
    }
    if not changed_refs:
        return

    matching = [
        e["id"]
        for e in evals
        if {ref.split("#", 1)[0] for ref in e["references"]} & changed_refs
    ]
    if matching:
        print(",".join(str(i) for i in matching))


if __name__ == "__main__":
    main()
