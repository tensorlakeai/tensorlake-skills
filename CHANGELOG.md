# Changelog

All notable changes to the TensorLake skill are documented here.

## [2.4.1] — 2026-04-22

### Added
- **SKILL.md** / **AGENTS.md** — "Verify before suggesting" guardrail: before showing any Tensorlake SDK code, confirm every symbol (import path, class, method, parameter) exists in the installed package or in `references/`, and say so instead of guessing when a symbol can't be verified

## [2.4.0] — SDK 0.4.49 — 2026-04-22

### Added
- **sandbox_sdk.md** — new **Browser Access with noVNC** subsection under Computer Use: backend-tunnel + WebSocket bridge architecture for live human-facing desktop streams on VNC port `5901` (password `tensorlake`), with a `@novnc/novnc` browser client snippet and the hybrid pattern of `noVNC` for the live view + `sandbox.connect_desktop()` for programmatic actions. Sourced from the new upstream section in `sandboxes/computer-use.md`
- **sandbox_sdk.md** — new **Running Docker Inside a Sandbox** subsection under Sandbox Images, cross-referencing the new upstream `sandboxes/docker.md` page (full install script lives there; `ubuntu-systemd` base image was already in the Base Images table)
- **sandbox_sdk.md** — `sandboxes/concepts.md` (new upstream Sandbox SDK Reference page) and `sandboxes/docker.md` added to the source URL header
- **sources.yaml** — four sources added to `sandbox_sdk.md`: `sandboxes/concepts.md`, `sandboxes/docker.md`, `sandboxes/environment-variables.md`, `sandboxes/quickstart.md`. The last two were already in the reference file's source header (added in v2.3.1) but had never been registered in `sources.yaml` — a drift-check bug from that release
- **CLAUDE.md** — new rule: `SDK version:` and `Last verified:` must always bump together. Bumping the SDK version without also bumping the date creates a false record claiming verification against a newer SDK on an older date. Applies to PyPI releases, content edits, and `Source:` / `sources.yaml` URL changes

### Changed
- **SKILL.md** / **AGENTS.md** / **README.md** — renamed the product from "Orchestrate" to "Orchestration" to match the upstream docs terminology shift in `agent-skills.md` and the new `sandboxes/concepts.md`. Affects the "Two APIs" opening paragraph, Quick Start heading, Core Patterns bullet, reference-list title (`Orchestration SDK`), and the README description/tree comment. Lowercase verb uses of "orchestrate" ("orchestrate multi-step LLM pipelines") were left alone
- All reference files + `sources.yaml` + README example — bumped `SDK version:` / `sdk_version:` to `tensorlake 0.4.49` (latest on PyPI) and `Last verified:` / `last_verified:` to `2026-04-22`

### Fixed
- **applications_sdk.md** / **sources.yaml** — removed dangling `applications/guides/autoscaling.md` entry (upstream page deleted in docs commit 3abea5f; content was consolidated into `applications/scaling-agents.md`, which was already tracked)

## [2.3.1] — SDK 0.4.46 — 2026-04-16

### Added
- **sandbox_sdk.md** — new **Environment Variables** section consolidating command-scope (`sandbox.run`), process-scope (`start_process`), and PTY-scope (`create_pty`) env usage, plus the `tl sbx exec --env` and `tl sbx ssh --env` CLI flags, sourced from the new upstream `sandboxes/environment-variables.md` page
- **sandbox_sdk.md** — `pip install tensorlake` and `tl login` / `TENSORLAKE_API_KEY` auth note in the Install line, sourced from the new upstream `sandboxes/quickstart.md` page
- **sandbox_sdk.md** — `ubuntu-vnc` row added to the Base Images table (previously only referenced in the Computer Use section)
- **sandbox_sdk.md** — `sandboxes/environment-variables.md` and `sandboxes/quickstart.md` added to the source URL header

### Changed
- **sandbox_sdk.md** / **sandbox_persistence.md** — bumped `SDK version` header to `tensorlake 0.4.46` and `Last verified` to `2026-04-16`

## [2.3.0] — SDK 0.4.44 — 2026-04-14

