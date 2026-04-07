#!/usr/bin/env python3
"""Compare fetched live docs against bundled reference files.

Produces a Markdown drift report covering:
  1. API symbols (classes, functions, parameters) present in live docs but missing from the reference.
  2. API symbols in the reference that no longer appear in live docs (possibly removed/renamed).
  3. New doc pages in llms.txt not tracked in sources.yaml.

Exit code 0 = no significant drift, 1 = drift detected.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pattern sets — we extract in two tiers:
#   1. HIGH-SIGNAL: Tensorlake SDK imports, classes, and known object methods.
#   2. MEDIUM-SIGNAL: General Python API patterns (parameters, decorators, CLI).
# Only high-signal and medium-signal matches that look SDK-relevant are kept.
# ---------------------------------------------------------------------------

# Tier 1: Tensorlake-specific patterns
TIER1_PATTERNS = [
    # Imports from tensorlake.*
    re.compile(r"from\s+(tensorlake[\w.]*)\s+import\s+(.+)"),
    # SDK class names (CamelCase with known suffixes)
    re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:Client|Info|Options|Config|Strategy|Provider|Status|Error|Mode|Type|Format|Result|Response|Session|Pool|Context|Retries|Filter))\b"),
    # Known SDK object method calls: client.method(, sandbox.method(, doc_ai.method(
    re.compile(r"\b(?:client|sandbox|doc_ai|pool|proc|session|request|ctx|future)\s*\.\s*(\w+)\s*\("),
    # Decorator names from tensorlake
    re.compile(r"@(application|function|cls)\s*\("),
    # CLI: tl sbx <subcommand>, tensorlake <subcommand>
    re.compile(r"tl\s+sbx\s+(\w+)"),
    re.compile(r"tensorlake\s+(\w+)"),
]

# Tier 2: General API patterns (parameters in signatures)
TIER2_PATTERNS = [
    # Keyword arguments in function/class signatures: word: Type or word=default
    # Only inside code blocks (heuristic: lines starting with spaces or containing def/class)
    re.compile(r"\b(\w+)\s*:\s*(?:[A-Z][a-zA-Z]+)"),
    re.compile(r"\b(\w+)\s*=\s*(?:[A-Z\"\'\d\[{(]|True|False|None)"),
]

# Noise: generic tokens that appear everywhere and carry no API signal.
NOISE = frozenset({
    # Language keywords & builtins
    "the", "and", "for", "with", "that", "this", "from", "your", "you",
    "are", "not", "can", "will", "use", "set", "get", "run", "new", "has",
    "all", "any", "str", "int", "bool", "float", "list", "dict", "none",
    "true", "false", "self", "return", "import", "print", "def", "class",
    "async", "await", "type", "name", "value", "data", "file", "path",
    "result", "error", "status", "page", "content", "text", "index",
    "key", "url", "json", "http", "https", "api", "doc", "docs",
    "example", "code", "python", "bash", "pip", "install", "output",
    "input", "model", "message", "response", "request", "query",
    "string", "number", "object", "array", "item", "items", "total",
    "count", "size", "time", "task", "step", "info", "note", "tip",
    "image", "base", "default", "config", "option", "args", "kwargs",
    # Third-party names that leak from tutorial examples
    "openai", "anthropic", "langchain", "crewai", "llamaindex",
    "pydantic", "basemodel", "field", "fastapi", "flask", "django",
    "pandas", "numpy", "torch", "chromadb", "qdrant", "redis",
    "duckdb", "databricks", "spark", "mongodb",
    # Common example variable names
    "foo", "bar", "baz", "tmp", "temp", "test", "demo", "main",
    "agent", "tool", "prompt", "role", "user", "system", "assistant",
    "source", "target", "dest", "src", "dst", "env", "cmd",
})

# Third-party class names to ignore — these appear in integration examples.
THIRD_PARTY_CLASSES = frozenset({
    "OpenAI", "Anthropic", "ChatOpenAI", "BaseModel", "Field",
    "Agent", "Task", "Crew", "Runner", "WebSearchTool",
    "VectorStoreIndex", "TextNode", "Document", "SentenceTransformer",
    "QdrantClient", "TavilySearchResults", "Logger",
    "ClaudeAgentOptions", "ApprovalDeniedError", "ValidationError",
    "ZeroDivisionError", "ModuleNotFoundError", "PersistentClient",
    "CitedResponse", "PersonSearchResult", "ProcessingResult",
})

# Regex for example variable names: things like agent_a, llm_image, research_image.
# These are tutorial-specific and not part of the SDK API surface.
_EXAMPLE_VAR_RE = re.compile(
    r"^(?:"
    r"agent_[a-z]|"                     # agent_a, agent_b
    r"\w+_image|"                        # llm_image, research_image
    r"\w+_future|"                       # numbers_future
    r"\w+_name(?:_future)?|"             # capitalized_name
    r"[a-z]+_value|"                     # input_value, query_value
    r"OPENAI_API_KEY|AWS_ACCESS_KEY|TENSORLAKE_API_KEY|ANTHROPIC_API_KEY"
    r")$"
)


def extract_symbols(text: str) -> set[str]:
    """Extract API-relevant symbols from a block of text."""
    symbols: set[str] = set()

    # Tier 1: high-signal Tensorlake patterns
    for pat in TIER1_PATTERNS:
        for match in pat.finditer(text):
            # Import lines may have multiple names
            for group_idx in range(1, match.lastindex + 1 if match.lastindex else 2):
                raw = match.group(group_idx)
                if raw is None:
                    continue
                for token in re.split(r"[,\s]+", raw):
                    token = token.strip("()`\"'")
                    if (len(token) >= 3
                            and token.lower() not in NOISE
                            and token not in THIRD_PARTY_CLASSES
                            and not _EXAMPLE_VAR_RE.match(token)):
                        symbols.add(token)

    # Tier 2: parameter names — only keep if they look like SDK params
    # (longer names, snake_case, not single common words)
    for pat in TIER2_PATTERNS:
        for match in pat.finditer(text):
            token = match.group(1).strip("()`\"'")
            if (len(token) >= 4
                    and "_" in token
                    and token.lower() not in NOISE
                    and not token.startswith("_")
                    and not _EXAMPLE_VAR_RE.match(token)):
                symbols.add(token)

    return symbols


# ---------------------------------------------------------------------------
# Page-index diffing (llms.txt)
# ---------------------------------------------------------------------------

def extract_doc_urls(llms_text: str) -> set[str]:
    """Pull all doc URLs from llms.txt."""
    return set(re.findall(r"https://docs\.tensorlake\.ai/[\w./-]+\.md", llms_text))


def tracked_urls(sources: dict) -> set[str]:
    """All URLs already listed in sources.yaml."""
    urls: set[str] = set()
    for meta in sources.values():
        for u in meta.get("sources", []):
            urls.add(u)
    return urls


# ---------------------------------------------------------------------------
# Auto-classify new pages into reference file buckets
# ---------------------------------------------------------------------------

# URL path prefix → suggested reference file (or "NEW: <name>" for new files).
_ROUTE_RULES: list[tuple[str, str]] = [
    ("/sandboxes/", "sandbox_sdk.md"),
    ("/api-reference/v2/sandboxes/", "sandbox_sdk.md"),
    ("/api-reference/v2/processes/", "sandbox_sdk.md"),
    ("/api-reference/v2/pty/", "sandbox_sdk.md"),
    ("/api-reference/v2/sandbox-files/", "sandbox_sdk.md"),
    ("/applications/", "applications_sdk.md"),
    ("/document-ingestion/", "documentai_sdk.md"),
    ("/api-reference/v2/parse/", "documentai_sdk.md"),
    ("/api-reference/v2/datasets/", "documentai_sdk.md"),
    ("/api-reference/v2/files/", "documentai_sdk.md"),
    ("/api-reference/v2/edit", "documentai_sdk.md"),
    ("/integrations/", "integrations.md"),
    ("/platform/", "platform.md"),
    ("/examples/", "_skip"),       # tutorials — not SDK reference
    ("/faqs/", "_skip"),
    ("/opensource/", "_skip"),
    ("/use-cases/", "_skip"),
]


def classify_new_pages(urls: list[str]) -> dict[str, list[str]]:
    """Bucket new URLs by suggested reference file.

    Returns {ref_file: [urls]} including "_skip" for pages we suggest ignoring
    and "_unclassified" for anything that doesn't match a rule.
    """
    buckets: dict[str, list[str]] = {}
    for url in urls:
        matched = False
        for prefix, target in _ROUTE_RULES:
            if prefix in url:
                buckets.setdefault(target, []).append(url)
                matched = True
                break
        if not matched:
            buckets.setdefault("_unclassified", []).append(url)
    return buckets


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(
    ref_diffs: dict[str, dict],
    new_pages: list[str],
) -> str:
    """Render the drift report as Markdown."""
    lines: list[str] = []
    lines.append("# Tensorlake Skill Drift Report\n")

    has_drift = False

    # Per-reference-file symbol drift
    for ref_file, diff in sorted(ref_diffs.items()):
        added = diff.get("in_docs_not_ref", set())
        removed = diff.get("in_ref_not_docs", set())
        if not added and not removed:
            continue

        has_drift = True
        lines.append(f"## `references/{ref_file}`\n")

        if added:
            lines.append(f"### New in live docs ({len(added)} symbols)\n")
            lines.append("These symbols appear in the upstream docs but are **missing** from the bundled reference.\n")
            for s in sorted(added):
                lines.append(f"- `{s}`")
            lines.append("")

        if removed:
            lines.append(f"### Possibly removed ({len(removed)} symbols)\n")
            lines.append("These symbols are in the bundled reference but were **not found** in the fetched docs. They may have been renamed or removed.\n")
            for s in sorted(removed):
                lines.append(f"- `{s}`")
            lines.append("")

    # New pages — classified into suggested reference file buckets
    if new_pages:
        has_drift = True
        buckets = classify_new_pages(new_pages)

        lines.append("## Suggested `sources.yaml` updates\n")
        lines.append("New doc pages found in `llms.txt`. Add these URLs to the indicated file in `sources.yaml`.\n")

        # Actionable buckets: existing or new reference files
        for target in sorted(buckets):
            if target.startswith("_"):
                continue
            urls = buckets[target]
            if target.startswith("NEW:"):
                label = f"**{target}** (create new reference file)"
            else:
                label = f"`{target}`"
            lines.append(f"### Add to {label}\n")
            lines.append("```yaml")
            for url in sorted(urls):
                lines.append(f"    - {url}")
            lines.append("```\n")

        # Skipped pages (examples, FAQs, etc.)
        skipped = buckets.get("_skip", [])
        if skipped:
            lines.append(f"### Skipped ({len(skipped)} pages — examples, FAQs, open-source)\n")
            lines.append("These are tutorials/examples/FAQs that typically don't belong in SDK reference files.\n")
            lines.append("<details><summary>Show skipped pages</summary>\n")
            for url in sorted(skipped):
                lines.append(f"- {url}")
            lines.append("\n</details>\n")

        # Unclassified
        unclassified = buckets.get("_unclassified", [])
        if unclassified:
            lines.append(f"### Unclassified ({len(unclassified)} pages)\n")
            lines.append("Could not auto-assign these. Review manually.\n")
            for url in sorted(unclassified):
                lines.append(f"- {url}")
            lines.append("")

    if not has_drift:
        lines.append("No significant drift detected. Bundled references look up-to-date.\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=str(Path(__file__).parent / "sources.yaml"),
        help="Path to sources.yaml",
    )
    parser.add_argument(
        "--fetched-dir",
        default=str(Path(__file__).parent / "fetched"),
        help="Directory produced by fetch_docs.py",
    )
    parser.add_argument(
        "--references-dir",
        default=str(Path(__file__).parents[2] / "references"),
        help="Path to the bundled references/ directory",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "drift-report.md"),
        help="Where to write the drift report",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Minimum new symbols to count as meaningful drift (default: 5)",
    )
    args = parser.parse_args()

    with open(args.sources) as f:
        sources = yaml.safe_load(f)

    fetched = Path(args.fetched_dir)
    refs = Path(args.references_dir)

    ref_diffs: dict[str, dict] = {}

    for ref_file in sources:
        if ref_file.startswith("_"):
            continue  # skip _uncovered

        ref_path = refs / ref_file
        if not ref_path.exists():
            print(f"[warn] reference file {ref_path} not found, skipping")
            continue

        ref_text = ref_path.read_text(encoding="utf-8")
        ref_symbols = extract_symbols(ref_text)

        # Combine all fetched pages for this reference.
        fetched_subdir = fetched / ref_file.replace(".md", "")
        if not fetched_subdir.exists():
            print(f"[warn] fetched dir {fetched_subdir} not found, skipping")
            continue

        docs_text = ""
        for txt_file in sorted(fetched_subdir.glob("*.txt")):
            docs_text += "\n" + txt_file.read_text(encoding="utf-8")

        docs_symbols = extract_symbols(docs_text)

        in_docs_not_ref = docs_symbols - ref_symbols
        in_ref_not_docs = ref_symbols - docs_symbols

        ref_diffs[ref_file] = {
            "in_docs_not_ref": in_docs_not_ref,
            "in_ref_not_docs": in_ref_not_docs,
        }

        print(f"{ref_file}: +{len(in_docs_not_ref)} new, -{len(in_ref_not_docs)} missing")

    # Check for new pages via llms.txt
    new_pages: list[str] = []
    llms_path = fetched / "llms.txt"
    if llms_path.exists():
        live_urls = extract_doc_urls(llms_path.read_text(encoding="utf-8"))
        known_urls = tracked_urls(sources)
        new_pages = sorted(live_urls - known_urls)
        if new_pages:
            print(f"\n{len(new_pages)} doc pages not tracked in sources.yaml")

    report = build_report(ref_diffs, new_pages)
    out_path = Path(args.output)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nDrift report written to {out_path}")

    # Determine exit code: drift if any ref has enough new or removed symbols, or new pages exist.
    significant = any(
        len(d.get("in_docs_not_ref", set())) >= args.threshold
        or len(d.get("in_ref_not_docs", set())) >= args.threshold
        for d in ref_diffs.values()
    ) or len(new_pages) > 0
    return 1 if significant else 0


if __name__ == "__main__":
    sys.exit(main())
