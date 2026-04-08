#!/usr/bin/env python3
"""Compare fetched live docs against bundled reference files.

Reliability improvements:
  1. Separate evidence into confidence tiers.
  2. Normalize explicit aliases across Python/TypeScript and snake/camel names.
  3. Apply per-reference-file extraction rules.
  4. Support allowlists/denylists for known noisy patterns.
  5. Corroborate symbols with structured local sources when present.
  6. Validate fetched-doc freshness/completeness before reporting drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


HIGH_CONFIDENCE = "high"
MEDIUM_CONFIDENCE = "medium"
LOW_CONFIDENCE = "low"

IMPORTS = "imports"
METHODS = "methods"
DECORATORS = "decorators"
CLI = "cli"
OPTIONS = "options"
JSON_FIELDS = "json_fields"
PROSE = "prose"

CONFIDENCE_ORDER = (HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE)

HIGH_SIGNAL_KINDS = frozenset({IMPORTS, METHODS, DECORATORS, CLI})
MEDIUM_SIGNAL_KINDS = frozenset({OPTIONS, JSON_FIELDS})
LOW_SIGNAL_KINDS = frozenset({PROSE})

PY_IMPORT_RE = re.compile(r"from\s+(tensorlake[\w.]*)\s+import\s+(.+)")
TS_IMPORT_RE = re.compile(
    r'import\s+(?:type\s+)?\{([^}]+)\}\s+from\s+[\'"]((?:@tensorlake/[\w./-]+)|tensorlake(?:/[\w./-]+)*)[\'"]'
)
METHOD_CALL_RE = re.compile(
    r"\b(?:client|sandbox|doc_ai|document_ai|pool|proc|session|request|ctx|future|dataset|parser|app)\s*\.\s*(\w+)\s*\("
)
DECORATOR_RE = re.compile(r"@(application|function|cls)\s*\(")
TL_SUBCOMMAND_RE = re.compile(r"\btl\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){0,2})")
TENSORLAKE_SUBCOMMAND_RE = re.compile(r"\btensorlake\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){0,2})")
OPTION_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:[A-Z\"'\d\[{(]|True|False|None)")
TS_OPTION_RE = re.compile(r"\b([a-z][a-zA-Z0-9]+)\s*:\s*(?:[A-Z\"'\d\[{(]|true|false|null)")
JSON_FIELD_RE = re.compile(r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']\s*:')
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
CAMEL_TOKEN_RE = re.compile(r"\b([a-z]+(?:[A-Z][a-z0-9]+)+)\b")
SNAKE_TOKEN_RE = re.compile(r"\b([a-z]+(?:_[a-z0-9]+)+)\b")
DOC_URL_RE = re.compile(r"https://docs\.tensorlake\.ai/[\w./-]+\.md")

NOISE = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "your",
        "you",
        "are",
        "not",
        "can",
        "will",
        "use",
        "set",
        "get",
        "run",
        "new",
        "has",
        "all",
        "any",
        "str",
        "int",
        "bool",
        "float",
        "list",
        "dict",
        "none",
        "true",
        "false",
        "self",
        "return",
        "import",
        "print",
        "def",
        "class",
        "async",
        "await",
        "type",
        "name",
        "value",
        "data",
        "file",
        "path",
        "result",
        "error",
        "status",
        "page",
        "content",
        "text",
        "index",
        "key",
        "url",
        "json",
        "http",
        "https",
        "api",
        "doc",
        "docs",
        "example",
        "code",
        "python",
        "bash",
        "pip",
        "install",
        "output",
        "input",
        "model",
        "message",
        "response",
        "request",
        "query",
        "string",
        "number",
        "object",
        "array",
        "item",
        "items",
        "count",
        "size",
        "time",
        "task",
        "step",
        "info",
        "note",
        "tip",
        "tensorlake",
        "image",
        "base",
        "default",
        "config",
        "option",
        "args",
        "kwargs",
        "sdk",
        "cli",
        "foo",
        "bar",
        "baz",
        "tmp",
        "temp",
        "test",
        "demo",
        "main",
        "agent",
        "tool",
        "prompt",
        "role",
        "user",
        "system",
        "assistant",
        "source",
        "target",
        "dest",
        "src",
        "dst",
        "env",
        "cmd",
        "openai",
        "anthropic",
        "langchain",
        "pydantic",
        "basemodel",
        "field",
        "chromadb",
        "qdrant",
        "databricks",
        "motherduck",
    }
)

THIRD_PARTY_CLASSES = frozenset(
    {
        "OpenAI",
        "Anthropic",
        "ChatOpenAI",
        "BaseModel",
        "Field",
        "QdrantClient",
        "PersistentClient",
        "ValidationError",
    }
)

THIRD_PARTY_PARAMS = frozenset(
    {
        "temperature",
        "top_p",
        "top_k",
        "max_tokens",
        "max_results",
        "response_format",
        "random_state",
        "exist_ok",
        "stack_info",
        "stacklevel",
        "exc_info",
        "capture_output",
    }
)

EXPLICIT_ALIASES = {
    "runLocalApplication": "run_local_application",
    "runRemoteApplication": "run_remote_application",
    "baseImage": "base_image",
    "filePath": "file_path",
    "StdinMode": "SandboxProcessStdinMode",
    "killProcess": "kill_process",
    "sandboxId": "sandbox_id",
    "requestId": "request_id",
    "scheduleId": "schedule_id",
    "allocationId": "allocation_id",
    "nextToken": "next_token",
    "createdAt": "created_at",
    "lastFiredAtMs": "last_fired_at_ms",
    "nextFireTimeMs": "next_fire_time_ms",
    "logAttributes": "log_attributes",
    "functionExecutor": "function_executor",
    "functionRunId": "function_run_id",
    "inputBase64": "input_base64",
    "documentAI": "document_ai",
    "docAI": "document_ai",
    "DocumentAI": "document_ai",
    "doc_ai": "document_ai",
    "tensorlake.documentai": "tensorlake.document_ai",
    "tensorlake.doc_ai": "tensorlake.document_ai",
}

EXAMPLE_TOKEN_RE = re.compile(
    r"^(?:"
    r"agent_[a-z]|"
    r"\w+_image|"
    r"\w+_future|"
    r"\w+_name(?:_future)?|"
    r"[a-z]+_value|"
    r"\w+_client|"
    r"\w+_numbers|"
    r"\w+_results|"
    r"[A-Z][A-Z0-9_]*_(?:TOOL|FUNCTION|PROMPT|RESULTS?)|"
    r"OPENAI_API_KEY|AWS_ACCESS_KEY|TENSORLAKE_API_KEY|ANTHROPIC_API_KEY"
    r")$"
)

MODULE_OWNERS = {
    "applications_sdk.md": ("tensorlake.applications",),
    "sandbox_sdk.md": ("tensorlake.sandbox",),
    "sandbox_advanced.md": ("tensorlake.sandbox",),
    "documentai_sdk.md": ("tensorlake.document_ai",),
    "integrations.md": (),
    "platform.md": (),
    "troubleshooting.md": (),
}

OBJECT_MODULES = {
    "sandbox": "tensorlake.sandbox",
    "pool": "tensorlake.sandbox",
    "proc": "tensorlake.sandbox",
    "doc_ai": "tensorlake.document_ai",
    "document_ai": "tensorlake.document_ai",
}

VERIFIED_FALSE_POSITIVES = {
    "sandbox_sdk.md": {
        "in_ref_not_docs": {"close"},
    },
}


@dataclass(frozen=True)
class RefRule:
    enabled_kinds: frozenset[str]
    owned_modules: tuple[str, ...] = ()
    deny_tokens: frozenset[str] = frozenset()
    allow_tokens: frozenset[str] = frozenset()
    min_option_occurrences: int = 2
    suppress_removals: frozenset[str] = frozenset()
    allowed_cli_prefixes: tuple[str, ...] = ()


REFERENCE_RULES = {
    "applications_sdk.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, DECORATORS, CLI, OPTIONS, JSON_FIELDS, PROSE}),
        owned_modules=MODULE_OWNERS["applications_sdk.md"],
        deny_tokens=frozenset({"done", "arg1", "arg2", "context", "current", "Sandbox"}),
        allowed_cli_prefixes=("deploy", "secrets_"),
    ),
    "sandbox_sdk.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, CLI, OPTIONS, JSON_FIELDS}),
        owned_modules=MODULE_OWNERS["sandbox_sdk.md"],
        deny_tokens=frozenset({"close", "stdout_capture", "Sandbox", "login", "secrets_set"}),
        allowed_cli_prefixes=("sbx_",),
    ),
    "sandbox_advanced.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, CLI, OPTIONS, JSON_FIELDS, PROSE}),
        owned_modules=MODULE_OWNERS["sandbox_advanced.md"],
        deny_tokens=frozenset({"analysis", "market"}),
    ),
    "documentai_sdk.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, CLI, OPTIONS, JSON_FIELDS, PROSE}),
        owned_modules=MODULE_OWNERS["documentai_sdk.md"],
        deny_tokens=frozenset({"structured_data", "text_lines"}),
    ),
    "integrations.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, CLI}),
        deny_tokens=frozenset(
            {
                "max_tokens",
                "temperature",
                "tool_choice",
                "response_format",
                "permission_mode",
                "user_id",
            }
        ),
        suppress_removals=frozenset(CONFIDENCE_ORDER),
        allowed_cli_prefixes=("sbx_", "deploy", "parse"),
    ),
    "platform.md": RefRule(
        enabled_kinds=frozenset({CLI, OPTIONS, JSON_FIELDS, PROSE}),
        min_option_occurrences=1,
        deny_tokens=frozenset({"sub", "tier", "timestamp"}),
        allowed_cli_prefixes=("login", "secrets_"),
    ),
    "troubleshooting.md": RefRule(
        enabled_kinds=frozenset({IMPORTS, METHODS, CLI, PROSE}),
        deny_tokens=frozenset({"logs", "errors", "results"}),
        allowed_cli_prefixes=("deploy", "parse", "sbx_"),
    ),
}

ROUTE_RULES = [
    ("/sandboxes/skills-in-sandboxes", "sandbox_advanced.md"),
    ("/sandboxes/ai-code-execution", "sandbox_advanced.md"),
    ("/sandboxes/data-analysis", "sandbox_advanced.md"),
    ("/sandboxes/cicd-build", "sandbox_advanced.md"),
    ("/applications/production/", "troubleshooting.md"),
    ("/document-ingestion/production/", "troubleshooting.md"),
    ("/applications/overview", "troubleshooting.md"),
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
    ("/examples/", "_skip"),
    ("/faqs/", "_skip"),
    ("/opensource/", "_skip"),
    ("/use-cases/", "_skip"),
]


def _normalize_imports(text: str) -> str:
    return re.sub(
        r"(from\s+tensorlake[\w.]*\s+import\s+)\(([^)]+)\)",
        lambda match: match.group(1) + match.group(2).replace("\n", " "),
        text,
        flags=re.DOTALL,
    )


def _to_snake_case(token: str) -> str:
    token = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", token)
    token = token.replace("-", "_")
    return token.lower()


def canonical_symbol(token: str) -> str:
    if not token:
        return token
    token = token.strip("`()\"' ")
    token = EXPLICIT_ALIASES.get(token, token)
    token = EXPLICIT_ALIASES.get(token.replace("/", "."), token.replace("/", "."))
    token = token.replace("tensorlake.documentai.", "tensorlake.document_ai.")
    token = token.replace("tensorlake.doc_ai.", "tensorlake.document_ai.")
    if token == "tensorlake.documentai":
        token = "tensorlake.document_ai"
    if token == "tensorlake.doc_ai":
        token = "tensorlake.document_ai"
    if token == "documentai":
        token = "document_ai"
    if token == "doc_ai":
        token = "document_ai"
    if token.startswith("tensorlake.") or token.startswith("@tensorlake/"):
        token = token.replace("@tensorlake/", "tensorlake.")
        token = EXPLICIT_ALIASES.get(token, token)
        return token
    if token and token[0].isupper() and "_" not in token:
        return token
    return _to_snake_case(token)


def _looks_noisy(token: str) -> bool:
    lower = token.lower()
    return (
        lower in NOISE
        or token in THIRD_PARTY_CLASSES
        or lower in THIRD_PARTY_PARAMS
        or token.startswith("_")
        or EXAMPLE_TOKEN_RE.match(token) is not None
    )


def _looks_example_symbol(token: str) -> bool:
    if _looks_noisy(token):
        return True
    example_prefixes = (
        "buyer_",
        "seller_",
        "invoice_",
        "driver_",
        "customer_",
        "order_",
        "contract_",
        "document_",
        "field_",
        "current_",
        "sample_",
        "demo_",
        "citation_",
    )
    example_suffixes = (
        "_date",
        "_name",
        "_number",
        "_address",
        "_amount",
        "_price",
        "_id",
        "_text",
        "_line",
        "_lines",
        "_section",
        "_sections",
        "_summary",
        "_message",
        "_content",
        "_schema",
        "_prompt",
    )
    return token.startswith(example_prefixes) or token.endswith(example_suffixes)


def _extract_code_blocks(text: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)


def _add_token(target: dict[str, Counter[str]], kind: str, token: str) -> None:
    canonical = canonical_symbol(token)
    if len(canonical) < 3 or _looks_noisy(canonical):
        return
    target[kind][canonical] += 1


def _extract_import_symbols(text: str, evidence: dict[str, Counter[str]]) -> None:
    normalized = _normalize_imports(text)
    for match in PY_IMPORT_RE.finditer(normalized):
        module = canonical_symbol(match.group(1))
        _add_token(evidence, IMPORTS, module)
        for token in re.split(r"[,\s]+", match.group(2)):
            token = token.strip("()`\"'")
            if token:
                _add_token(evidence, IMPORTS, token)

    for match in TS_IMPORT_RE.finditer(normalized):
        module = canonical_symbol(match.group(2))
        _add_token(evidence, IMPORTS, module)
        for token in match.group(1).split(","):
            token = token.strip()
            if token:
                token = re.sub(r"^type\s+", "", token)
                token = token.split(" as ", 1)[0].strip()
                _add_token(evidence, IMPORTS, token)


def _extract_method_symbols(text: str, evidence: dict[str, Counter[str]]) -> None:
    for match in METHOD_CALL_RE.finditer(text):
        _add_token(evidence, METHODS, match.group(1))
    for match in DECORATOR_RE.finditer(text):
        _add_token(evidence, DECORATORS, match.group(1))
    for block in _extract_code_blocks(text):
        for regex in (
            re.compile(r"\btl\s+(login|deploy|parse|secrets(?:\s+\w+)?|sbx\s+(?:new|image\s+create))"),
            re.compile(r"\btensorlake\s+(login|deploy|parse|secrets(?:\s+\w+)?|sbx\s+(?:new|image\s+create))"),
        ):
            for match in regex.finditer(block):
                _add_token(evidence, CLI, match.group(1).replace(" ", "_"))
    for span in INLINE_CODE_RE.findall(text):
        for regex in (
            re.compile(r"^tl\s+(login|deploy|parse|secrets(?:\s+\w+)?|sbx\s+(?:new|image\s+create))$"),
            re.compile(r"^tensorlake\s+(login|deploy|parse|secrets(?:\s+\w+)?|sbx\s+(?:new|image\s+create))$"),
        ):
            match = regex.match(span.strip())
            if match:
                _add_token(evidence, CLI, match.group(1).replace(" ", "_"))


def _extract_option_symbols(text: str, evidence: dict[str, Counter[str]]) -> None:
    for block in _extract_code_blocks(text):
        for match in OPTION_RE.finditer(block):
            _add_token(evidence, OPTIONS, match.group(1))
        for match in TS_OPTION_RE.finditer(block):
            _add_token(evidence, OPTIONS, match.group(1))
        for match in JSON_FIELD_RE.finditer(block):
            _add_token(evidence, JSON_FIELDS, match.group(1))


def _extract_prose_symbols(text: str, evidence: dict[str, Counter[str]]) -> None:
    for span in INLINE_CODE_RE.findall(text):
        for match in CAMEL_TOKEN_RE.finditer(span):
            _add_token(evidence, PROSE, match.group(1))
        for match in SNAKE_TOKEN_RE.finditer(span):
            _add_token(evidence, PROSE, match.group(1))
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        for match in re.finditer(r"\b([A-Z][A-Za-z0-9_]+)\b", line):
            _add_token(evidence, PROSE, match.group(1))


def extract_evidence(text: str) -> dict[str, Counter[str]]:
    evidence = {kind: Counter() for kind in (IMPORTS, METHODS, DECORATORS, CLI, OPTIONS, JSON_FIELDS, PROSE)}
    _extract_import_symbols(text, evidence)
    _extract_method_symbols(text, evidence)
    _extract_option_symbols(text, evidence)
    _extract_prose_symbols(text, evidence)
    return evidence


def _extract_foreign_symbols(text: str, owned_prefixes: tuple[str, ...]) -> set[str]:
    if not owned_prefixes:
        return set()

    foreign: set[str] = set()
    normalized = _normalize_imports(text)
    for match in PY_IMPORT_RE.finditer(normalized):
        module = canonical_symbol(match.group(1))
        if any(module == prefix or module.startswith(prefix + ".") for prefix in owned_prefixes):
            continue
        if module.startswith("tensorlake."):
            foreign.add(module)
        for token in re.split(r"[,\s]+", match.group(2)):
            token = canonical_symbol(token.strip("()`\"'"))
            if token:
                foreign.add(token)

    for obj_name, module in OBJECT_MODULES.items():
        if any(module == prefix or module.startswith(prefix + ".") for prefix in owned_prefixes):
            continue
        obj_re = re.compile(rf"\b{re.escape(obj_name)}\s*\.\s*(\w+)\s*\(")
        for match in obj_re.finditer(text):
            foreign.add(canonical_symbol(match.group(1)))

    return foreign


def load_structured_symbols(repo_root: Path) -> set[str]:
    symbols: set[str] = set()
    candidate_patterns = (
        "**/*.pyi",
        "**/*schema*.json",
        "**/*openapi*.json",
        "**/*models*.py",
        "**/*models*.ts",
        "**/*sdk*.py",
        "**/*sdk*.ts",
    )
    for pattern in candidate_patterns:
        for path in repo_root.glob(pattern):
            if path.is_dir() or ".git/" in str(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if path.suffix == ".json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                properties = data.get("properties", {}) if isinstance(data, dict) else {}
                for key in properties:
                    symbols.add(canonical_symbol(key))
                continue
            for regex in (
                re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE),
                re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b", re.MULTILINE),
                re.compile(r"^\s*export\s+(?:type|interface|class|function)\s+([A-Za-z_]\w*)\b", re.MULTILINE),
            ):
                for match in regex.finditer(text):
                    symbols.add(canonical_symbol(match.group(1)))
    return symbols


def bucket_symbols(
    evidence: dict[str, Counter[str]],
    rule: RefRule,
    structured_symbols: set[str],
    foreign_symbols: set[str],
) -> dict[str, set[str]]:
    buckets = {HIGH_CONFIDENCE: set(), MEDIUM_CONFIDENCE: set(), LOW_CONFIDENCE: set()}

    for kind, counter in evidence.items():
        if kind not in rule.enabled_kinds:
            continue
        for token, count in counter.items():
            if token in foreign_symbols or token in rule.deny_tokens:
                continue
            if kind == CLI and rule.allowed_cli_prefixes and not token.startswith(rule.allowed_cli_prefixes):
                continue
            if rule.allow_tokens and token not in rule.allow_tokens and kind == PROSE:
                continue
            if kind in HIGH_SIGNAL_KINDS:
                buckets[HIGH_CONFIDENCE].add(token)
                continue
            if kind in MEDIUM_SIGNAL_KINDS:
                looks_structured = "_" in token or token in structured_symbols or token in rule.allow_tokens
                if looks_structured and (count >= rule.min_option_occurrences or token in structured_symbols):
                    if not _looks_example_symbol(token):
                        buckets[MEDIUM_CONFIDENCE].add(token)
                        continue
                buckets[LOW_CONFIDENCE].add(token)
                continue
            if not _looks_example_symbol(token):
                buckets[LOW_CONFIDENCE].add(token)

    buckets[LOW_CONFIDENCE] -= buckets[HIGH_CONFIDENCE]
    buckets[LOW_CONFIDENCE] -= buckets[MEDIUM_CONFIDENCE]
    return buckets


def set_diff_with_aliases(left: set[str], right: set[str]) -> set[str]:
    right_canonical = {canonical_symbol(token) for token in right}
    return {token for token in left if canonical_symbol(token) not in right_canonical}


def all_bucket_symbols(buckets: dict[str, set[str]]) -> set[str]:
    merged: set[str] = set()
    for symbols in buckets.values():
        merged |= symbols
    return merged


def text_mentions_symbol(text: str, token: str) -> bool:
    variants = {
        token,
        canonical_symbol(token),
        token.replace("_", " "),
        canonical_symbol(token).replace("_", " "),
        token.replace(".", " "),
        canonical_symbol(token).replace(".", " "),
    }
    for variant in variants:
        if len(variant) < 3:
            continue
        if re.search(rf"\b{re.escape(variant)}\b", text, flags=re.IGNORECASE):
            return True
    return False


def extract_doc_urls(llms_text: str) -> set[str]:
    return set(DOC_URL_RE.findall(llms_text))


def tracked_urls(sources: dict) -> set[str]:
    urls: set[str] = set()
    for meta in sources.values():
        for url in meta.get("sources", []):
            urls.add(url)
    return urls


def classify_new_pages(urls: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for url in urls:
        target = "_unclassified"
        for prefix, candidate in ROUTE_RULES:
            if prefix in url:
                target = candidate
                break
        buckets.setdefault(target, []).append(url)
    return buckets


def validate_fetch_corpus(
    fetched_dir: Path,
    sources: dict,
    require_llms_index: bool,
    max_age_hours: int,
) -> list[str]:
    problems: list[str] = []
    manifest_path = fetched_dir / "manifest.yaml"
    if not manifest_path.exists():
        return [f"missing manifest: {manifest_path}"]

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    fetched_at = manifest.get("fetched_at")
    if not fetched_at:
        problems.append("manifest missing fetched_at")
    else:
        try:
            fetched_time = datetime.strptime(fetched_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - fetched_time
            if age > timedelta(hours=max_age_hours):
                problems.append(f"fetched docs are stale: {age} old, limit is {max_age_hours}h")
        except ValueError:
            problems.append(f"manifest has invalid fetched_at: {fetched_at}")

    if manifest.get("failed", 0):
        problems.append(f"fetch manifest reports {manifest['failed']} failed page fetches")

    checksums = manifest.get("checksums", {}) or {}
    expected_urls = tracked_urls(sources)
    missing_urls = sorted(expected_urls - set(checksums))
    if missing_urls:
        problems.append(f"manifest missing checksums for {len(missing_urls)} tracked URLs")

    for ref_file in sources:
        ref_subdir = fetched_dir / ref_file.replace(".md", "")
        if not ref_subdir.exists():
            problems.append(f"missing fetched directory for {ref_file}: {ref_subdir}")

    llms_path = fetched_dir / "llms.txt"
    if require_llms_index and not llms_path.exists():
        problems.append("llms.txt was not fetched; new-page detection is incomplete")

    return problems


def build_report(ref_diffs: dict[str, dict], new_pages: list[str], fetch_problems: list[str]) -> str:
    lines = ["# Tensorlake Skill Drift Report", ""]

    if fetch_problems:
        lines.append("## Fetch Correctness")
        lines.append("The fetched corpus is not reliable enough for a clean drift decision.")
        lines.append("")
        for problem in fetch_problems:
            lines.append(f"- {problem}")
        lines.append("")

    has_drift = bool(fetch_problems)
    for ref_file, diff in sorted(ref_diffs.items()):
        sections = []
        for confidence in CONFIDENCE_ORDER:
            added = diff.get(f"{confidence}_in_docs_not_ref", set())
            removed = diff.get(f"{confidence}_in_ref_not_docs", set())
            if not added and not removed:
                continue
            sections.append((confidence, added, removed))
        if not sections:
            continue

        has_drift = True
        lines.append(f"## `references/{ref_file}`")
        lines.append("")
        for confidence, added, removed in sections:
            if added:
                lines.append(f"### {confidence.capitalize()}-confidence additions ({len(added)})")
                for token in sorted(added):
                    lines.append(f"- `{token}`")
                lines.append("")
            if removed:
                lines.append(f"### {confidence.capitalize()}-confidence removals ({len(removed)})")
                for token in sorted(removed):
                    lines.append(f"- `{token}`")
                lines.append("")

    if new_pages:
        has_drift = True
        buckets = classify_new_pages(new_pages)
        lines.append("## Suggested `sources.yaml` updates")
        lines.append("")
        for target, urls in sorted(buckets.items()):
            if target == "_skip":
                continue
            if target == "_unclassified":
                lines.append(f"### Unclassified ({len(urls)})")
            else:
                lines.append(f"### Add to `{target}`")
            for url in sorted(urls):
                lines.append(f"- {url}")
            lines.append("")
        skipped = buckets.get("_skip", [])
        if skipped:
            lines.append(f"### Skipped ({len(skipped)})")
            for url in sorted(skipped):
                lines.append(f"- {url}")
            lines.append("")

    if not has_drift:
        lines.append("No significant drift detected. Bundled references look up-to-date.")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default=str(Path(__file__).parent / "sources.yaml"))
    parser.add_argument("--fetched-dir", default=str(Path(__file__).parent / "fetched"))
    parser.add_argument("--references-dir", default=str(Path(__file__).parents[2] / "references"))
    parser.add_argument("--output", default=str(Path(__file__).parent / "drift-report.md"))
    parser.add_argument("--threshold", type=int, default=5)
    parser.add_argument("--max-fetch-age-hours", type=int, default=36)
    parser.add_argument("--allow-stale-fetch", action="store_true")
    args = parser.parse_args()

    sources = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))
    fetched_dir = Path(args.fetched_dir)
    refs_dir = Path(args.references_dir)

    fetch_problems = validate_fetch_corpus(
        fetched_dir=fetched_dir,
        sources=sources,
        require_llms_index=True,
        max_age_hours=10**9 if args.allow_stale_fetch else args.max_fetch_age_hours,
    )

    structured_symbols = load_structured_symbols(Path(__file__).parents[2])
    ref_diffs: dict[str, dict] = {}

    for ref_file in sources:
        rule = REFERENCE_RULES.get(ref_file, RefRule(enabled_kinds=frozenset({IMPORTS, METHODS, CLI, OPTIONS, JSON_FIELDS})))
        ref_path = refs_dir / ref_file
        if not ref_path.exists():
            print(f"[warn] reference file {ref_path} not found, skipping")
            continue

        fetched_subdir = fetched_dir / ref_file.replace(".md", "")
        if not fetched_subdir.exists():
            print(f"[warn] fetched dir {fetched_subdir} not found, skipping")
            continue

        ref_text = ref_path.read_text(encoding="utf-8")
        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(fetched_subdir.glob("*.txt")))

        ref_foreign = _extract_foreign_symbols(ref_text, rule.owned_modules)
        docs_foreign = _extract_foreign_symbols(docs_text, rule.owned_modules)

        ref_buckets = bucket_symbols(extract_evidence(ref_text), rule, structured_symbols, ref_foreign)
        docs_buckets = bucket_symbols(extract_evidence(docs_text), rule, structured_symbols, docs_foreign)
        all_ref_symbols = all_bucket_symbols(ref_buckets)
        all_docs_symbols = all_bucket_symbols(docs_buckets)

        diff = {}
        for confidence in CONFIDENCE_ORDER:
            in_docs_not_ref = set_diff_with_aliases(docs_buckets[confidence], all_ref_symbols)
            in_ref_not_docs = set_diff_with_aliases(ref_buckets[confidence], all_docs_symbols)
            in_docs_not_ref = {token for token in in_docs_not_ref if not text_mentions_symbol(ref_text, token)}
            in_ref_not_docs = {token for token in in_ref_not_docs if not text_mentions_symbol(docs_text, token)}
            if confidence in rule.suppress_removals:
                in_ref_not_docs = set()
            verified = VERIFIED_FALSE_POSITIVES.get(ref_file, {})
            in_docs_not_ref -= verified.get(f"{confidence}_in_docs_not_ref", set())
            in_ref_not_docs -= verified.get(f"{confidence}_in_ref_not_docs", set())
            if confidence == HIGH_CONFIDENCE:
                in_docs_not_ref -= verified.get("in_docs_not_ref", set())
                in_ref_not_docs -= verified.get("in_ref_not_docs", set())
            diff[f"{confidence}_in_docs_not_ref"] = in_docs_not_ref
            diff[f"{confidence}_in_ref_not_docs"] = in_ref_not_docs

        ref_diffs[ref_file] = diff
        print(
            f"{ref_file}: "
            f"high +{len(diff['high_in_docs_not_ref'])}/-{len(diff['high_in_ref_not_docs'])}, "
            f"medium +{len(diff['medium_in_docs_not_ref'])}/-{len(diff['medium_in_ref_not_docs'])}, "
            f"low +{len(diff['low_in_docs_not_ref'])}/-{len(diff['low_in_ref_not_docs'])}"
        )

    new_pages: list[str] = []
    llms_path = fetched_dir / "llms.txt"
    if llms_path.exists():
        live_urls = extract_doc_urls(llms_path.read_text(encoding="utf-8"))
        new_pages = sorted(live_urls - tracked_urls(sources))
        if new_pages:
            print(f"{len(new_pages)} doc pages not tracked in sources.yaml")

    report = build_report(ref_diffs, new_pages, fetch_problems)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"Drift report written to {args.output}")

    significant = bool(fetch_problems) or bool(new_pages)
    if not significant:
        for diff in ref_diffs.values():
            if (
                len(diff["high_in_docs_not_ref"]) >= args.threshold
                or len(diff["high_in_ref_not_docs"]) >= args.threshold
                or len(diff["medium_in_docs_not_ref"]) >= args.threshold
                or len(diff["medium_in_ref_not_docs"]) >= args.threshold
            ):
                significant = True
                break
    return 1 if significant else 0


if __name__ == "__main__":
    sys.exit(main())