### Changed
- **SKILL.md** / **AGENTS.md** — reworded the Setup section to clarify that the skill declares no required environment variables: `TENSORLAKE_API_KEY` is a runtime prerequisite for the user's code (not a plugin/skill config), and provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) are only needed when the user opts into the corresponding integration. Named `TENSORLAKE_API_KEY` as the canonical env var (no aliases), distinguished the key *value* format `tl_apiKey_*` from the env var name, and documented the `secrets=[...]` + `tensorlake secrets set` pattern with a "never inline the value" guardrail
- **sandbox_advanced.md** — added a Scope note to the `Skills in Sandboxes` section clarifying that the install patterns are templates for user-built sandbox images; the agent must not write to discovery paths (`~/.claude/skills/`, `~/.agents/skills/`) on the user's host or shared systems

### Fixed
- **platform.md** — replaced the dangerous `Disable CSRF protection on your endpoint` webhook instruction with safer guidance: exempt only the webhook route from CSRF middleware and verify the Svix signature on every request
- **sandbox_persistence.md** — renamed all 6 occurrences of `$TL_API_KEY` in curl examples to `$TENSORLAKE_API_KEY` to match the canonical env var name used everywhere else

## [2.2.0] — SDK 0.4.44 — 2026-04-10

### Added
- **sandbox_persistence.md** — new state-centric reference split out from `sandbox_sdk.md`: sandbox state machine with transitions and per-state billability table, ephemeral vs named sandboxes, snapshots (create / restore / list / delete / `snapshot_and_wait` parameters), clone (CLI only), suspend & resume (Python / TypeScript / CLI / REST, with status codes), idle auto-suspend and auto-resume, `Suspend vs Snapshot` comparison table, and a limitations section
- **SKILL.md** / **AGENTS.md** — surfaced sandbox persistence in the frontmatter description and the opening "Two APIs" paragraph so the skill auto-triggers on queries about stateful/persistent sandboxes; added cross-link to `sandbox_persistence.md` from the Core Patterns bullet
- **CLAUDE.md** — new rule: `SKILL.md` and `AGENTS.md` must stay in sync on substantive changes (frontmatter, opening paragraph, Quick Start, Key Rules, Core Patterns, Reference Documentation, CLI Commands)

### Changed
- **sandbox_sdk.md** — trimmed `Ephemeral vs Named Sandboxes`, `Snapshots`, `Clone`, `Suspend & Resume`, `Idle Suspend and Auto-Resume`, and `Sandbox Statuses` sections (all moved into `sandbox_persistence.md`); removed `lifecycle.md` and `snapshots.md` from the source header; added pointers to `sandbox_persistence.md` from the header and the former persistence sections
- **sources.yaml** — new `sandbox_persistence.md` entry mapping to `sandboxes/lifecycle.md` and `sandboxes/snapshots.md`; removed those two pages from `sandbox_sdk.md`'s source list
- **SKILL.md** / **AGENTS.md** / **README.md** — added `references/sandbox_persistence.md` to the reference documentation list; refined the `sandbox_sdk.md` description to reflect its trimmed scope (create, connect, run commands, file ops, processes, networking, images)
- **check_drift.py** — registered `sandbox_persistence.md` in `MODULE_OWNERS` (owns `tensorlake.sandbox`) and `REFERENCE_RULES` (same configuration as `sandbox_sdk.md`: `sbx_` CLI prefix); expanded `METHOD_CALL_RE` to match `sandbox_client.*` / `sandboxClient.*` / `doc_ai_client.*` variants so docs using those variable names are no longer invisible; added `REVERSE_ALIASES` and taught `source_urls_for_token()` to report which alias form actually matched in a doc; threaded alias annotations through `build_report()` for `in_docs_not_ref` evidence; added `"_skip"` routes for `/api-reference/`, `/examples/`, `/faqs/`, `/opensource/`, `/use-cases/` to `ROUTE_RULES`; disabled the raw-text "symbol appears somewhere" safety net for HIGH-confidence drift (structural extraction is trustworthy enough that a loose word match in prose should no longer mask real additions/removals)

