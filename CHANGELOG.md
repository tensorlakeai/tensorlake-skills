# Changelog

All notable changes to the TensorLake skill are documented here.

## [2.9.0] — SDK 0.5.44 — 2026-06-16

### Added
- **`references/sandbox_sdk.md`** — new "Managed Processes" section: supervised background processes via `start_process(..., name=, restart=RestartPolicyConfig(...), health_check=ProcessHealthCheck(...), user=)`, plus `get_process` / `restart_process` (TS `getProcess` / `restartProcess`), the new imports (`ProcessHealthCheck`, `ProcessHealthCheckType`, `RestartPolicy`, `RestartPolicyConfig`), restart policies (`never` / `on_failure` / `always`), HTTP/TCP health checks, default process user `tl-user`, and CLI `--detach` / `tl sbx ps|restart|kill`. New "Import an Image from a Registry" section (`tl sbx image import`, `import_sandbox_image()`, `importSandboxImage()`) and "Public Images" section (`--public` / `is_public` / `isPublic` for cross-namespace resolvable names).
- **`references/sandbox_usecases.md`** — new "Claude Managed Agents" section (run the Claude Agent SDK / managed agents on sandboxes: brain-vs-hands model, three orchestrator modes, recreate-vs-resume for long sessions, per-command env injection, common failure modes) and a concise "Agentic Dungeons & Dragons" section (branch→map→reduce multi-agent demo running untrusted dice scripts in isolated sandboxes). Added `claude-managed-agents.md` and `agentic-d&g.md` to the source list.
- **`references/feature_lookup.md`** — new entries for Claude managed agents and Agentic Dungeons & Dragons.

### Changed
- **`references/sandbox_sdk.md`** — bumped SDK version 0.5.17 → 0.5.44 and `Last verified:` to 2026-06-16. Removed `sandboxes/processes.md` from the source list (it now redirects into `sandboxes/commands.md`, "Commands & Processes"). Image build API now uses `image.build(registered_name=...)` / `registeredName` (was bare `build()`), with `context_dir` / `contextDir`, `builder_disk_mb` / `builderDiskMb`, corrected build defaults, and fully-qualified base names; added `tl sbx image register` / `tl sbx image ls`. `SandboxInfo` corrected: lowercase `SandboxStatus` enum, added `ingress_endpoint` / `sandbox_url` / `network`, nullable `image` / `timeout_secs` / `exposed_ports` / `entrypoint`, dropped undocumented `secret_names` and `resources.disk_mb`. "Supported Build Operations" rewritten to the live Dockerfile limitations. Expanded SSH (tmux/screen persistent shells, auth-failure messages, `tl sbx ls -r`, `IdentitiesOnly`). File ops use `bytes(read_file(...))` and `list_directory(...).entries`.
- **`references/applications_sdk.md`** — bumped SDK version 0.5.0 → 0.5.44 and `Last verified:` to 2026-06-16. CLI corrected to `tl app deploy` / `tl app new`; `@application` defaults clarified (no retries by default, any-region); class-method applications callable by name string; `progress.update()` corrected to positional `current, total, message=None, attributes=None`; `File` raw-bytes / 5 TB note; scaling rate-limit formula (`max_containers × concurrency`); Cron Scheduler expanded (per-minute granularity, `schedule_id`, List/Delete endpoints, 1 MiB input limit); Secrets corrected to envelope encryption (per-project DEK wrapped by KMS KEK, mTLS); Observability/Logging corrected to structlog-style `Logger` usage, log levels TRACE–ERROR, 7-day retention, and the `GET /logs` query API.
- **`references/sandbox_persistence.md`** — bumped SDK version 0.5.17 → 0.5.44 and `Last verified:` to 2026-06-16. Corrected the memory-snapshot restore lock: only image, resources (CPUs, memory), and entrypoint are inherited/immutable — `secrets` removed from that list (fixed in the TL;DR, Snapshot Types table, restore bullet, and Limitations). Clarified omitted snapshot type is a server-side default (currently `filesystem`).
- **`references/computer_use.md`** — bumped SDK version 0.5.17 → 0.5.44 and `Last verified:` to 2026-06-16 (content already matched the live doc; no material changes).
- **`.github/scripts/sources.yaml`** — bumped `sdk_version` / `last_verified` to `0.5.44` / `2026-06-16` for `sandbox_sdk.md`, `computer_use.md`, `sandbox_persistence.md`, `applications_sdk.md`, and `sandbox_usecases.md`. Removed `processes.md` from `sandbox_sdk.md` sources; added `claude-managed-agents.md` and `agentic-d&g.md` to `sandbox_usecases.md` sources.
- **`README.md`** — illustrative source-header example bumped to `tensorlake 0.5.44` / `2026-06-16`.

