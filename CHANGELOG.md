# Changelog

All notable changes to the TensorLake skill are documented here.

## [2.5.4] — 2026-04-28

### Changed (Snapshot restore — surfacing the filesystem/full distinction earlier)
- **`SKILL.md`, `AGENTS.md`** — added a Core Patterns bullet stating that snapshot restore is **not** uniformly "as-is": filesystem snapshots (the default) accept `cpus=`, `memory_mb=`, `disk_mb=` overrides at `Sandbox.create(snapshot_id=...)` (`disk_mb` growth-only, 10240–102400 MiB); full snapshots lock resources. Eagerly loaded so the agent doesn't fall back on stale priors when answering snapshot-restore questions without reading `sandbox_persistence.md`.
- **`references/sandbox_persistence.md`** — added a TL;DR callout at the top of the Snapshots section so the filesystem-default override behavior is encountered before the per-row "cannot be changed at restore time" wording in the Snapshot Types table. `Last verified: 2026-04-28`.
- **`references/sandbox_sdk.md`** — replaced the absolute "When restoring, the new sandbox inherits image, resources, entrypoint, and secrets from the snapshot — these cannot be overridden" line in the Snapshots (Instance) section with a type-distinguished version that links to `sandbox_persistence.md#snapshot-types--filesystem-default-vs-full`. `Last verified: 2026-04-28`.
- **`.github/scripts/sources.yaml`** — bumped `last_verified` for `sandbox_sdk.md` and `sandbox_persistence.md` to `2026-04-28`.

### Why
Eval 15 (`filesystem-snapshot-restore-with-resource-overrides`) regressed to 0/6 with the CI-pinned sonnet agent: the pre-0.5.3 absolute claim still in `sandbox_sdk.md:266` contradicted the 0.5.3 filesystem/full distinction in `sandbox_persistence.md`, and the agent was answering from a strong "restore is as-is" prior — fabricating quotes rather than reading the reference. Putting the override fact directly in `SKILL.md` / `AGENTS.md` lifted the score to 6/6.

## [2.5.3] — SDK 0.5.3 — 2026-04-27

### Changed (References — verified against live docs)
- **`references/sandbox_sdk.md`** — bumped to SDK 0.5.3. Added `disk_mb` (10240–102400 MiB, growth-only) to `Sandbox.create()` and `resources` info. Added intro paragraph on Firecracker/CloudHypervisor MicroVMs, boot times, HIPAA + SOC 2 Type II + EU residency + zero data retention. Expanded TypeScript `createPty()` example with `args`, `env`, `workingDir`, `onData`, `onExit` (with note that Python attaches via `pty.on_data(...)` after creation). Expanded desktop API table with `mouse_press`, `mouse_release`, `scroll`, `width`/`height` properties, plus ~4s startup delay note. Documented `image.build(cpus, memory_mb, disk_mb)` (defaults 2.0 / 4096 / 10240) and `tl sbx image create --cpus --memory --disk_mb`. Added `tl sbx clone` to CLI commands. Added `debian11-minimal`, `debian12-minimal`, `debian-minimal` to base images table; dropped `tensorlake/` prefix from base-image references.
- **`references/sandbox_persistence.md`** — bumped to SDK 0.5.3. Added Filesystem (default) vs Full snapshot distinction with comparison table. Documented `sandbox.checkpoint(timeout=300, poll_interval=1.0)` defaults. Added `tl sbx clone` CLI shortcut (CLI-only, no SDK equivalent). Updated restore semantics: filesystem snapshots accept `cpus=`, `memory_mb=`, `disk_mb=` overrides at restore (`disk_mb` growth-only); full snapshots remain locked.
- **`references/sandbox_advanced.md`** — dropped `tensorlake/` prefix from base-image references for consistency with the docs' base-image table.

## [2.5.2] — 2026-04-27

