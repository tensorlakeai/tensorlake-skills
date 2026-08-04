# Tensorlake offline reference index

Bundled offline equivalent of [docs.tensorlake.ai/llms.txt](https://docs.tensorlake.ai/llms.txt). Each entry routes to the relevant section of a snapshot file in this directory. Use when network access to `docs.tensorlake.ai` is unavailable; otherwise prefer the live docs (snapshots may lag).

## Sandboxes

### Core

- [SDK Reference](sandbox_sdk.md) — `Sandbox` handle and `SandboxClient`: every method, parameter, and data model
- [Lifecycle](sandbox_persistence.md) — states, creation, suspend/resume, idle auto-suspend, ephemeral vs named, cleanup, limitations
- [Snapshots & forking](sandbox_persistence.md#snapshot-types--filesystem-default-vs-memory) — `checkpoint()`, filesystem vs memory snapshot types, resource overrides at restore, forking N parallel sandboxes
- [Copy / clone a sandbox](sandbox_persistence.md#copy-a-sandbox) — `tl sbx copy` warm-start clones from a running or suspended source, fan-out with `-n`, naming and partial-failure rules
- [Sandbox pools](sandbox_persistence.md#sandbox-pools) — pre-warmed container pools for near-instant startup, `Sandbox.create(pool_id=...)`, pool CRUD on `SandboxClient`
- [Execute commands](sandbox_sdk.md#run-a-command) — `sandbox.run`, output capture, streaming, error handling
- [Default user & working directory](sandbox_sdk.md#default-user-and-working-directory) — the `tl-user` account, why `/workspace` writes can fail, and how to fix it
- [File operations](sandbox_sdk.md#file-operations) — read, write, list, delete, `tl sbx cp`
- [Process management](sandbox_sdk.md#background-processes) — start, monitor, signal, follow background processes; [managed processes](sandbox_sdk.md#managed-processes) with restart policies and health checks
- [Retained process logs](sandbox_sdk.md#retained-process-logs) — `sandbox.get_logs()`, `tl sbx logs`, structured JSON logs, Console Logs tab
- [PTY / interactive shells](sandbox_sdk.md#pty-sessions) — long-lived terminal sessions, resize, reconnect via session id + token, raw WebSocket frame protocol
- [Async SDK (Python)](sandbox_sdk.md#async-sdk-python) — `AsyncSandbox` with `asyncio.gather` fan-out, async context manager, mirrors every sync method
- [Environment variables](sandbox_sdk.md#environment-variables) — per-command, per-process, and per-PTY env
- [Networking, egress, port exposure](sandbox_sdk.md#networking) — egress allow/deny lists, full-deny mode, public URLs (authenticated or unauthenticated), serving webapps from a sandbox
- [Local tunnels](sandbox_sdk.md#local-tunnels) — forward a local TCP port into a sandbox over an authenticated WebSocket; required for non-HTTP protocols (VNC, Postgres, Redis, custom binary)
- [Tensorlake managed images](sandbox_sdk.md#tensorlake-managed-images) — `ubuntu-minimal`, `ubuntu-systemd`, `debian-minimal`, `ubuntu-vnc`; PEP 668 Python
- [Build & import images](sandbox_sdk.md#sandbox-images) — build and register named images (Python / TypeScript / Dockerfile), import a registry image as-is, `--docker_compat`, list/describe
- [OCI base images](sandbox_sdk.md#define-an-image) — build from any standard OCI reference (`python:3.12-slim`, `node:22-alpine`, `ghcr.io/...`); private-registry auth via `~/.docker/config.json`
- [Computer use / desktop automation](computer_use.md) — XFCE + Firefox, screenshots, mouse/keyboard, noVNC live view
- [Drive Chrome over CDP](sandbox_usecases.md#drive-chrome-over-cdp) — sandboxed Chrome with `--remote-debugging-port`, Playwright `connect_over_cdp`, raw CDP WebSocket, `chrome-devtools-mcp` for Claude Code / Codex
- [SSH access](sandbox_sdk.md#ssh) — `ssh`/`scp`/`sftp`/`rsync`, port forwarding (`-L` / `-D` / `-R` / UNIX sockets), VS Code Remote-SSH and JetBrains Gateway
- [Run Docker](sandbox_sdk.md#running-docker-inside-a-sandbox) — Docker-in-sandbox on `tensorlake/ubuntu-systemd`
- [CLI quick reference](sandbox_sdk.md#cli-quick-reference) — every `tl` / `tl sbx` verb in one block

### Use cases

- [Skills in sandboxes](sandbox_usecases.md#skills-in-sandboxes) — bundling Claude Code, Codex, Cursor, Cline, Windsurf, GitHub Copilot, Google ADK skills inside images
- [Tool calls / sandbox-as-tool](sandbox_usecases.md#ai-code-execution) — LLM code-execution tool, executing untrusted/LLM-generated code with network policy
- [Claude managed agents](sandbox_usecases.md#claude-managed-agents) — Anthropic runs the loop, sandboxes run the tools; orchestrator modes, recreate-vs-resume, per-command env injection
- [OpenCode](sandbox_usecases.md#opencode) — `tensorlake-opencode` plugin routes the agent's file/shell tools into a sandbox; lazy creation, env-var config
- [Crabbox](sandbox_usecases.md#crabbox-test-suites) — run your test suite in a Firecracker microVM; `tl-crabbox` image, `.crabbox.yaml`, workdir pitfalls
- [Devin Outposts](sandbox_usecases.md#devin-outposts) — serve Devin sessions on sandboxes you own; orchestrator-in-sandbox, credential model, cron keep-alive
- [Sandbox as a dev environment](sandbox_usecases.md#sandbox-as-a-dev-environment) — portable cloud workstation with idle-suspend, resume-by-name, persistent `~/.vscode-server`
- [Agentic swarm intelligence](sandbox_usecases.md#agentic-swarm-intelligence) — fan-out parallel specialist agents
- [Agentic Dungeons & Dragons](sandbox_usecases.md#agentic-dungeons--dragons) — branch→map→reduce multi-agent demo running untrusted dice scripts in isolated sandboxes
- [Agentic autoresearch loop](sandbox_usecases.md#agentic-autoresearch-loop) — overnight ML script self-improvement with parallel sandbox races
- [RL reproducible environments](sandbox_usecases.md#rl-reproducible-environments) — deterministic isolated rollouts
- [RL training (GSPO)](sandbox_usecases.md#rl-training-with-gspo) — fine-tune on code generation with a sandbox reward oracle
- [CI/CD & build systems](sandbox_usecases.md#cicd-build-pipelines) — isolated reproducible build/test pipelines
- [Data analysis](sandbox_usecases.md#data-analysis) — parallel data analysis, model benchmarking
- [Harbor (evals + RL rollouts)](sandbox_usecases.md#harbor-evals--rl-rollouts) — Terminal-Bench 2.1 / SWE-Bench / Aider Polyglot evals and RL rollouts with `harbor[tensorlake]`, per-trial sandboxes, image caching, `task.toml` tuning

## Cloud Volumes & Git Repositories

- [Overview and how to choose](volumes_and_git.md) — shared linear timeline (volumes) vs private-until-promoted branches (Git)
- [Cloud Volumes quickstart](volumes_and_git.md#quickstart) — `tl fs create` / `mount` / `snapshot`, `FilesystemClient`
- [Mount modes](volumes_and_git.md#mount-modes) — writable, read-only following, read-only pinned
- [Autosave, snapshots, retention](volumes_and_git.md#autosave-snapshots-and-retention) — replication timing, permanent vs ephemeral points, the 256/24h window
- [Session management](volumes_and_git.md#session-management) — status, history, resume, restore/time-travel, `tl fs doctor`, delete
- [Push without mounting](volumes_and_git.md#push-a-folder-without-mounting) — `tl fs push` for CI and release services
- [Concurrent writes](volumes_and_git.md#concurrent-writes) — disjoint paths merge, same-path is last-writer-wins
- [Mounting volumes in sandboxes](volumes_and_git.md#mounting-inside-a-sandbox) — `tl fs token` scoped guest credential
- [Distribute files to agent fleets](volumes_and_git.md#distributing-files-to-agent-fleets) — versioned read-only skills, manuals, configs, binary tools
- [Git repositories](volumes_and_git.md#git-repositories) — managed Git at agent scale, plain `git clone`/`push`
- [Git or the tl CLI?](volumes_and_git.md#git-or-the-tl-cli) — one-rule guide plus the verb mapping
- [Git credentials & scopes](volumes_and_git.md#authentication-and-credentials) — `tl git token`, username `t`, one-hour lifetime, scope table
- [Repository mounts](volumes_and_git.md#repository-mounts) — writable workspaces, read-only branch/commit/subtree views, reattach, delete
- [Snapshot, promote, rebase](volumes_and_git.md#snapshot-promote-rebase) — deliberate commits, squashed promotion, server-side rebase, `tl git sync`
- [Merging and conflicts](volumes_and_git.md#merging-and-conflicts) — preflight, `--deep`, `--materialize`, diff3 markers, conflict-kind table
- [Workspace observability & retention](volumes_and_git.md#workspace-observability-and-retention) — `tl git workspaces`, `smartlog`, liveness, 48h/14d collection
- [Repository SDKs](volumes_and_git.md#repository-sdks) — `RepositoryClient`: create, list, fork, archive, refs, `push_worktree`, `merge`, conflict records
- [Architecture](volumes_and_git.md#architecture-notes) — metadata/content split, two engines with one mount client, lazy content delivery

## Orchestration (Applications SDK)

- [SDK Reference](applications_sdk.md) — functions, applications, decorators, request context, lifecycle
- [Programming agents](troubleshooting.md#agent-programming-patterns) — single-function loops, sandboxed tool functions, harness pattern, framework snippets
- [Architecture](troubleshooting.md#application-runtime-architecture) — how the Application Runtime executes code, schedulers, dataplanes, allocations
- [Orchestration + Sandboxes](applications_sdk.md#sandboxes-and-orchestration) — agent-in-sandbox vs sandbox-as-tool integration patterns
- [Futures](applications_sdk.md#future-api) — `.future()`, parallel calls, `Future.wait`, tail calls
- [Map-reduce](applications_sdk.md#map--reduce) — `.map()` / `.reduce()` parallel ETL
- [Async functions](applications_sdk.md#async-functions) — Python `async`/`await`
- [Durable execution](applications_sdk.md#durable-execution) — checkpointing, replay API, adaptive vs strict modes, call fingerprinting
- [Retries & rate limits](applications_sdk.md#retries) — LLM rate limits, validation-driven retries, `max_containers` × `concurrency`
- [Error handling](applications_sdk.md#exceptions) — exception propagation, degradation patterns, debugging
- [Timeouts](applications_sdk.md#function) — function timeouts and progress-based reset
- [Public endpoints](applications_sdk.md#public-endpoints) — `allow=["unauthenticated_requests"]`, `HttpBody`, webhook receivers
- [Request headers](applications_sdk.md#requestcontext) — `ctx.headers`, case-insensitive lookups, stripped headers
- [Container images](applications_sdk.md#image-builder) — per-function `Image` API, base image, packages, private base images
- [File type](applications_sdk.md#file-type) — `File` inputs/outputs up to 5 TB
- [Secrets](applications_sdk.md#secrets) — function-level secret injection, `tl secrets`, envelope encryption
- [Scale-out & queuing](applications_sdk.md#scaling) — `warm_containers`, `max_containers`, FIFO queuing, autoscaling
- [Cron scheduler](applications_sdk.md#cron-scheduler) — recurring endpoint invocations, limits, response fields
- [Observability & logging](applications_sdk.md#observability) — tracing, execution timelines, `Logger`, structlog, logs API parameters
- [Progress updates](applications_sdk.md#requestcontext) — `ctx.progress.update()` and the progress polling endpoint
- [Troubleshooting](troubleshooting.md) — timeouts, failed requests, OOM, sandbox pitfalls, debugging across function calls

## Platform

- [Authentication & API keys](platform.md#authentication) — API request auth, key management, rotation
- [Access control](platform.md#access-control) — organizations, projects, role/permission tables, invitations
- [Webhooks](platform.md#webhooks) — configuration, delivery contract, envelope, sandbox/application/request event catalog, Svix signature verification, testing
- [EU endpoints](platform.md#eu-endpoints) — `api.eu.tensorlake.ai`, region pinning
- [Billing](platform.md#billing) — usage-based billing
- [Security & compliance](platform.md#security) — HIPAA, SOC 2 Type II, zero data retention, storage/deletion policies, subprocessors
- [SSO](platform.md#single-sign-on-sso) — OIDC and SAML 2.0 setup, testing, enforcement, bypass users
