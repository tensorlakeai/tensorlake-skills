<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/snapshots.md
SDK version: tensorlake 0.4.44
Last verified: 2026-04-12
-->

# TensorLake Sandbox Persistence

State-centric reference for keeping sandbox state across time: state machine, ephemeral vs named, snapshots, clone, suspend/resume, and idle auto-suspend.

For creating, connecting to, and running commands in a sandbox, see [sandbox_sdk.md](sandbox_sdk.md).

## State Machine

Every sandbox moves through the states below. `create` starts the sandbox in `Pending`. From `Running` you can snapshot, suspend (named only), or terminate. `Terminated` is final.

```
     [*]
      │
      ▼
   Pending  ◄── create / restore from snapshot
      │
      ▼
   Running ──────── snapshot ────────► Snapshotting ──┐
      │ ▲                                             │
      │ └─────────── snapshot complete ───────────────┘
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

| State | Meaning | Billable |
|---|---|---|
| `Pending` | Sandbox is being scheduled or started. | Yes |
| `Running` | Sandbox is active and ready for commands, files, or processes. | Yes |
| `Snapshotting` | A snapshot is being created from the running sandbox. Sandbox returns to `Running` on completion. | Yes |
| `Suspending` | Sandbox is being suspended — state is snapshotted for later resume. Triggered by manual suspend or timeout. Named sandboxes only. | Yes |
| `Suspended` | Paused. Filesystem and memory are preserved. Named sandboxes only. | Snapshot storage only |
| `Terminated` | Final state. Resources released. Cannot be reversed. Triggered by explicit terminate (any sandbox) or timeout (ephemeral only). | No |

## Ephemeral vs Named

Persistence requires a **named** sandbox. Ephemeral sandboxes cannot be suspended, resumed, or auto-resumed.

| | Ephemeral | Named |
|---|---|---|
| Created with | `client.create()` (no name) | `client.create(name=...)` |
| Suspend / Resume | Not supported — returns an error | Supported |
| Idle auto-suspend | Not supported | Supported |
| Timeout behavior | Terminates on timeout | Suspends on timeout |
| Reference by | ID only | ID **or** name |
| Use when | Short-lived, one-off execution | Multi-step agents, persistent environments |

An ephemeral sandbox can be promoted to a named sandbox after creation via `client.update_sandbox(id, new_name)` (Python) / `client.update(id, { name })` (TypeScript). After renaming, it becomes eligible for suspend/resume.

## Snapshots

Snapshots capture the filesystem and memory state of a running sandbox. Use them to save work mid-session and restore it later in a **new** sandbox. Unlike suspend, snapshots do not pause the original — the sandbox keeps running after the snapshot completes.

Snapshots are independent of sandbox lifecycle — they persist after the source sandbox is terminated. This means you can snapshot an ephemeral sandbox before it terminates and still recover its state later.

### Create a Snapshot

**Python:**

```python
snapshot = client.snapshot_and_wait(
    sandbox_id,
    timeout=300,          # max seconds to wait for completion
    poll_interval=1.0,    # seconds between status polls
)
print(snapshot.snapshot_id)
# snapshot.status.value, snapshot.size_bytes
```

**TypeScript:**

```typescript
const snapshot = await client.snapshotAndWait(sandbox.sandboxId);
console.log(snapshot.snapshotId);
```

**CLI:**

```bash
tl sbx snapshot <sandbox-id>
tl sbx snapshot <sandbox-id> --timeout 600
```

**REST:**

```bash
curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id>/snapshot \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### Restore from a Snapshot

Create a new sandbox from a snapshot. The new sandbox restores the captured filesystem and memory state **exactly as it was** — image, resources (CPUs, memory), entrypoint, and secrets all come from the snapshot and cannot be changed at restore time. If you need different resources, create a fresh sandbox instead of restoring.

**Python:**

```python
restored = client.create_and_connect(snapshot_id=snapshot.snapshot_id)
```

**TypeScript:**

```typescript
const restored = await client.createAndConnect({
  snapshotId: snapshot.snapshotId,
});
```

**CLI:**

```bash
tl sbx new --snapshot <snapshot-id>
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
info = client.get_snapshot(snapshot_id)          # -> SnapshotInfo
snapshots = client.list_snapshots()               # -> list[SnapshotInfo]
client.delete_snapshot(snapshot_id)
```

**TypeScript:**

```typescript
const info = await client.getSnapshot("snapshot-id");
const snapshots = await client.listSnapshots();
await client.deleteSnapshot("snapshot-id");
```