### Added (Eval CI)
- **`.github/workflows/evals.yml`** — CI workflow that runs the eval suite on PRs touching `references/**.md`. Triggers narrowly: version bumps, `SKILL.md`/`AGENTS.md` edits, and `evals/**` script changes do NOT auto-run evals. Full runs are available via `workflow_dispatch` (with optional comma-separated eval IDs).
- **`evals/filter.py`** — maps changed files to eval IDs via each eval's `references[]` field, deduplicating across overlapping reference files. Empty result skips the CI job.
- **`evals/ci_summary.py`** — renders a markdown summary table for `$GITHUB_STEP_SUMMARY`. Report-only (always exits 0); failures show in the table and uploaded `eval-workspace` artifact, never block the PR.

### Changed (Eval harness)
- **`evals/grade.py`** — `JUDGE_MODEL` constant replaced by a `--model` CLI flag (`DEFAULT_JUDGE_MODEL` = `claude-opus-4-7`). Judge model now propagates into `benchmark.json` → `metadata.analyzer_model`.
- **`evals/run.py`** — writes `evals/workspace/iteration-N/run_meta.json` recording the executor model. `grade.py` reads it so `benchmark.json` → `metadata.executor_model` reflects the real model used (was previously hardcoded as `"default (claude -p)"`).
- CI is pinned to **agent: `claude-sonnet-4-6`**, **judge: `claude-haiku-4-5-20251001`**.

### Fixed
- **`evals/evals.json`** eval 1 (`named-sandbox-suspend-resume`) — expectation #4 no longer requires an unsolicited contrast against snapshot/restore. The original prompt asks only about suspend/resume + ephemeral, and `expected_output` doesn't request the comparison either; the negative-direction expectation #5 still tests the underlying misconception.

## [2.5.1] — SDK 0.5.1 — 2026-04-25

### Changed (Sandbox SDK 0.5.1)
- **sandbox_sdk.md** — updated to reflect 0.5.1 API surface:
  - Rename and port exposure now live on the `Sandbox` instance via `sandbox.update(name=..., exposed_ports=..., allow_unauthenticated_access=...)`. `SandboxClient.update_sandbox` / `expose_ports` / `unexpose_ports` still work but are deprecated.
  - `expose_ports` / `allow_unauthenticated_access` removed from `Sandbox.create()` parameters — port exposure is now a post-create operation.
  - `SandboxClient` construction emits a `DeprecationWarning`. Only `client.list()` lacks a direct `Sandbox`-level replacement.
  - `sandbox.status` returns a `SandboxStatus` enum (e.g., `SandboxStatus.RUNNING`); use `.value` for the lowercase string form.
  - `sandbox.read_file(...)` / `sandbox.list_directory(...)` now return `Traced[...]` — unwrap with `.value`.
- **sources.yaml** — bumped `sandbox_sdk.md` to `sdk_version: 0.5.1`, `last_verified: 2026-04-25`.
- Verified all examples in **sandbox_persistence.md** continue to run cleanly against `tensorlake==0.5.1` (no doc changes needed).

## [2.5.0] — SDK 0.5.0 — 2026-04-24

### Changed (breaking — Sandbox SDK 0.5.0)
- **sandbox_sdk.md** — rewritten for the 0.5.0 Sandbox API. `SandboxClient` is **removed**; the entry point is now the `Sandbox` class itself:
  - Static methods: `Sandbox.create()`, `Sandbox.connect()`, `Sandbox.list()`, `Sandbox.update()`, `Sandbox.expose_ports()`, `Sandbox.unexpose_ports()`, `Sandbox.get_snapshot()`, `Sandbox.delete_snapshot()`
  - Instance methods on returned handles: `.suspend()`, `.resume()`, `.terminate()`, `.checkpoint()` (replaces `snapshot_and_wait`), `.list_snapshots()`, `.run()`, file / process / PTY operations
  - `create_and_connect()` is gone — `Sandbox.create()` now returns a ready-to-use handle
  - Snapshot restore: `Sandbox.create(snapshot_id=...)` (was `client.create_and_connect(snapshot_id=...)`)
  - New creation parameters: `expose_ports`, `allow_unauthenticated_access`
  - `Image.build()` now exists in Python too (was TypeScript-only via `createSandboxImage()`)
  - `tl sbx new` → `tl sbx create`; `tl sbx snapshot <id>` → `tl sbx checkpoint <id>`
