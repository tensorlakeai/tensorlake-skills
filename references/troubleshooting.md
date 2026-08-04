<!--
Source:
  - https://docs.tensorlake.ai/applications/overview.md
  - https://docs.tensorlake.ai/applications/architecture.md
  - https://docs.tensorlake.ai/applications/production/troubleshooting.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Troubleshooting & Architecture Guide

> Earlier versions of this snapshot also covered Document Ingestion production integration and OCR/extraction benchmarks. **Those docs no longer exist** — the Document Ingestion product and its `document-ingestion/*` pages have been removed from the Tensorlake docs. Don't cite parse-job polling, `file_id`/`file_url` parameters, or TEDS/JSON-F1 benchmark numbers.

## Table of Contents

- [Applications — Common Issues](#applications--common-issues)
- [Sandbox — Common Issues](#sandbox--common-issues)
- [Agent Programming Patterns](#agent-programming-patterns)
- [Application Runtime Architecture](#application-runtime-architecture)

## Applications — Common Issues

### Function Timeout

1. **Increase the timeout** — raise `timeout` in the `@function` decorator (default `300`, max `172800`).
2. **Report progress** — `ctx.progress.update()` resets the timeout counter, so a function can run indefinitely while making progress.
3. **Check the logs** — use the Logs API to see what the function was doing before it timed out.

### Request Failed

1. **Check request state** — the full state includes the failure reason:

```bash
curl -X GET "https://api.tensorlake.ai/applications/{application}/requests/{request_id}" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

`outcome` is `success` or `failure`, and `null` while the request is still in progress. `failure_reason` and `request_error` carry the detail.

2. **Review logs filtered by request ID:**

```bash
curl -X GET "https://api.tensorlake.ai/applications/{application}/logs?requestId={request_id}" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

3. **Replay it** once fixed — `POST /applications/{app}/requests/{request_id}/replay` re-runs the same request ID and skips already-successful calls. See [applications_sdk.md](applications_sdk.md#durable-execution).

### Out of Memory

1. **Check current allocation** — review `memory` in the `@function` decorator (default `1.0` GB).
2. **Increase memory** — up to 32 GB.
3. **Process in batches** — break large datasets into smaller chunks.

Guidance from the docs: set `memory` to **at least 2× the size of the largest input or output**, because both serialized and deserialized representations are held in memory at once. For multi-gigabyte inputs/outputs also raise `cpu` to **at least 3** for the fastest transfer speeds.

### Debugging Tips

- Add `print()` statements to log intermediate values (stdout is captured automatically at level `INFO`).
- Use `ctx.request_id` to correlate logs across function calls.
- Verify CPU, memory, and ephemeral-disk allocations are adequate.
- Review retry settings if functions fail intermittently.
- **Reproduce locally** — applications run as ordinary Python via `run_local_application`.
- Make side effects idempotent, since functions can retry.

## Sandbox — Common Issues

| Symptom | Cause / fix |
|---|---|
| `Permission denied` writing to `/workspace` | Managed `tensorlake/*` images run as `tl-user`, and `/workspace` is root-owned. Use `/home/tl-user/...`, pass `--user root`, or `sudo chown tl-user:tl-user /workspace`. See [sandbox_sdk.md](sandbox_sdk.md#default-user-and-working-directory). |
| A relative command like `touch output.txt` fails | Non-interactive commands start from `/`. Pass `working_dir` / `--workdir`. |
| `externally-managed-environment` from `pip` | The images ship a PEP 668-managed system Python. Use `--break-system-packages` or a venv — **do not** switch to an alternate Python version, which produces the same error. |
| `result.returncode` raises `AttributeError` | The Python field is `exit_code`, not `returncode`. |
| Sandbox suspended unexpectedly | `timeout_secs` is an **idle** threshold. Named sandboxes suspend on timeout; ephemeral ones terminate. |
| `suspend` returns `400` | Suspend requires a **named** sandbox. Promote with `sandbox.update(name=...)`. |
| Tunnel: `Connection refused` locally | The remote service isn't listening yet — check `tl sbx exec <id> -- bash -lc 'ss -ltnp'`. |
| Tunnel/proxy: `502 Bad Gateway` | The workload hasn't finished booting; nothing is listening on the remote port yet. |
| `tl sbx ssh keys` fails | It requires user-level auth. `TENSORLAKE_API_KEY` takes precedence over `tl login` — unset it for the registration step. |
| `Permission denied (publickey)` over SSH | Client offered an unregistered key. Constrain with `IdentitiesOnly yes` + `IdentityFile`. |
| Exposed port unreachable | The port must be listed in `exposed_ports`; `allow_unauthenticated_access` alone does not expose it. |
| Empty sandbox Logs tab | Confirm a process wrote to stdout/stderr, that you're on the right project and sandbox, and allow a moment for ingestion. |
| Pool delete fails with `409` / `PoolInUseError` | Sandboxes claimed from the pool are still active. Terminate them, or `force=true` over HTTP. |

## Agent Programming Patterns

Tensorlake is a **compute platform for agents** — it runs your agents, it doesn't replace your agent framework. You bring the agent logic (OpenAI Agents SDK, LangGraph, Claude Agent SDK, or plain Python); Tensorlake provides serverless containers, durable execution, sandboxes, and observability.

### Agent loop in a single function

The simplest pattern: the whole agent loop runs inside one `@function()`. Works well for agents that run a single loop with tool calls, don't fan out to other agents, and have predictable resource requirements.

```python
@application()
@function(timeout=3600)
def research_agent(topic: str) -> str:
    from agents import Agent, Runner, WebSearchTool

    agent = Agent(name="ResearchAgent",
                  instructions="Thoroughly research the given topic using web search.",
                  tools=[WebSearchTool()])
    return Runner.run_sync(agent, topic).final_output
```

### Sandboxing functions

When tools have different resource needs (CPU, memory, GPU, dependencies), wrap each tool in its own `@function()`. Each runs in its own container with its own dependencies and limits, is independently retryable and durable, and scales independently.

```python
heavy_image = Image().run("pip install torch transformers")

@function(image=heavy_image, memory=8, gpu="T4")
def classify_image(image_url: str) -> str: ...

@function()
def search_web(query: str) -> list[str]: ...

@application()
@function(timeout=1800)
def research_agent(topic: str) -> dict:
    return {"image": classify_image(url), "web": search_web(topic)}
```

### Harness pattern — agent as orchestrator

Separate the **harness** (orchestration logic, lightweight) from the **work** (tool execution, heavy). A lightweight orchestrator can dispatch to GPU-equipped containers without needing GPU resources itself.

### Parallel sub-agents

Fan out specialist agents with futures or async functions:

```python
@application()
@function()
def analyze_proposal(text: str) -> dict:
    financial = financial_agent.future(text)
    legal = legal_agent.future(text)
    technical = technical_agent.future(text)
    return synthesize.future(financial, legal, technical)   # tail call
```

### Framework snippets

The docs give runnable shapes for the **OpenAI Agents SDK** (`agents.Agent` + `Runner.run_sync`), **LangGraph** (`create_react_agent` with `Image().run("pip install langgraph langchain-openai")`), and the **Claude Agent SDK** (`claude_agent_sdk.query` with `ClaudeAgentOptions`, run via `asyncio.run`, `ephemeral_disk=4`, `cwd="/tmp/workspace"`). In every case the framework import happens **inside** the function body.

## Application Runtime Architecture

> Advanced topic — you do not need this to use Tensorlake effectively.

When a request hits your application the runtime creates a new sandbox in milliseconds and your agent starts in an isolated environment with its own filesystem. Every `@function()` can run in its own remote sandbox with dedicated resources; from your code it looks like a normal function call.

**Server (control plane).** Receives requests from clients and the SDK, persists all state to a durable store, and runs two schedulers. On arrival it creates a **request context** — a persisted record tracking the function call graph, all function runs, and the final outcome.

- **Application scheduler** — manages function-call lifecycle: builds the execution graph per request, creates allocations, checkpoints outputs, handles replay on failure.
- **Container scheduler** — manages infrastructure: tracks resources across dataplanes, places containers on worker nodes, manages warm pools, scales up and down on demand.

**Dataplane.** Manages containers on a pool of worker nodes — effectively a regional cluster of compute. Multiple dataplanes run in parallel and the server distributes work across them. Each maintains a **bidirectional gRPC stream** for desired state plus a **heartbeat every 5 seconds** reporting running containers, resource usage, and allocation results. Results are buffered and large payloads are fragmented across heartbeats (**10 MB limit per message**), removed from the buffer only after the server acknowledges receipt. Disconnections self-heal: the stream reconnects, heartbeats use exponential backoff, and the next successful sync reconciles drift.

**Language runtime.** The sandbox that runs your code. Each allocation moves through three phases:

1. **Preparing** — download input data, presign blob URLs for outputs. **Does not occupy a concurrency slot**, so a container can prepare allocations in parallel while running others.
2. **Running** — execute the function, streaming progress updates, output blob requests, child function calls, and the final result back to the dataplane controller. For **blocking calls** the runtime registers a watcher and pauses until the child's result arrives from the server.
3. **Finalizing** — complete multipart uploads, clean up blob handles, release the concurrency slot.

`max_concurrency` limits how many allocations one runtime executes simultaneously in the running phase; when all slots are full the application scheduler queues the work or requests a new container.

**Execution model.** Request → **function call** (a node in the execution DAG) → **function run** (an execution instance tracking pending/running/completed plus the checkpointed output) → **allocation** (a unit of work binding a run to a specific container). When a function calls another function, the language runtime reports the child call to the server, which adds a node and creates a run — **the DAG grows dynamically as your code executes**. Completed run outputs are checkpointed to **object storage, not the database**, so agents can pass large files between functions without workarounds.

**Placement and scaling.** The container scheduler keeps a real-time view of every executor's total and free CPU/memory/GPU and every container on it, grouped into per-function **container pools** with configurable minimums, maximums, and buffer sizes. It first tries to claim a **warm container** from the function's pool, avoiding cold start entirely. Otherwise the **placement engine** finds a candidate executor satisfying resource requirements and constraints; if none has room, a **vacuum pass** evicts lower-priority containers — first those above the pool's buffer count, then those above the minimum, and only as a last resort those at or below it. **Containers with active allocations are never evicted.** Functions with no traffic have no running containers and incur no cost.

**Desired state model.** Rather than imperative commands, the scheduler declares each container's desired state (running or terminated) and the dataplane reconciles toward it — so a lost message is corrected on the next reconciliation cycle.

**Replay** walks the function call graph from the beginning: runs with checkpointed outputs return instantly without re-executing, fast-forwarding through completed work until the failed function, which runs again from scratch. **Retries** handle individual function failures (exception, container crash, or timeout) by creating a new allocation with the same inputs, subject to the function's retry policy.

**Why a custom scheduler instead of Kubernetes.** Tensorlake creates a fresh sandbox per request in single-digit milliseconds, hundreds per second at peak; a Kubernetes pod involves etcd writes, admission controllers, kubelet sync, and image pulls — seconds at best, and pod-per-request would overwhelm the control plane. Beyond speed, the container scheduler is tightly coupled to the application scheduler in ways a general-purpose orchestrator isn't: function-level warm pools and buffers, an eviction algorithm that knows which containers hold active allocations, and per-function container affinity that routes work to dataplanes with warm containers. Kubernetes' watch/list model over etcd also adds latency when the scheduling loop must react in milliseconds. Operationally, Tensorlake collapses YAMLs, HPAs, image pull policies, KEDA/Knative scale-to-zero, and a separate durable-execution server into one runtime.

## See Also

- [applications_sdk.md](applications_sdk.md) — decorators, futures, durability, retries, scaling, logs API
- [sandbox_sdk.md](sandbox_sdk.md) — sandbox creation, commands, files, processes, logs, networking, images
- [sandbox_persistence.md](sandbox_persistence.md) — lifecycle, snapshots, copy, pools
- [volumes_and_git.md](volumes_and_git.md) — Cloud Volumes and Git repositories
- [platform.md](platform.md) — auth, access control, lifecycle webhooks, EU endpoints, security, SSO