**CLI / REST:**

```bash
tl sbx snapshot ls
tl sbx snapshot rm <snapshot-id>

curl https://api.tensorlake.ai/snapshots \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"

curl -X DELETE https://api.tensorlake.ai/snapshots/<snapshot-id> \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### `snapshot_and_wait` Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sandbox_id` | `str` | — | ID of the running sandbox to snapshot |
| `timeout` | `float` | `300` | Max seconds to wait for completion |
| `poll_interval` | `float` | `1.0` | Seconds between status polls |

## Clone

`tl sbx clone` is a one-shot snapshot + restore. It creates a snapshot of a running sandbox and immediately boots a new sandbox from it — useful when an agent has reached an interesting intermediate state and you want to fork or debug it without touching the original.

```bash
tl sbx clone <sandbox-id>
tl sbx clone <sandbox-id> --timeout 600
```

**Availability:** CLI only. Not exposed in the Python SDK, TypeScript SDK, or HTTP API. For programmatic forking, call `snapshot_and_wait()` followed by `create_and_connect(snapshot_id=...)` explicitly.

## Suspend & Resume

Suspend a running **named** sandbox to pause its state in place: filesystem and memory are preserved, and the running container stops so you aren't billed for compute. Resume brings the **same** sandbox back to `Running` exactly where it left off — the `sandbox_id` and name are unchanged, and you're resuming the suspended sandbox itself, not restoring from a snapshot into a new sandbox. Ephemeral sandboxes cannot be suspended — suspend calls on them return an error.

Both operations accept either the sandbox name or the sandbox ID.

**Python:**

```python
client.suspend("my-env")   # Pauses the sandbox in place; stops the running container
client.resume("my-env")    # Brings the same sandbox back to Running
```

**TypeScript:**

```typescript
await client.suspend("my-env");
await client.resume("my-env");
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
- **Auto-resume on request:** Many sandbox-proxy requests (e.g., hitting `https://<port>-<sandbox-id>.sandbox.tensorlake.ai`) automatically resume a suspended named sandbox and wait for the port to become routable before forwarding the request. Resume typically takes under a second.
- **Ephemeral sandboxes:** Do not auto-suspend and cannot be auto-resumed — they simply terminate when their work ends or their `timeout_secs` elapses.

This pattern lets agents preserve long-lived environments between tasks without paying to keep them running.

## Suspend vs Snapshot — When to Use Which

Both operations persist sandbox state, but they solve different problems:

| | Suspend / Resume | Snapshot / Restore |
|---|---|---|
| **What it does** | Pauses the **same** sandbox in place | Creates a reusable artifact you boot **new** sandboxes from |
| **Same sandbox ID after?** | Yes — `sandbox_id` and `name` are preserved | No — restore produces a new sandbox with a new ID |
| **Run multiple copies?** | No — one sandbox at a time | Yes — fork N sandboxes from one snapshot |
| **Requires named sandbox?** | Yes | No — works on ephemeral too |
| **Auto-triggered?** | Yes (idle auto-suspend, auto-resume on request) | No — always explicit |
| **Use for** | Pausing an agent's environment between tasks; keeping the same URL/identity | Checkpoints, forking work, reusable starting states, handing off state to a new sandbox |

Rule of thumb: **suspend** when you want *this* sandbox back later; **snapshot** when you want a starting point you can restore, fork, or share.

## Limitations

- **Suspend/resume requires named sandboxes.** Ephemeral sandboxes return an error on suspend. Rename first via `update_sandbox` / `update` if you need to suspend.
- **Terminated is final.** A terminated sandbox cannot be resumed. Use snapshots beforehand if you need a restore path.
- **Clone is CLI-only.** Python SDK, TypeScript SDK, and HTTP API do not expose a one-shot clone. Use `snapshot_and_wait` + `create_and_connect(snapshot_id=...)` instead.
- **Snapshot restore is to a new sandbox.** Restoring does not mutate the original sandbox; it creates a new one with a new `sandbox_id`.
- **Snapshot restore is as-is.** A restored sandbox inherits image, resources, entrypoint, and secrets from the snapshot — none of these can be changed at restore time. If you need different CPUs, memory, or an updated image, create a fresh sandbox instead.

## See Also

- [sandbox_sdk.md](sandbox_sdk.md) — create, connect, run commands, file ops, processes, networking, images
- [sandbox_advanced.md](sandbox_advanced.md) — patterns: skills-in-sandboxes, AI code execution, CI/CD