- **sandbox_persistence.md** — updated every snippet to the new static/instance split. `client.snapshot_and_wait()` → `sandbox.checkpoint()`; `client.suspend()` / `client.resume()` → `sandbox.suspend()` / `sandbox.resume()`; restore via `Sandbox.create(snapshot_id=...)`. Added top-of-file 0.5.0 upgrade note.
- **sandbox_advanced.md** — replaced every `SandboxClient` / `create_and_connect` / `snapshot_and_wait` / `sandbox.close()` with the new API in Skills-in-Sandboxes, AI Code Execution, Data Analysis, and CI/CD patterns
- **integrations.md** — updated LangChain, OpenAI function-calling, and multi-agent examples to use `Sandbox.create()` / `sandbox.terminate()`
- **SKILL.md** / **AGENTS.md** — bumped version to 2.5.0. Updated CLI quick-reference (`tl sbx create`, `tl sbx checkpoint`). Annotated the LLM code-execution pattern with the 0.5.0 import change.
- **sources.yaml** — bumped every `sdk_version` to `0.5.0` and `last_verified` to `2026-04-24`. Added `sandboxes/lifecycle.md` to the `sandbox_sdk.md` source list (now explicitly referenced for the static-method API surface).
- All reference files — bumped `SDK version:` / `Last verified:` headers together, per the paired-bump rule.

## [2.4.1] — 2026-04-22

### Added
- **SKILL.md** / **AGENTS.md** — "Verify before suggesting" guardrail: before showing any Tensorlake SDK code, confirm every symbol (import path, class, method, parameter) exists in the installed package or in `references/`, and say so instead of guessing when a symbol can't be verified

## [2.4.0] — SDK 0.4.49 — 2026-04-22

### Added
- **sandbox_sdk.md** — new **Browser Access with noVNC** subsection under Computer Use: backend-tunnel + WebSocket bridge architecture for live human-facing desktop streams on VNC port `5901` (password `tensorlake`), with a `@novnc/novnc` browser client snippet and the hybrid pattern of `noVNC` for the live view + `sandbox.connect_desktop()` for programmatic actions. Sourced from the new upstream section in `sandboxes/computer-use.md`
- **sandbox_sdk.md** — new **Running Docker Inside a Sandbox** subsection under Sandbox Images, cross-referencing the new upstream `sandboxes/docker.md` page (full install script lives there; `ubuntu-systemd` base image was already in the Base Images table)
- **sandbox_sdk.md** — `sandboxes/sdk-reference.md` (new upstream Sandbox SDK Reference page) and `sandboxes/docker.md` added to the source URL header
- **sources.yaml** — four sources added to `sandbox_sdk.md`: `sandboxes/sdk-reference.md`, `sandboxes/docker.md`, `sandboxes/environment-variables.md`, `sandboxes/quickstart.md`. The last two were already in the reference file's source header (added in v2.3.1) but had never been registered in `sources.yaml` — a drift-check bug from that release
- **CLAUDE.md** — new rule: `SDK version:` and `Last verified:` must always bump together. Bumping the SDK version without also bumping the date creates a false record claiming verification against a newer SDK on an older date. Applies to PyPI releases, content edits, and `Source:` / `sources.yaml` URL changes

### Changed
- **SKILL.md** / **AGENTS.md** / **README.md** — renamed the product from "Orchestrate" to "Orchestration" to match the upstream docs terminology shift in `agent-skills.md` and the new `sandboxes/sdk-reference.md`. Affects the "Two APIs" opening paragraph, Quick Start heading, Core Patterns bullet, reference-list title (`Orchestration SDK`), and the README description/tree comment. Lowercase verb uses of "orchestrate" ("orchestrate multi-step LLM pipelines") were left alone
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