## [2.8.0] — SDK 0.5.17 — 2026-05-23

### Added
- **`references/sandbox_sdk.md`** — new "SSH" subsection covering one-time key registration via `tl sbx ssh keys add`, connection through `ssh <sandbox-id>@sandbox.tensorlake.ai`, file transfer (`scp`/`sftp`/`rsync`), port forwarding (`-L` / `-D` / `-R`), `~/.ssh/config` block from `tl sbx describe`, and VS Code Remote-SSH / JetBrains Gateway / Cursor usage. New "Resource Limits and Timeouts" table covering `cpus`, `memory_mb` (1024–8192 MB per CPU core), `disk_mb` (10240–102400 MiB, growth-only on restore), and `timeout_secs` semantics (idle threshold, `0` requests plan max, named → suspend / ephemeral → terminate). New "OCI base images" coverage under "Base Images" — any standard OCI reference (`python:3.12-slim`, `node:22-alpine`, `ghcr.io/...`, `public.ecr.aws/...`) plus private-registry auth via `~/.docker/config.json`.
- **`references/sandbox_persistence.md`** — new "Resource Limits and Timeouts" section (mirrors the SDK reference) covering create-time-only resources, idle-threshold timeout semantics, plan-max table, and named-vs-ephemeral timeout outcomes.
- **`references/computer_use.md`** — new "Connect with a VNC Client" subsection covering `tl sbx tunnel <sandbox-id> 5901 --listen-port 15901` plus macOS Screen Sharing / TigerVNC / Remmina / KRDC client commands. Added complete JavaScript/TypeScript examples for Quickstart and "Reconnect to an Existing Desktop Sandbox" (was Python-only). Expanded methods table to call out `doubleClick`, `typeText`, `scrollDown`, `keyDown`.
- **`references/sandbox_usecases.md`** — new "Sandbox as a Dev Environment" section (named sandbox as portable cloud workstation): one-time SSH key registration, named-sandbox create with `--disk_mb` / `--timeout`, `~/.ssh/config` entry, VS Code Remote-SSH walkthrough on `/home/tl-user/workspace`, day-to-day flow including long-job vs. SSH disconnect tradeoffs and explicit suspend/resume. Added `remote-dev.md` to the source list.
- **`references/feature_lookup.md`** — new entries for SSH access, Sandbox as a dev environment, and OCI base images.

