# Changelog

All notable changes to the TensorLake skill are documented here.

## [2.0.2] — SDK 0.4.41 — 2026-04-08

### Changed
- **sandbox_sdk.md** — added `connect()`, `update_sandbox()`, `close()`/`terminate()`, `write_stdin()`/`close_stdin()`, `expose_ports()`/`unexpose_ports()`; renamed `create_pty_session()` → `create_pty()` and `pty_ws_url()` → `connect_pty()`; added `SandboxProcessStatus`, `SandboxProcessStdinMode`, `SandboxProcessOutputMode` enums; added `pty-sessions.md` source
- **sandbox_advanced.md** — added `close()`/`terminate()` teardown note in AI code execution best practices

## [2.0.1] — SDK 0.4.39 — 2026-04-07

### Fixed
- **check_drift.py** — eliminated false positives from cross-module symbol leakage, third-party API params, and multi-line import extraction gaps
  - Added `_normalize_imports()` to collapse multi-line `from X import (...)` statements
  - Added `_MODULE_OWNERS` and `_extract_foreign_symbols()` for cross-module filtering (both directions)
  - Added `THIRD_PARTY_PARAMS` frozenset for LLM/logging/agent SDK parameter noise
  - Expanded `_EXAMPLE_VAR_RE` patterns (`*_client`, `*_numbers`, `*_results`, ALL_CAPS tool defs)
  - Fixed code block regex to handle ```` ```python  theme={null} ```` format from fetched docs
  - Added TIER2 pattern for typed function signatures with lowercase Python types
  - Fixed falsy empty-list check (`if owned:` → `if owned is not None:`)
- **sandbox_sdk.md** — added `ContainerResourcesInfo` type for `resources` attribute, added `tl sbx terminate` to CLI reference, updated sandbox lifecycle docs

### Changed
- **sources.yaml** — added `applications/quickstart.md`, `applications/architecture.md`, `applications/error-handling.md` to applications_sdk sources

## [2.0.0] — SDK 0.4.39 — 2026-04-07

### Added
- **platform.md** — webhooks (event types, payloads, signature verification), authentication, access control (org/project roles), EU data residency
- **sandbox_advanced.md** — skills-in-sandboxes (multi-agent installation), AI code execution patterns, parallel data analysis, CI/CD build pipelines
- **troubleshooting.md** — common application issues (timeout, OOM, request failures), production integration workflow, document parsing benchmarks
- Source tracking headers (`Source`, `SDK version`, `Last verified`) added to all reference files
- `sources.yaml` now maps every reference file to its upstream doc URLs
- Automated drift detection via GitHub Actions (weekly `sync-check.yml`)

### Changed
- `sources.yaml` — moved all `_uncovered` entries into proper file mappings for the 3 new reference files

## [1.0.0] — SDK 0.4.39 — 2026-04-07

### Added
- **sandbox_sdk.md** — SandboxClient lifecycle, commands, file ops, snapshots, processes, networking, images
- **applications_sdk.md** — decorators, futures, map-reduce, async, durability, crash recovery, retries, secrets, timeouts, scaling, observability, cron, parallel sub-agents
- **documentai_sdk.md** — DocumentAI client, parsing options, structured extraction, page classification, edit, DOCX, charts, key-value, tables, signatures, barcodes, summarization, datasets
- **integrations.md** — LangChain, OpenAI, Anthropic, ChromaDB, Qdrant, Databricks, MotherDuck patterns