### Fixed
- **sandbox_persistence.md** — corrected snapshot restore semantics: a restored sandbox inherits image, resources, entrypoint, and secrets from the snapshot **exactly as captured** and none of these can be overridden at restore time (the upstream docs' override examples are misleading — flag to docs team)
- **sandbox_persistence.md** — corrected suspend/resume semantics: resume brings the **same** sandbox back to `Running` with its `sandbox_id` and name preserved; it is not described as "restoring from a snapshot into a new sandbox" (that framing conflates the internal suspend mechanism with the user-facing model)
- **check_drift.py** — added `ReplayMode` to `VERIFIED_FALSE_POSITIVES["applications_sdk.md"]["in_ref_not_docs"]`: the reference imports it (HIGH confidence via `PY_IMPORT_RE`) but the live `applications/durability` page only mentions it inline in prose snippets like `request.replay(mode=ReplayMode.ADAPTIVE)`, which the structural extractor does not capture. Combined with the new HIGH-confidence text-fallback behavior, this was producing a spurious drift entry
- **check_drift.py** — added `suspend`, `resume`, `snapshot_and_wait`, `get_snapshot`, `list_snapshots`, `delete_snapshot` to `VERIFIED_FALSE_POSITIVES["sandbox_sdk.md"]["in_docs_not_ref"]`: these symbols now live in `sandbox_persistence.md`, but `sandboxes/introduction.md` (still a `sandbox_sdk.md` source) mentions them in quickstart snippets. The drift checker runs each reference file in isolation and cannot see sibling coverage
- **check_drift.py** — documented the `SandboxProcessStdinMode` false positive (Python enum that canonicalizes from the TypeScript `StdinMode` alias)

## [2.1.2] — SDK 0.4.43 — 2026-04-09

### Added
- **sandbox_sdk.md** — added Computer Use (Desktop Automation) section: `connect_desktop()`, `screenshot()`, `press()`, `type_text()`, `move_mouse()`, `click()`, `double_click()`, `scroll()`, `key_down()`, `key_up()` with `ubuntu-vnc` image

### Changed
- **check_drift.py** — added `("/api-reference/", "_skip")` to `ROUTE_RULES` so API reference pages are excluded from the drift report
- **sources.yaml** — added `sandboxes/computer-use.md` to `sandbox_sdk.md` sources

## [2.1.1] — SDK 0.4.42 — 2026-04-08

### Changed
- **check_drift.py** — separated evidence by confidence, restricted the rendered report to high-confidence drift, added per-symbol source URL attribution, parsed `llms.txt` line-by-line from Markdown links, and reduced false positives across sandbox/applications references
- **fetch_docs.py** — preserve previously fetched pages/checksums on failed retries so a bad fetch cannot poison the manifest
- **sources.yaml** / **references/** — expanded non-API doc coverage from `llms.txt`, synchronized source headers in reference files, and added `sandboxes/pty-sessions.md` so PTY symbols stop reporting as false removals

## [2.1.0] — SDK 0.4.42 — 2026-04-08

### Added
- **sandbox_sdk.md** — added TypeScript SDK alongside all Python examples: imports (`import { SandboxClient } from "tensorlake"`), client init (`SandboxClient.forCloud()`), `create()`, `connect()`, `get()`, `delete()`, `update()`, `createAndConnect()`, `run()`, file ops (`writeFile`/`readFile`/`deleteFile`), `startProcess()`/`followOutput()`, `writeStdin()`/`closeStdin()`, `createPty()`, snapshots (`snapshotAndWait`/`listSnapshots`/`getSnapshot`/`deleteSnapshot`), `exposePorts()`/`unexposePorts()`, Image builder with `createSandboxImage()`
- **sandbox_sdk.md** — documented `identifier` parameter on Python `connect()` (accepts sandbox_id or name), and name-or-ID acceptance on `get()`/`delete()`/`update_sandbox()`
- **sandbox_sdk.md** — documented Sandbox properties: Python `sandbox.sandbox_id`/`sandbox.name` vs TypeScript `sandbox.sandboxId`/`sandbox.name`
- **sandbox_sdk.md** — added `allow_out`/`allowOut` networking parameter for outbound allowlist
- **sandbox_advanced.md** — added TypeScript AI code execution example with `SandboxClient.forCloud()` and `createAndConnect()`
- **SKILL.md** / **AGENTS.md** — documented TypeScript SDK availability (`npm install tensorlake`) and `npx tl login` setup

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