### Changed
- **`references/sandbox_sdk.md`** — bumped SDK version 0.5.8 → 0.5.17 and `Last verified:` to 2026-05-23. Rewrote List/Rename → "List, Inspect, Rename": listing now uses `Sandbox.list()`, with `sandbox.info()` for per-sandbox metadata; `SandboxClient` flagged as fully deprecated with `Sandbox`-level equivalents for every operation. Image names in the base-image table and the intro paragraph qualified to `tensorlake/ubuntu-minimal` / `tensorlake/ubuntu-systemd` / `tensorlake/ubuntu-vnc` / `tensorlake/debian-minimal`. Noted that TS `sandbox.status()` is an async method (not a getter) and that `sandbox.update(...)` is the canonical handle for rename / port exposure.
- **`references/sandbox_persistence.md`** — bumped SDK version 0.5.5 → 0.5.17 and `Last verified:` to 2026-05-23. Promote-ephemeral example now uses `sandbox.update(name=...)` (returns `Traced[SandboxInfo]`; original handle is renamed in place) and the legacy `SandboxClient().update_sandbox(...)` form is noted as deprecated. Added cross-links to the new SSH / dev-environment / computer-use sections.
- **`references/computer_use.md`** — bumped SDK version 0.5.5 → 0.5.17 and `Last verified:` to 2026-05-23. All image references updated to `tensorlake/ubuntu-vnc`. Startup-delay guidance bumped to ≈5s with a snapshot-restore caveat (vncserver up before XFCE settles → first `Ctrl+Alt+T` can drop). Clarified that `sandbox.close()` on a `Sandbox.connect(...)` handle closes the client only; `sandbox.terminate()` is required to stop the VM.
- **`references/sandbox_usecases.md`** — bumped SDK version 0.5.8 → 0.5.17 and `Last verified:` to 2026-05-23. Chrome-CDP launch command updated to the fully-qualified `tensorlake/ubuntu-vnc` image.
- **`.github/scripts/sources.yaml`** — bumped `sdk_version` and `last_verified` for `sandbox_sdk.md`, `computer_use.md`, `sandbox_persistence.md`, and `sandbox_usecases.md` to `0.5.17` / `2026-05-23`. Added `https://docs.tensorlake.ai/sandboxes/remote-dev.md` to `sandbox_usecases.md` sources.
- **`SKILL.md` / `AGENTS.md`** — extended the trigger description with "file transfer, SSH access, remote-dev (VS Code Remote-SSH), or OCI base images" so the skill activates on SSH-into-a-sandbox / remote-dev-environment / OCI-base-image phrasing. Description length 1009 chars, under the 1024-char loader limit.
- **`README.md`** — illustrative source-header example bumped to `tensorlake 0.5.17` / `2026-05-23`. Added three new bullets to "When It Triggers": SSH access (with `scp`/`sftp`/`rsync` + port forwarding), named sandbox as a remote dev environment (VS Code Remote-SSH / JetBrains Gateway / Cursor), and OCI base images for `tl sbx image create`.

### Fixed
- **`references/sandbox_sdk.md`** — corrected three API claims surfaced during the 0.5.17 audit: (1) TypeScript `Sandbox.connect(...)` only accepts an options object (`{ sandboxId: "..." }`) — bare-string examples removed; the TS runtime reads `options.sandboxId` and would throw on a bare string. (2) `sandbox.update(...)` returns `Traced[SandboxInfo]` in Python and `Promise<Traced<SandboxInfo>>` in TS, not a renamed `Sandbox` handle — example restored to the original `info = sandbox.update(name="my-env")` form with `info.value.name` access. (3) `SandboxStatus` string values are lowercase in both Python and TypeScript (`"suspended"`, `"running"`, …), not capitalized — example filter switched to `SandboxStatus.SUSPENDED` and the trailing prose corrected.
- **`references/sandbox_persistence.md`** — same `sandbox.update(name=...)` return-type correction (was incorrectly described as returning a renamed `Sandbox`).

## [2.7.1] — 2026-05-06

### Changed
- **`SKILL.md` / `AGENTS.md`** — trimmed the skill description from 1145 → 946 chars to fit under the 1024-char limit enforced by skill loaders. Preserved all trigger keywords (sandboxes, suspend/resume, snapshots, custom images, ports, egress, PTY, computer-use, Chrome CDP, Playwright, tunnels, async, Harbor, RL rollouts, file transfer, orchestration, LLM providers, frameworks, llms.txt). Mainly tightened phrasing — e.g., "guide for writing code that uses Tensorlake's sandbox product to build" → "sandboxes for", "for example" → "e.g.", "Claude agents sdk, OpenAI agents sdk" → "Claude/OpenAI agents SDK"; dropped "as the infrastructure layer" and "live docs from".

## [2.7.0] — 2026-05-06

