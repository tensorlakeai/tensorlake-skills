# Changelog

All notable changes to the TensorLake skill are documented here.

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
