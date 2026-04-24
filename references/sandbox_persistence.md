<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/snapshots.md
SDK version: tensorlake 0.5.0
Last verified: 2026-04-24
-->

# TensorLake Sandbox Persistence

State-centric reference for keeping sandbox state across time: state machine, ephemeral vs named, snapshots, suspend/resume, and idle auto-suspend.

For creating, connecting to, and running commands in a sandbox, see [sandbox_sdk.md](sandbox_sdk.md).

> **0.5.0:** snapshot/suspend/resume are instance methods on the `Sandbox` handle; restore is `Sandbox.create(snapshot_id=...)`. `SandboxClient` still ships in `0.5.0` for management operations such as list/update/port exposure, but it is deprecated in favor of the direct `Sandbox` handle where available.

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

Snapshots capture the filesystem, memory, and running processes of a sandbox. Use them to save work mid-session and restore it later in a **new** sandbox. Unlike suspend, snapshots do not pause the original — the sandbox keeps running after the snapshot completes.

Snapshots are independent of sandbox lifecycle — they persist after the source sandbox is terminated. This means you can snapshot an ephemeral sandbox before it terminates and still recover its state later.

### Create a Snapshot

**Python:**

```python
from tensorlake.sandbox import Sandbox

sandbox = Sandbox.create()
sandbox.run("pip", ["install", "numpy", "pandas", "--user", "--break-system-packages"])

snapshot = sandbox.checkpoint()         # SnapshotInfo
print(snapshot.snapshot_id)
# snapshot.status, snapshot.size_bytes
```

**TypeScript:**

```typescript
const sandbox = await Sandbox.create();
await sandbox.run("pip", {
  args: ["install", "numpy", "pandas", "--user", "--break-system-packages"],
});

const snapshot = await sandbox.checkpoint();
console.log(snapshot.snapshotId);
```

**CLI:**

```bash
tl sbx checkpoint <sandbox-id>
tl sbx checkpoint <sandbox-id> --timeout 600
```

**REST:**

```bash
curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id>/snapshot \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### Restore from a Snapshot

Create a new sandbox from a snapshot. The new sandbox restores the captured filesystem, memory, and running processes **exactly as they were** — image, resources (CPUs, memory), entrypoint, and secrets all come from the snapshot and cannot be changed at restore time. If you need different resources, create a fresh sandbox instead of restoring.

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
- **Snapshot restore is as-is.** A restored sandbox inherits image, resources, entrypoint, and secrets from the snapshot — none of these can be changed at restore time. If you need different CPUs, memory, or an updated image, create a fresh sandbox instead.

## See Also

- [sandbox_sdk.md](sandbox_sdk.md) — create, connect, run commands, file ops, processes, networking, images
- [sandbox_advanced.md](sandbox_advanced.md) — patterns: skills-in-sandboxes, AI code execution, CI/CD