### Added
- **`references/sandbox_sdk.md`** — new "Async SDK (Python)" section covering `AsyncSandbox.create` / `connect`, async context manager, `asyncio.gather` fan-out, the `sandbox_id`-on-fresh-handle caveat, and async background processes / file ops / suspend / checkpoint. New "Local Tunnels" section under Networking covering the CLI (`tl sbx tunnel`), TypeScript `sandbox.createTunnel(remotePort, options)` returning a `TcpTunnel`, the Python subprocess wrapper, common patterns table (VNC/CDP/Postgres/dev server), and troubleshooting.
- **`references/sandbox_usecases.md`** — new "Drive Chrome over CDP" section (sandboxed Google Chrome with `--remote-debugging-port`, `--remote-allow-origins=*`, `--user-data-dir`; tunnel; Playwright `connect_over_cdp`; raw CDP WebSocket; `chrome-devtools-mcp` registration for Claude Code / Codex; version pitfalls). New "Harbor (evals + RL rollouts)" section covering `harbor[tensorlake]` install, `harbor run --env tensorlake`, `harbor env attach`, `task.toml` `[environment]` block forwarding to `cpus`/`memory_mb`/`ephemeral_disk_mb`/`allow_internet_access`.
- **`references/feature_lookup.md`** — new entries for Async SDK, Local tunnels, Drive Chrome over CDP (Core), and Harbor (Use cases).

### Changed
- **`references/sandbox_sdk.md`** — bumped SDK version 0.5.5 → 0.5.8 and `Last verified:` to 2026-05-06. API audit corrections against installed `tensorlake==0.5.8`: TypeScript `Sandbox.connect("name")` examples corrected to `Sandbox.connect({ sandboxId: "name" })` (the static signature requires an options object); `Sandbox.exposePorts/unexposePorts` static-method examples replaced with `sandbox.update({ exposedPorts, allowUnauthenticatedAccess })` and `SandboxClient` instance forms; removed the false claim that Python's `Image` lacks `.workdir(path)`; corrected `SnapshotInfo.status` values (`SnapshotStatus`: `"in_progress" | "completed" | "failed"`) and added `snapshot_type` / `rootfs_disk_bytes` / `base_image` fields; renamed Process Status / Mode enums to actual class names (`ProcessStatus`, `StdinMode`, `OutputMode`).
- **`references/sandbox_persistence.md`** — corrected the TypeScript `Sandbox.connect("my-env")` example to `Sandbox.connect({ sandboxId: "my-env" })` in the Suspend & Resume section.
- **`references/sandbox_usecases.md`** — bumped SDK version 0.5.5 → 0.5.8 and `Last verified:` to 2026-05-06; corrected source URL `ai-code-execution.md` → `tool-calls.md` to align with live `llms.txt`.
- **`.github/scripts/sources.yaml`** — added `async.md` and `tunnels.md` to `sandbox_sdk.md` sources; added `chrome-cdp.md` and `harbor.md` to `sandbox_usecases.md` sources; bumped both `sdk_version` to `0.5.8` and `last_verified` to `2026-05-06`.
- **`README.md`** — illustrative source-header example bumped to `tensorlake 0.5.8` / `2026-05-06`.

## [2.6.3] — 2026-04-30

### Changed
- **`references/sandbox_persistence.md`** — added a callout in the "Restore from a Snapshot" section directing agents to read an existing snapshot's type from the documented inspection API (`Sandbox.get_snapshot(...).snapshot_type` / `Sandbox.getSnapshot(...).snapshotType` / `tl sbx checkpoint ls` / `GET /snapshots/<id>` / dashboard) instead of deducing from creation-time defaults. Bumped `Last verified:` to 2026-04-30 in both the file header and `.github/scripts/sources.yaml`.
- **`evals/evals.json`** — tightened task 15 (`filesystem-snapshot-restore-with-resource-overrides`): the snapshot-type-inspection expectation is now an unconditional requirement and explicitly disallows deducing the type from `CheckpointType` defaults.

## [2.6.2] — 2026-04-30

### Changed
- **`AGENTS.md`** — re-synced with `SKILL.md` per `CLAUDE.md`. Trimmed the "Where to find docs" intro paragraph to match `SKILL.md`'s shorter form (removed the "Do not read any file under `references/`..." sentence and the "'I have a local copy' is not a reason..." closing line).

## [2.6.1] — 2026-04-28

### Changed
- **`AGENTS.md`** — re-synced with `SKILL.md` per `CLAUDE.md`. Added `## Usage` heading and reordered "For building" before "For documentation questions"; expanded the description's agent framework list to include Claude/OpenAI agents SDKs and "snapshots / checkpoints"; updated Quick Start with explicit defaults, `cpus/memory_mb/timeout_secs` args, named-sandbox example, and `result.stdout/stderr/exit_code` note; dropped "direct the user to" wording from the API key paragraph; removed "Orchestration for durable workflow coordination" from the Agentic + Sandbox bullet; reordered DAG composition before LLM integration; removed `tl secrets ls` from CLI Commands and switched `Dockerfile` → `./Dockerfile`.

