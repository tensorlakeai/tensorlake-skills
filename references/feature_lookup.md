# Tensorlake offline reference index

Bundled offline equivalent of [docs.tensorlake.ai/llms.txt](https://docs.tensorlake.ai/llms.txt). Each entry routes to the relevant section of a snapshot file in this directory. Use when network access to `docs.tensorlake.ai` is unavailable; otherwise prefer the live docs (snapshots may lag).

## Sandboxes

### Core

- [SDK Reference](sandbox_sdk.md) — `SandboxClient`, `Sandbox` handle, every method/parameter/data model
- [Lifecycle](sandbox_persistence.md) — states, creation, suspend/resume, idle auto-suspend, ephemeral vs named, cleanup, persistence limitations
- [Snapshots & forking](sandbox_persistence.md#snapshot-types--filesystem-default-vs-memory) — checkpoints, filesystem vs memory snapshot types, resource overrides at restore, forking N parallel sandboxes
- [Execute commands](sandbox_sdk.md) — `sandbox.run`, output capture, streaming, error handling
- [File operations](sandbox_sdk.md) — read, write, upload, download, list
- [Process management](sandbox_sdk.md) — start, monitor, signal, follow background processes
- [PTY / interactive shells](sandbox_sdk.md#interactive-pty-session) — long-lived terminal sessions, resize, reconnect via session id + token, WebSocket I/O
- [Environment variables](sandbox_sdk.md) — per-command and per-PTY env, secrets
- [Networking, egress, port exposure](sandbox_sdk.md#outbound-internet-control) — egress allow/deny lists, full-deny mode, public URLs (authenticated or unauthenticated), serving webapps from a sandbox
- [Sandbox images](sandbox_sdk.md#sandbox-images) — build and register named images with pre-installed deps (Python / TypeScript / Dockerfile)
- [Computer use / desktop automation](computer_use.md) — XFCE + Firefox, screenshots, mouse/keyboard, noVNC live view
- [Skills in sandboxes](sandbox_usecases.md) — bundling Claude Code, Codex, Cursor, Cline, Windsurf, GitHub Copilot, Google ADK skills inside images
- [Run Docker](sandbox_sdk.md) — Docker-in-sandbox

### Use cases

- [Tool calls / sandbox-as-tool](sandbox_usecases.md#ai-code-execution) — LLM code-execution tool, executing untrusted/LLM-generated code with network policy
- [Agentic swarm intelligence](sandbox_usecases.md) — fan-out parallel specialist agents
- [RL training (GSPO)](sandbox_usecases.md) — fine-tune on code generation with sandbox reward oracle
- [RL reproducible environments](sandbox_usecases.md) — deterministic isolated rollouts
- [Agentic autoresearch loop](sandbox_usecases.md) — overnight ML script self-improvement with parallel sandbox races
- [CI/CD & build systems](sandbox_usecases.md) — isolated reproducible build/test pipelines
- [Data analysis](sandbox_usecases.md) — parallel data analysis, model benchmarking

## Orchestration (Applications SDK)

- [SDK Reference](applications_sdk.md) — functions, applications, decorators, request context, lifecycle
- [Programming agents](applications_sdk.md) — core concepts and patterns
- [Architecture](applications_sdk.md) — how the Application Runtime executes code
- [Building workflows](applications_sdk.md) — multi-step DAGs, parallel execution
- [Orchestration + Sandboxes](applications_sdk.md) — agent-in-sandbox vs sandbox-as-tool integration patterns
- [Futures](applications_sdk.md#future-api) — `.future()`, run multiple function calls in parallel
- [Map-reduce](applications_sdk.md#map--reduce) — `.map()` / `.reduce()` parallel ETL
- [Parallel sub-agents](applications_sdk.md) — fan out specialist agents
- [Durable execution](applications_sdk.md) — output persistence, retries skip succeeded work
- [Crash recovery](applications_sdk.md) — survive failures and resume without losing work
- [Retries & rate limits](applications_sdk.md) — LLM rate limit and transient failure handling
- [Error handling](applications_sdk.md) — exception propagation, timeouts, resilient patterns
- [Timeouts](applications_sdk.md) — function timeouts and progress-based reset
- [Async functions](applications_sdk.md) — Python `async`/`await`
- [Container images](applications_sdk.md) — per-function `Image` API, base image, packages
- [Secrets](applications_sdk.md) — function-level secret injection
- [Autoscaling](applications_sdk.md) — scaling Orchestration endpoints
- [Scale-out & queuing](applications_sdk.md) — automatic scaling per function
- [Cron scheduler](applications_sdk.md) — recurring endpoint invocations
- [Observability](applications_sdk.md) — tracing, execution timelines, monitoring
- [Streaming progress](applications_sdk.md) — real-time progress updates from functions
- [Logging](applications_sdk.md) — `print`, application logger, structlog JSON logs
- [Troubleshooting](troubleshooting.md) — debugging across function calls, OOM, common errors, production patterns

## Platform

- [Authentication & API keys](platform.md) — API request auth, key management
- [Access control](platform.md) — RBAC, project membership, SSO
- [Webhooks](platform.md) — configuration, signature verification, payloads, testing
- [EU data residency](platform.md)
- [Billing](platform.md)
- [Security & compliance](platform.md) — HIPAA, SOC 2, zero data retention, playground

## Integrations

- [Integrations overview](integrations.md) — frameworks, vector databases, data platforms
- [LangChain](integrations.md) — agentic workflows with on-demand parsing
- [OpenAI](integrations.md) — Applications and function calling that delegates to Sandbox
- [Anthropic](integrations.md) — Applications integration
- [Multi-agent orchestration](integrations.md)
- [ChromaDB / Qdrant](integrations.md) — vectorstores fed by DocumentAI
- [Databricks](integrations.md)
- [MotherDuck](integrations.md)
