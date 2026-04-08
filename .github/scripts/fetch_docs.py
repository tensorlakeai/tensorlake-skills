#!/usr/bin/env python3
"""Fetch live Tensorlake doc pages listed in sources.yaml.

Saves each page as a text file under <output_dir>/<ref_file>/<slug>.txt
so check_drift.py can compare them against the bundled references.
"""

import argparse
import hashlib
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import yaml  # PyYAML — available in GitHub Actions via pip install pyyaml


def slug(url: str) -> str:
    """Turn a URL into a safe filename."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", url.split("docs.tensorlake.ai/")[-1]).strip("_")


def fetch(url: str, retries: int = 3, backoff: float = 2.0) -> str | None:
    """Fetch a URL with retries. Returns body text or None on failure."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tensorlake-skills-drift-check/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(f"  [warn] attempt {attempt + 1}/{retries} failed for {url}: {exc}")
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=str(Path(__file__).parent / "sources.yaml"),
        help="Path to sources.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).parent / "fetched"),
        help="Directory to write fetched pages into",
    )
    parser.add_argument(
        "--llms-txt",
        action="store_true",
        help="Also fetch llms.txt and save it for new-page detection",
    )
    args = parser.parse_args()

    with open(args.sources) as f:
        sources = yaml.safe_load(f)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    previous_manifest_path = out / "manifest.yaml"
    previous_manifest = {}
    if previous_manifest_path.exists():
        previous_manifest = yaml.safe_load(previous_manifest_path.read_text(encoding="utf-8")) or {}
    previous_checksums: dict[str, str] = previous_manifest.get("checksums", {}) or {}

    total = 0
    failed = 0
    retained = 0
    checksums: dict[str, str] = {}
    llms_txt_fetched = False

    for ref_file, meta in sources.items():
        urls = meta.get("sources", [])
        if not urls:
            continue

        ref_dir = out / ref_file.replace(".md", "")
        ref_dir.mkdir(parents=True, exist_ok=True)

        for url in urls:
            total += 1
            name = slug(url)
            print(f"Fetching {url} ...")
            body = fetch(url)
            if body is None:
                if dest.exists() and url in previous_checksums:
                    checksums[url] = previous_checksums[url]
                    retained += 1
                    print(f"  [retain] Keeping previously fetched copy for {url}")
                else:
                    failed += 1
                    print(f"  [FAIL] Could not fetch {url}")
                continue

            dest = ref_dir / f"{name}.txt"
            dest.write_text(body, encoding="utf-8")
            checksums[url] = hashlib.sha256(body.encode()).hexdigest()[:16]
            print(f"  -> {dest} ({len(body)} chars)")

    # Optionally fetch the llms.txt index for new-page detection.
    if args.llms_txt:
        print("Fetching llms.txt ...")
        body = fetch("https://docs.tensorlake.ai/llms.txt")
        if body:
            dest = out / "llms.txt"
            dest.write_text(body, encoding="utf-8")
            checksums["https://docs.tensorlake.ai/llms.txt"] = hashlib.sha256(body.encode()).hexdigest()[:16]
            llms_txt_fetched = True
            print(f"  -> {dest} ({len(body)} chars)")
        elif (out / "llms.txt").exists() and "https://docs.tensorlake.ai/llms.txt" in previous_checksums:
            checksums["https://docs.tensorlake.ai/llms.txt"] = previous_checksums["https://docs.tensorlake.ai/llms.txt"]
            llms_txt_fetched = True
            retained += 1
            print("  [retain] Keeping previously fetched copy for llms.txt")

    # Write a manifest so check_drift.py knows what was fetched.
    manifest = out / "manifest.yaml"
    manifest.write_text(
        yaml.dump({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "total": total, "failed": failed, "retained": retained,
                    "checksums": checksums, "llms_txt_fetched": llms_txt_fetched},
                   default_flow_style=False),
        encoding="utf-8",
    )

    print(f"\nDone: {total - failed}/{total} pages available, {retained} retained, {failed} failures.")
    return 1 if failed > 0 else 0  # Fail on any fetch failure to avoid false drift reports


if __name__ == "__main__":
    sys.exit(main())