## [2.6.0] — 2026-04-28

### Changed (Core Patterns — sandbox capabilities promoted to first-class)
- **`SKILL.md`, `AGENTS.md`** — split Core Patterns into `### Sandboxes` and `### Orchestration` sub-sections. Sandboxes now has 8 bullets: agentic+sandbox framing, persistent named sandboxes, snapshots (restore + parallel forks), LLM code-execution tool, interactive PTY shells, computer use / desktop automation, public URLs / port exposure, and custom sandbox images. Orchestration kept at 3 bullets. Every bullet links to the relevant `references/` anchor for verifiability.
- **`SKILL.md`, `AGENTS.md`** — `AGENTS.md` Quick Start switched from an orchestration-first `@application` example to a sandbox-first `Sandbox.create()` example to mirror `SKILL.md`. Added a one-line TypeScript / CLI pointer at the bottom of Quick Start in both files.
- **`SKILL.md`, `AGENTS.md`** — `## Key Rules` renamed to `## Orchestration Key Rules` and trimmed from 8 rules to 3 (decorators, reduce signature, secrets). The dropped rules were first-touch info already documented in `references/applications_sdk.md`, not gotcha-level facts that earn top-level skill prominence.
- **`SKILL.md`** — frontmatter `description` dropped the parenthetical "(parallel map/reduce DAGs via `@application` / `@function`)". No other capability phrase names SDK symbols, so the decorators read as outliers without earning extra trigger signal.
- **`SKILL.md`, `AGENTS.md`** — Setup section dropped the "Provider keys" bullet entirely. The `secrets=[...]` declaration pattern remains in Orchestration Key Rules; the "never inline keys" rule remains in the next-paragraph guidance.
- **`README.md`** — added 4 use-case bullets surfacing the now-first-class sandbox capabilities: interactive shell sessions, sandboxed Linux desktop (computer use), public URL port exposure, snapshot forks for parallel batch work.

### Fixed
- **`SKILL.md`** — split a collapsed API Reference bullet that had `Sandbox Advanced` and `Orchestration SDK` running together on one line.

### Why
The Core Patterns section had grown sandbox-light: PTY, computer use, port exposure, custom images, and snapshot-fork were all triggers named in the frontmatter description but invisible at the Core Patterns level. Promoting them surfaces capabilities an agent would otherwise miss while reading `SKILL.md`, and the per-bullet reference links make each claim verifiable. Renaming Key Rules → Orchestration Key Rules makes the file's now-sandbox-first orientation honest — these rules were never general, they were always orchestration-specific. `AGENTS.md` had also drifted significantly from `SKILL.md`; this commit re-syncs them per `CLAUDE.md`.

## [2.5.5] — 2026-04-28

### Changed (Eval harness — skill-trigger detection)
- **`evals/run.py`** — switched `claude -p` to `--output-format stream-json --verbose` and added `detect_skill_trigger()` / `extract_final_text()`. Each run now writes `stream.jsonl`, `output.md`, and `trigger.json` (`{"skill_triggered": bool, "skill_invocations": [...]}`).
- **`evals/grade.py`** — reads `trigger.json` first; if the skill didn't trigger, the judge LLM call is skipped and all expectations are recorded as failed with reason `"skill not triggered; grading skipped"`. Adds `skill_triggered`, `skill_invocations`, and aggregate `skill_trigger_rate` to `benchmark.json`.
- **`evals/ci_summary.py`** — added a `Skill triggered` column to the per-eval table (with `_(skipped)_` annotation when the judge was bypassed) and a new `## Skill trigger rate` section with the overall rate and per-eval invocation list.

### Why
Eval pass-rate alone conflates "skill didn't fire" with "skill fired but answered wrong" — two very different failure modes. Surfacing trigger detection as a first-class signal makes regressions in the description/trigger criteria visible immediately, and short-circuiting the judge on no-trigger runs saves the cost of grading a response that was never going to consult the skill.

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
