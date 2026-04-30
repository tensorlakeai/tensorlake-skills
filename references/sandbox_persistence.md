<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/snapshots.md
SDK version: tensorlake 0.5.5
Last verified: 2026-04-28
-->

# TensorLake Sandbox Persistence

State-centric reference for keeping sandbox state across time: state machine, ephemeral vs named, snapshots, suspend/resume, and idle auto-suspend.

For creating, connecting to, and running commands in a sandbox, see [sandbox_sdk.md](sandbox_sdk.md).

Snapshot/suspend/resume are instance methods on the `Sandbox` handle; restore is `Sandbox.create(snapshot_id=...)`. `SandboxClient` still ships for management operations such as list/update/port exposure, but it is deprecated in favor of the direct `Sandbox` handle where available.

## Table of Contents

- [State Machine](#state-machine)
- [Ephemeral vs Named](#ephemeral-vs-named)
- [Snapshots](#snapshots)
- [Suspend & Resume](#suspend--resume)
- [Suspend vs Snapshot — When to Use Which](#suspend-vs-snapshot--when-to-use-which)
- [Limitations](#limitations)
- [See Also](#see-also)

## State Machine

Every sandbox moves through the states below. `create` starts the sandbox in `Pending`. From `Running` you can snapshot, suspend (named only), or terminate. `Terminated` is final.

```
     [*]
      │
      ▼
   Pending  ◄── create / restore from snapshot
      │
      ▼
   Running ──────── checkpoint ────────► Snapshotting ──┐
      │ ▲                                               │
      │ └─────────── snapshot complete ─────────────────┘
      │
      │                  (named only: suspend or timeout)
      ├─── suspend / timeout ───► Suspending ───► Suspended
      │                                                │
      │ ◄──────────────── resume ──────────────────────┘
      │                                                │
      ▼ (ephemeral only: timeout; any: terminate)      ▼
  Terminated  ◄────────── terminate  ───────────  Terminated
      │
      ▼
     [*]
```

**Timeout behavior differs by sandbox type:**
- **Named** — timeout triggers a suspend, preserving state for later resume.
- **Ephemeral** — timeout triggers termination (final state).

Ephemeral sandboxes follow the same `create → Pending → Running → Terminated` flow but cannot enter `Suspending`/`Suspended`. Explicit `terminate` works from `Running` for any sandbox.

### State Descriptions

| State            | Meaning                                                                                              | Billable               |
|------------------|------------------------------------------------------------------------------------------------------|------------------------|
| `Pending`        | Sandbox is being scheduled or started.                                                               | Yes                    |
| `Running`        | Sandbox is active and ready for commands, files, or processes.                                       | Yes                    |
| `Snapshotting`   | A snapshot is being created from the running sandbox. Returns to `Running` on completion.            | Yes                    |
| `Suspending`     | Sandbox is being suspended. Triggered by manual suspend or timeout. Named sandboxes only.            | Yes                    |
| `Suspended`      | Paused. Filesystem, memory, and running processes are preserved. Named only.                         | Snapshot storage only  |
| `Terminated`     | Final state. Resources released. Cannot be reversed. Triggered by terminate or ephemeral timeout.    | No                     |

## Ephemeral vs Named

Persistence requires a **named** sandbox. Ephemeral sandboxes cannot be suspended, resumed, or auto-resumed.

|                       | Ephemeral                          | Named                                       |
|-----------------------|------------------------------------|---------------------------------------------|
| Created with          | `Sandbox.create()` (no name)       | `Sandbox.create(name=...)`                  |
| Suspend / Resume      | Not supported — returns an error   | Supported                                   |
| Idle auto-suspend     | Not supported                      | Supported                                   |
| Timeout behavior      | Terminates on timeout              | Suspends on timeout                         |
| Reference by          | ID only                            | ID **or** name                              |
| Use when              | Short-lived, one-off execution     | Multi-step agents, persistent environments  |

An ephemeral sandbox can be promoted to a named sandbox after creation via `SandboxClient().update_sandbox(id, name)` in Python (or the client update helper in TypeScript). After renaming, it becomes eligible for suspend/resume. The CLI equivalent is `tl sbx name <id> <new-name>`.

## Snapshots

Snapshots capture sandbox state into a reusable artifact you can boot a **new** sandbox from. Unlike suspend, snapshots do not pause the original — the sandbox keeps running after the snapshot completes.

Snapshots are independent of sandbox lifecycle — they persist after the source sandbox is terminated. This means you can snapshot an ephemeral sandbox before it terminates and still recover its state later.

> **TL;DR — restore is not uniformly "as-is".** Snapshots come in two types: **filesystem (the default)** and **memory**. Filesystem snapshots **accept `cpus=`, `memory_mb=`, and `disk_mb=` overrides** at `Sandbox.create(snapshot_id=...)` — so booting on bigger hardware than the original sandbox is supported. Memory snapshots lock image, resources, entrypoint, and secrets to the snapshot. Don't tell users they have to rebuild from scratch just to change resources without first checking the snapshot type. See [Snapshot Types](#snapshot-types--filesystem-default-vs-memory) for the full table.

### Snapshot Types — Filesystem (default) vs Memory

Two snapshot types exist; they differ in what they capture and how flexibly you can restore from them.

|                            | Filesystem snapshot (default)                          | Memory snapshot                                                     |
|----------------------------|--------------------------------------------------------|---------------------------------------------------------------------|
| **What it captures**       | Filesystem only                                        | Filesystem **+ memory + running processes** — exact frozen state    |
| **Restore semantics**      | Boot a fresh sandbox onto the captured filesystem      | Warm-restore into the exact in-memory state, processes still running |
| **Resource changes at restore?** | **Yes** — `cpus`, `memory_mb`, `disk_mb` may all be passed to `Sandbox.create(snapshot_id=...)` (`disk_mb` is growth-only); image is locked | **No** — image, resources, entrypoint, and secrets all locked to the snapshot |
| **Use for**                | Reusable starting points, baking dependencies, forking on different hardware | Pause-and-fork an agent mid-execution, debug-after-the-fact         |

**Selecting the type.** The snapshot type is selectable at checkpoint time:

- **Python:** `sandbox.checkpoint(checkpoint_type=CheckpointType.MEMORY)` (or `CheckpointType.FILESYSTEM`, the default). Import via `from tensorlake.sandbox import CheckpointType`.
- **TypeScript:** `sandbox.checkpoint({ checkpointType: "memory" })` (or `"filesystem"`).
- **CLI:** `tl sbx checkpoint <id> --checkpoint-type memory` (or `filesystem`).

Read the type back from `Sandbox.get_snapshot(snapshot_id).snapshot_type` (a `SnapshotType` enum exposed at `tensorlake.sandbox.models.SnapshotType`, with members `MEMORY` and `FILESYSTEM`). Note: `CheckpointType` is what you pass *in* to `checkpoint()`; `SnapshotType` is what you read *out* of `SnapshotInfo` — they're parallel enums with the same members.

### Create a Snapshot

**Python:**

```python
from tensorlake.sandbox import Sandbox, CheckpointType

sandbox = Sandbox.create()
sandbox.run("pip", ["install", "numpy", "pandas", "--user", "--break-system-packages"])

# Filesystem checkpoint (default)
snapshot = sandbox.checkpoint(
    timeout=300,        # float — max seconds to wait for completion (default 300)
    poll_interval=1.0,  # float — seconds between status polls (default 1.0)
    # checkpoint_type=CheckpointType.FILESYSTEM,  # default; pass MEMORY for warm-restore
)                                       # -> SnapshotInfo
print(snapshot.snapshot_id)
# snapshot.status, snapshot.snapshot_type, snapshot.size_bytes

# Memory checkpoint (captures filesystem + memory + processes)
mem_snapshot = sandbox.checkpoint(checkpoint_type=CheckpointType.MEMORY)
```

Pass `wait=False` to fire-and-return — `checkpoint()` then returns `None` instead of waiting for the artifact to commit.

**TypeScript:**

```typescript
const sandbox = await Sandbox.create();
await sandbox.run("pip", {
  args: ["install", "numpy", "pandas", "--user", "--break-system-packages"],
});

// Filesystem (default)
const snapshot = await sandbox.checkpoint();

// Memory checkpoint
const memSnapshot = await sandbox.checkpoint({ checkpointType: "memory" });
console.log(snapshot.snapshotId);
```

**CLI:**

```bash
tl sbx checkpoint <sandbox-id>                              # filesystem (default)
tl sbx checkpoint <sandbox-id> --checkpoint-type memory     # memory checkpoint
tl sbx checkpoint <sandbox-id> --timeout 600
```

**REST:**

```bash
curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id>/snapshot \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### Graceful Stop + Snapshot (long-running process)

When you want to interrupt a running background process and preserve its post-shutdown state for later inspection, the canonical sequence is **SIGTERM → wait for the process to exit → `checkpoint()` → `terminate()`**. SIGTERM gives the program a chance to flush buffers and write its own final partial output; the snapshot then captures that flushed state. Snapshotting *before* the signal captures in-flight memory but misses anything the process would have written on graceful shutdown.

```python
import signal
from tensorlake.sandbox import Sandbox

sandbox = Sandbox.create(name="training-run", cpus=4.0, memory_mb=8192)

proc = sandbox.start_process("python", args=["/workspace/train.py"])

try:
    for event in sandbox.follow_output(proc.pid):
        print(event.line, end="", flush=True)
        # ... decide to interrupt based on what you see ...
except KeyboardInterrupt:
    sandbox.send_signal(proc.pid, signal.SIGTERM)   # 1. graceful — let the process flush
    # (optional) wait briefly for the process to exit, then:
    snapshot = sandbox.checkpoint()                  # 2. capture post-shutdown state
    print(f"Snapshot: {snapshot.snapshot_id}")
    sandbox.terminate()                              # 3. tear down the sandbox

# Later, in a fresh script — restore creates a NEW sandbox with a new sandbox_id
restored = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

This is **snapshot/restore semantics** (new sandbox, new id), not **suspend/resume** (same sandbox, same id). Use suspend/resume when you want *this* sandbox back later; use checkpoint/restore when you want a starting point you can fork into a fresh environment.

> **When answering, surface this distinction explicitly.** If the user's prompt mentions "fresh environment", "clean environment", "new sandbox", "later/separately", "fork", or "inspect/debug after the fact" — call out in prose that `Sandbox.create(snapshot_id=...)` produces a *new* sandbox with a *new* `sandbox_id`, and that this is why it's the right tool over suspend/resume here. Don't conflate "checkpoints" with "suspend semantics" in summary lines — they're different lifecycle concepts and users get confused when they're bundled.

### Restore from a Snapshot

Create a new sandbox from a snapshot. Behavior depends on the snapshot type (see [Snapshot Types](#snapshot-types--filesystem-default-vs-memory) above):

- **Filesystem snapshot (default):** the new sandbox boots onto the captured filesystem. You may pass `cpus=`, `memory_mb=`, and `disk_mb=` to `Sandbox.create(snapshot_id=...)` (or `--cpus`, `--memory`, `--disk_mb` on the CLI) to override resources. `disk_mb` is **growth-only** — range `10240`–`102400` MiB (10–100 GiB). Image is locked to the snapshot.
- **Memory snapshot:** the new sandbox warm-restores filesystem, memory, and running processes **exactly as they were**. Image, resources (CPUs, memory, disk), entrypoint, and secrets all come from the snapshot and cannot be changed at restore time. If you need different resources, create a fresh sandbox instead of restoring.

**Python:**

```python
restored = Sandbox.create(snapshot_id=snapshot.snapshot_id)
result = restored.run("cat", ["/data/output.csv"])
```

**TypeScript:**

```typescript
const restored = await Sandbox.create({ snapshotId: snapshot.snapshotId });
```

**CLI:**

```bash
tl sbx create --snapshot <snapshot-id>
```

**REST:**

```bash
curl -X POST https://api.tensorlake.ai/sandboxes \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id": "<snapshot-id>"}'
```

### Manage Snapshots

**Python:**

```python
info = Sandbox.get_snapshot(snapshot_id)            # -> SnapshotInfo (static)
snapshots = sandbox.list_snapshots()                 # snapshots from this sandbox (instance)
Sandbox.delete_snapshot(snapshot_id)                 # static
```

**TypeScript:**

```typescript
const info = await Sandbox.getSnapshot("snapshot-id");
const snapshots = await sandbox.listSnapshots();
await Sandbox.deleteSnapshot("snapshot-id");
```

**CLI / REST:**

```bash
tl sbx checkpoint ls
tl sbx checkpoint rm <snapshot-id>

curl https://api.tensorlake.ai/snapshots \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"

curl -X DELETE https://api.tensorlake.ai/snapshots/<snapshot-id> \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### Forking from a Snapshot

To fork a running agent's environment, call `sandbox.checkpoint()` and then `Sandbox.create(snapshot_id=...)` to launch one or more forks from that point. Each fork is a fresh sandbox with its own ID; the source sandbox is unaffected.

```python
snapshot = sandbox.checkpoint()
fork_a = Sandbox.create(snapshot_id=snapshot.snapshot_id)
fork_b = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

The intermediate snapshot persists and consumes storage until you delete it with `Sandbox.delete_snapshot(snapshot_id)` (or `tl sbx checkpoint rm <snapshot-id>`).

**CLI shortcut — `tl sbx clone`:** for a one-shot checkpoint-then-restore flow, use:

```bash
tl sbx clone <sandbox-id>
tl sbx clone <sandbox-id> --timeout 600
```

This creates a **memory** checkpoint and immediately warm-restores a new sandbox from it. The intermediate snapshot persists — it shows up in `tl sbx checkpoint ls` and counts toward storage until you delete it. **CLI-only** — there is no equivalent in the Python SDK, TypeScript SDK, or HTTP API. From those, call `checkpoint(checkpoint_type=CheckpointType.MEMORY)` followed by `Sandbox.create(snapshot_id=...)` explicitly.

## Suspend & Resume

Suspend a running **named** sandbox to pause its state in place: filesystem and memory are preserved, and the running container stops so you aren't billed for compute. Resume brings the **same** sandbox back to `Running` exactly where it left off — the `sandbox_id` and name are unchanged. Ephemeral sandboxes cannot be suspended — suspend calls on them return an error.

Suspend and resume are **instance methods** on the `Sandbox` handle. Get a handle via `Sandbox.create(...)` or `Sandbox.connect(...)` first.

**Python:**

```python
sandbox = Sandbox.connect("my-env")
sandbox.suspend()    # pauses the sandbox in place; stops the running container
sandbox.resume()     # brings the same sandbox back to Running
```

**TypeScript:**

```typescript
const sandbox = await Sandbox.connect("my-env");
await sandbox.suspend();
await sandbox.resume();
```

**CLI:**

```bash
tl sbx suspend my-env
tl sbx resume my-env
```

**REST:**

```bash
# Suspend
curl -X POST https://api.tensorlake.ai/sandboxes/{sandbox_id_or_name}/suspend \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
# 202 = suspend initiated, 200 = already suspended

# Resume
curl -X POST https://api.tensorlake.ai/sandboxes/{sandbox_id_or_name}/resume \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
# 202 = resume initiated, 200 = already running
```

**Status codes (both endpoints):** 400 = cannot suspend/resume in current state (or ephemeral), 401 = invalid credentials, 403 = insufficient permissions, 404 = not found.

### Idle Auto-Suspend and Auto-Resume

Named sandboxes can be auto-suspended when they go idle, and most sandbox-proxy traffic automatically resumes a suspended sandbox on the next request.

- **Auto-suspend:** When a named sandbox goes idle, Tensorlake can suspend it automatically, preserving filesystem and memory state without billing for a running container.
- **Auto-resume on request:** Many sandbox-proxy requests (e.g., hitting `https://<port>-<sandbox-id-or-name>.sandbox.tensorlake.ai`) automatically resume a suspended named sandbox and wait for the port to become routable before forwarding the request. Resume typically takes under a second.
- **Ephemeral sandboxes:** Do not auto-suspend and cannot be auto-resumed — they simply terminate when their work ends or their `timeout_secs` elapses.

This pattern lets agents preserve long-lived environments between tasks without paying to keep them running.

## Suspend vs Snapshot — When to Use Which

Both operations persist sandbox state, but they solve different problems:

|                            | Suspend / Resume                                       | Snapshot / Restore                                          |
|----------------------------|--------------------------------------------------------|-------------------------------------------------------------|
| **What it does**           | Pauses the **same** sandbox in place                   | Creates a reusable artifact you boot **new** sandboxes from |
| **Same sandbox ID after?** | Yes — `sandbox_id` and `name` are preserved            | No — restore produces a new sandbox with a new ID           |
| **Run multiple copies?**   | No — one sandbox at a time                             | Yes — fork N sandboxes from one snapshot                    |
| **Requires named sandbox?**| Yes                                                    | No — works on ephemeral too                                 |
| **Auto-triggered?**        | Yes (idle auto-suspend, auto-resume on request)        | No — always explicit                                        |
| **Use for**                | Pausing an agent's environment between tasks; same URL | Checkpoints, forking work, reusable starting states         |

Rule of thumb: **suspend** when you want *this* sandbox back later; **checkpoint** when you want a starting point you can restore, fork, or share.

## Limitations

- **Suspend/resume requires named sandboxes.** Ephemeral sandboxes return an error on suspend. Promote to named first via `SandboxClient().update_sandbox(id, name)` if you need to suspend.
- **Terminated is final.** A terminated sandbox cannot be resumed. Use `sandbox.checkpoint()` beforehand if you need a restore path.
- **Snapshot restore is to a new sandbox.** Restoring does not mutate the original sandbox; it creates a new one with a new `sandbox_id`.
- **Restore semantics depend on snapshot type.** *Memory* snapshots restore as-is — image, resources, entrypoint, and secrets all come from the snapshot and cannot be changed. *Filesystem* snapshots (the default) accept `cpus=`, `memory_mb=`, and `disk_mb=` overrides at restore (`disk_mb` is growth-only); image is still locked. If you need a different image, or you have a memory snapshot and need different resources, create a fresh sandbox instead.

## See Also

- [sandbox_sdk.md](sandbox_sdk.md) — create, connect, run commands, file ops, processes, networking, images
- [sandbox_usecases.md](sandbox_usecases.md) — patterns: skills-in-sandboxes, AI code execution, CI/CD
