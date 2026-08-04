<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/snapshots.md
  - https://docs.tensorlake.ai/sandboxes/pools.md
  - https://docs.tensorlake.ai/api-reference/v2/sandboxes/copy.md
  - https://docs.tensorlake.ai/api-reference/v2/sandboxes/suspend.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Sandbox Persistence

State-centric reference for keeping sandbox state across time: the state machine, ephemeral vs named, snapshots, copy/clone, suspend/resume, idle auto-suspend, and sandbox pools.

For creating, connecting to, and running commands in a sandbox, see [sandbox_sdk.md](sandbox_sdk.md). For persisting files *outside* a sandbox's own lifecycle — versioned Cloud Volumes and Git repositories mounted into sandboxes — see [volumes_and_git.md](volumes_and_git.md).

Snapshot / suspend / resume are instance methods on the `Sandbox` handle; restore is `Sandbox.create(snapshot_id=...)`. Rename is `sandbox.update(name=...)`. Listing is `Sandbox.list()`. Pools live on `SandboxClient` / `AsyncSandboxClient`.

## Table of Contents

- [State Machine](#state-machine)
- [Resource Limits and Timeouts](#resource-limits-and-timeouts)
- [Ephemeral vs Named](#ephemeral-vs-named)
- [Snapshots](#snapshots)
  - [Snapshot Types](#snapshot-types--filesystem-default-vs-memory)
  - [Create a Snapshot](#create-a-snapshot)
  - [Restore from a Snapshot](#restore-from-a-snapshot)
  - [Manage Snapshots](#manage-snapshots)
  - [Forking from a Snapshot](#forking-from-a-snapshot)
  - [Copy a Sandbox](#copy-a-sandbox)
- [Suspend & Resume](#suspend--resume)
- [Suspend vs Snapshot — When to Use Which](#suspend-vs-snapshot--when-to-use-which)
- [Sandbox Pools](#sandbox-pools)
- [Limitations](#limitations)
- [See Also](#see-also)

## State Machine

Every sandbox moves through the states below. `create` (or restore from a snapshot) starts the sandbox in `Pending`. From `Running` you can snapshot, suspend (named only), or terminate. `Terminated` is final.

```
     [*]
      │
      ▼
   Pending  ◄── create / restore from snapshot
      │
      ▼
   Running ──────── snapshot ────────► Snapshotting ──┐
      │ ▲                                            │
      │ └─────────── snapshot complete ──────────────┘
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

- **Named** — timeout triggers a suspend, preserving filesystem, memory, and running processes for later resume.
- **Ephemeral** — timeout triggers termination (final state).

Ephemeral sandboxes follow the same `create → Pending → Running → Terminated` flow but never enter `Suspending`/`Suspended`. Explicit `terminate` works from `Running` or `Suspended`.

### State Descriptions

| State | What it means | How you exit it |
|---|---|---|
| `Pending` | Being scheduled and booted. Not yet accepting commands. | Transitions to `Running` automatically once boot completes. |
| `Running` | Live and accepting commands, file operations, and process execution. Snapshots can be taken from here. | Call `suspend` (named only) or `terminate`. |
| `Snapshotting` | A reusable snapshot artifact is being captured. | Returns to `Running` when capture completes. |
| `Suspending` | Named sandbox being paused in place. Triggered by manual suspend or by `timeout_secs` elapsing. | Transitions to `Suspended` automatically. |
| `Suspended` | Named sandbox paused. **Consumes no compute**; state preserved for resume under the same sandbox ID. | Call `resume` to return to `Running`, or `terminate`. |
| `Terminated` | Stopped, manually or via timeout for ephemeral sandboxes. Final; cannot be reversed. | — |

## Resource Limits and Timeouts

**Resources** are fixed at create time and cannot be changed afterwards — create a new sandbox if you need different ones.

| Parameter | Default | Allowed range |
|---|---|---|
| `cpus` | `1.0` | float |
| `memory_mb` | `1024` | **1024–8192 MB per CPU core** |
| `disk_mb` | `10240` | 10240–102400 MiB (10–100 GiB). Accepted on fresh creates. With `image`, or with a **filesystem** `snapshot_id`, it can grow the root disk (growth-only). CLI flag `--disk_mb`, in MiB. |

**Timeouts.** `timeout_secs` is an **idle threshold**, not a wall-clock lifetime. The sandbox stays running as long as it is handling traffic through the sandbox proxy: an open SSH session, a connected WebSocket PTY, a request to an exposed user port, or any SDK/CLI call. Once no proxied traffic has been in flight for `timeout_secs`, it times out. Default is `600` seconds (10 minutes) when unset.

Setting `timeout_secs=0` requests the **plan maximum** — it does NOT mean "no timeout":

| Plan | Max `timeout_secs` |
|---|---|
| Free (unverified) | 1 hour |
| Free (verified) | 2 hours |
| On-Demand (pay-as-you-go) | 24 hours |

See [tensorlake.ai/pricing](https://www.tensorlake.ai/pricing) for higher limits on committed plans.

## Ephemeral vs Named

Persistence requires a **named** sandbox. Ephemeral sandboxes cannot be suspended, resumed, or auto-resumed.

| | Ephemeral | Named |
|---|---|---|
| Created with | `Sandbox.create()` / `tl sbx create` | `Sandbox.create(name=...)` / `tl sbx create <name>` |
| Suspend / Resume | Not supported — returns an error (`400`) | Supported |
| Idle auto-suspend | Not supported | Supported |
| Timeout behavior | Terminates on timeout | Suspends on timeout |
| Reference by | ID only | ID **or** name |
| Use when | Short-lived tasks, one-off execution | Multi-step work, persistent environments |

An ephemeral sandbox can be promoted to named after creation via `sandbox.update(name="my-env")` — the `sandbox_id` is preserved and the handle stays usable. CLI equivalent: `tl sbx name <id> <new-name>`. HTTP: `PATCH /sandboxes/<sandbox-id>` with `{"name": "my-env"}`. After renaming it becomes eligible for suspend/resume.

Once a sandbox has a name, either the name or the UUID works anywhere a sandbox identifier is accepted — including the proxy hostname (`https://my-env.sandbox.tensorlake.ai`) and every `tl sbx` verb. The management URL on port `9501` still requires authentication.

## Snapshots

Snapshots capture sandbox state into a reusable artifact you can boot a **new** sandbox from. Unlike suspend, the source sandbox keeps running.

Snapshots are independent of sandbox lifecycle — once captured, the artifact persists after the source sandbox is terminated. You can snapshot an ephemeral sandbox before it ends and restore that state into a new sandbox much later.

> **Restore is not uniformly "as-is".** There are two snapshot types: **`filesystem` (the default)** and **`memory`**. Filesystem snapshots accept resource overrides at restore, so booting on bigger hardware than the original is supported. Memory snapshots lock image, resources, and entrypoint to the snapshot. Don't tell users they must rebuild from scratch to change resources without first checking the snapshot type.

### Snapshot Types — Filesystem (default) vs Memory

| | Filesystem snapshot (default) | Memory snapshot |
|---|---|---|
| **What it captures** | Filesystem state | Filesystem **+ memory + running process state** |
| **Restore semantics** | Cold boot onto the captured filesystem | Warm start into the exact captured state, processes still running |
| **Resource changes at restore?** | **Yes** — CPU, memory, and disk can change for the new sandbox; `disk_mb` / `resources.disk_mb` is growth-only | **No** — image, resources (CPUs, memory), and entrypoint come from the snapshot and cannot be changed |
| **Use for** | Reusable starting points, baking dependencies, forking onto different hardware | Pause-and-fork an agent mid-execution, debug-after-the-fact |

When you do not specify a type, Tensorlake uses `filesystem`.

**Selecting the type:**

- **Python:** `sandbox.checkpoint(checkpoint_type=CheckpointType.MEMORY)` or `CheckpointType.FILESYSTEM`. Import: `from tensorlake.sandbox import CheckpointType, Sandbox`.
- **TypeScript:** `sandbox.checkpoint({ checkpointType: "memory" })` or `"filesystem"`. `CheckpointType` is exported from `tensorlake`; the field on `CheckpointOptions` is `checkpointType`.
- **CLI:** `tl sbx checkpoint <id> --checkpoint-type memory` (or `filesystem`).

Read the type back off `SnapshotInfo`: `snapshot.snapshot_type` (Python — an enum, so `.snapshot_type.value` for the string) / `snapshot.snapshotType` (TypeScript).

### Create a Snapshot

**`checkpoint()` parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sandbox_id` | `str` | — | ID of the running sandbox to snapshot |
| `checkpoint_type` | `CheckpointType` (TS: `"memory" \| "filesystem"`) | server default (currently `filesystem`) | `FILESYSTEM` captures filesystem-only state; `MEMORY` captures filesystem + VM memory + running processes |
| `timeout` | `float` | `300` | Max seconds to wait for completion |
| `poll_interval` | `float` | `1.0` | Seconds between status polls |

**Python:**

```python
from tensorlake.sandbox import CheckpointType, Sandbox

sandbox = Sandbox.create()
sandbox.run("pip", ["install", "numpy", "pandas", "--user", "--break-system-packages"])

# Default (server-side default, currently `filesystem`)
snapshot = sandbox.checkpoint()

# Explicitly request a memory checkpoint (warm-restore VM memory + processes)
snapshot = sandbox.checkpoint(checkpoint_type=CheckpointType.MEMORY)

# Filesystem-only checkpoint (cold-boot from snapshot tarball)
snapshot = sandbox.checkpoint(checkpoint_type=CheckpointType.FILESYSTEM)

print(snapshot.snapshot_id)
```

**TypeScript:**

```typescript
import { Sandbox, type CheckpointType } from "tensorlake";

const sandbox = await Sandbox.create();

let snapshot = await sandbox.checkpoint();
snapshot = await sandbox.checkpoint({ checkpointType: "memory" });
snapshot = await sandbox.checkpoint({ checkpointType: "filesystem" });

console.log(snapshot?.snapshotId);
```

**CLI:**

```bash
tl sbx checkpoint <sandbox-id>
tl sbx checkpoint <sandbox-id> --checkpoint-type filesystem
tl sbx checkpoint <sandbox-id> --checkpoint-type memory
tl sbx checkpoint <sandbox-id> --timeout 600
```

**REST:**

```bash
curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id>/snapshot \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

### Graceful Stop + Snapshot (long-running process)

To interrupt a running background process and preserve its post-shutdown state, the canonical sequence is **SIGTERM → wait for the process to exit → `checkpoint()` → `terminate()`**. SIGTERM gives the program a chance to flush buffers and write its own final partial output; the snapshot then captures that flushed state. Snapshotting *before* the signal captures in-flight memory but misses whatever the process would have written on graceful shutdown.

```python
import signal
from tensorlake.sandbox import Sandbox

sandbox = Sandbox.create(name="training-run", cpus=4.0, memory_mb=8192)
proc = sandbox.start_process("python", args=["/workspace/train.py"])

try:
    for event in sandbox.follow_output(proc.pid):
        print(event.line, end="", flush=True)
except KeyboardInterrupt:
    sandbox.send_signal(proc.pid, signal.SIGTERM)   # 1. graceful — let the process flush
    snapshot = sandbox.checkpoint()                 # 2. capture post-shutdown state
    print(f"Snapshot: {snapshot.snapshot_id}")
    sandbox.terminate()                             # 3. tear down the sandbox

# Later, in a fresh script — restore creates a NEW sandbox with a new sandbox_id
restored = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

This is **snapshot/restore semantics** (new sandbox, new ID), not **suspend/resume** (same sandbox, same ID).

> **Surface this distinction explicitly when answering.** If the prompt mentions "fresh environment", "clean environment", "new sandbox", "later/separately", "fork", or "inspect/debug after the fact" — say in prose that `Sandbox.create(snapshot_id=...)` produces a *new* sandbox with a *new* `sandbox_id`, and that this is why it beats suspend/resume here. Don't bundle "checkpoints" with "suspend semantics" in summary lines.

### Restore from a Snapshot

- **Filesystem snapshot (default):** the new sandbox restores the captured filesystem. You can change resources (CPU, memory, disk) for the new sandbox; `disk_mb` / `resources.disk_mb` is **growth-only** (10240–102400 MiB). Image is locked to the snapshot.
- **Memory snapshot:** the new sandbox restores filesystem, memory, and running processes exactly as they were. Image, resources (CPUs, memory), and entrypoint come from the snapshot and cannot be changed at restore time. If you need different resources, create a fresh sandbox instead of restoring.

> **Don't deduce the snapshot type from creation defaults — read it from the API.** When someone asks whether their existing snapshot's kind matters, or wants to restore with overrides, don't reason from "the default is filesystem unless `MEMORY` was passed". Point them at `Sandbox.get_snapshot(snapshot_id).snapshot_type` (Python) / `Sandbox.getSnapshot(...).snapshotType` (TypeScript) / `tl sbx checkpoint ls` (CLI) / `GET /snapshots/<id>` (REST). Defaults change and the snapshot may have been created by someone else; the API is authoritative.

```python
restored = Sandbox.create(snapshot_id=snapshot.snapshot_id)
result = restored.run("cat", ["/data/output.csv"])
print(result.stdout)
```

```typescript
const restored = await Sandbox.create({ snapshotId: snapshot.snapshotId });
```

```bash
tl sbx create --snapshot <snapshot-id>
```

```bash
curl -X POST https://api.tensorlake.ai/sandboxes \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id": "<snapshot-id>"}'
```

### Manage Snapshots

**Python:**

```python
snapshots = sandbox.list_snapshots()          # snapshots created from THIS sandbox (instance)
for s in snapshots:
    print(s.snapshot_id, s.status.value, s.snapshot_type.value if s.snapshot_type else "-", s.size_bytes)

info = Sandbox.get_snapshot("snapshot_id")    # static
print(info.status, info.snapshot_type)

Sandbox.delete_snapshot("snapshot_id")        # static
```

**TypeScript:**

```typescript
const snapshots = await sandbox.listSnapshots();
for (const s of snapshots) {
  console.log(s.snapshotId, s.status, s.snapshotType ?? "-", s.sizeBytes ?? 0);
}

const info = await Sandbox.getSnapshot("snapshot-id");
console.log(info.status, info.snapshotType, info.baseImage, info.sizeBytes);

await Sandbox.deleteSnapshot("snapshot-id");
```

**CLI / REST:**

```bash
tl sbx checkpoint ls
tl sbx checkpoint rm <snapshot-id>

curl https://api.tensorlake.ai/snapshots -H "Authorization: Bearer $TENSORLAKE_API_KEY"
curl https://api.tensorlake.ai/snapshots/<snapshot-id> -H "Authorization: Bearer $TENSORLAKE_API_KEY"
curl -X DELETE https://api.tensorlake.ai/snapshots/<snapshot-id> -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

Getting snapshot details is **not supported in the CLI** as a single-snapshot command — use `tl sbx checkpoint ls`, the SDKs, or REST.

### Forking from a Snapshot

To fork a running agent's environment, `checkpoint()` and then `Sandbox.create(snapshot_id=...)` once per fork. Each fork is a fresh sandbox with its own ID; the source is unaffected.

```python
snapshot = sandbox.checkpoint()
fork_a = Sandbox.create(snapshot_id=snapshot.snapshot_id)
fork_b = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

The intermediate snapshot persists and consumes storage until you delete it with `Sandbox.delete_snapshot(...)` / `tl sbx checkpoint rm <snapshot-id>`.

### Copy a Sandbox

`tl sbx copy` is the one-shot clone: it boots one or more new sandboxes from a **running or suspended** source, restoring filesystem, memory, and running processes so each copy **warm-starts**.

```bash
tl sbx copy <sandbox-id>
tl sbx copy <sandbox-id> -n 4              # several copies from the same source in one call
tl sbx copy <sandbox-id> --timeout 600
```

```bash
curl -X POST "https://api.tensorlake.ai/sandboxes/<sandbox-id>/copy?times=1" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

- **Not supported in the Python SDK. Not yet exposed in the TypeScript SDK** — use the CLI or HTTP API, or call `checkpoint()` followed by `Sandbox.create(snapshot_id=...)` explicitly.
- The source must be **running or suspended**; any other state returns `400`.
- A running source is copied from the executor hosting it; a suspended source is copied from the snapshot its suspend already produced — so **a copy does not leave a new checkpoint behind for you to clean up**.
- Copies inherit the source's **image, resources, entrypoint, network policy, and exposed ports**.
- The request takes **no body**; `times` (default `1`) and `name` are query parameters. The path accepts a sandbox ID or name.

**Naming.** Names are unique per namespace, so copies cannot reuse the source's name:

| `name` | `times` | Source | Copy names |
|---|---|---|---|
| `worker` | 1 | any | `worker` |
| `worker` | 3 | any | `worker-1`, `worker-2`, `worker-3` |
| omitted | 1 | named `build-env` | `build-env-copy` |
| omitted | 2 | named `build-env` | `build-env-copy-1`, `build-env-copy-2` |
| omitted | any | unnamed | unnamed |

Naming matters for lifecycle: only named sandboxes can be suspended and resumed, so a named source keeps its copies named (and suspendable) by default, while an unnamed copy terminates at its idle timeout. Pass `name` explicitly to name an unnamed source's copies.

Derived names are validated up front: `400` if a derived name is malformed or exceeds the **63-character DNS label limit** once suffixed (a base that fits alone can still overflow with `-N`), `409` if a derived name is already claimed by a live sandbox in the namespace. A rejected request creates nothing, so re-running the same named fan-out is safe and leaves no partial copies.

**Partial failures.** `200` means every requested copy is running. `422` means one or more copies failed before becoming ready; `504` means one or more did not become ready within the timeout. Both return the same body shape — inspect each entry's `status` to see which copies succeeded.

## Suspend & Resume

Suspend a running **named** sandbox to pause it in place: it is snapshotted and the live container is terminated, so it consumes no compute while filesystem, memory, and running processes are preserved. Resume brings the **same** sandbox back to `Running` exactly where it left off — `sandbox_id` and name unchanged. Ephemeral sandboxes cannot be suspended and return an error.

Suspend and resume do **not** create a reusable artifact you can boot other sandboxes from; use [Snapshots](#snapshots) for that.

**Python:**

```python
sandbox = Sandbox.connect("my-env")
sandbox.suspend()
sandbox.resume()
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
curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id-or-name>/suspend \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"

curl -X POST https://api.tensorlake.ai/sandboxes/<sandbox-id-or-name>/resume \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

Both paths accept the sandbox ID **or** the sandbox name. On suspend, Tensorlake returns `202 Accepted` when suspension starts or is already in progress, and `200 OK` when the sandbox is already suspended. Ephemeral sandboxes return `400 Bad Request`.

### Idle Auto-Suspend and Auto-Resume

- **Auto-suspend:** when a named sandbox has had no proxied traffic for `timeout_secs`, it suspends automatically, preserving filesystem, memory, and running processes without billing for a running container.
- **Auto-resume on request:** if a named sandbox is suspended, the proxy can auto-resume it when a request arrives for an exposed port.
- **Ephemeral sandboxes:** never auto-suspend and cannot be auto-resumed — they terminate when their work ends or `timeout_secs` elapses.

This lets agents keep long-lived environments between tasks without paying to keep them running.

## Suspend vs Snapshot — When to Use Which

| | Suspend / Resume | Snapshot / Restore |
|---|---|---|
| **What it does** | Pauses the **same** sandbox in place | Creates a reusable artifact you boot **new** sandboxes from |
| **Same sandbox ID after?** | Yes — `sandbox_id` and `name` preserved | No — restore produces a new sandbox with a new ID |
| **Run multiple copies?** | No — one sandbox at a time | Yes — fork N sandboxes from one snapshot |
| **Requires named sandbox?** | Yes | No — works on ephemeral too |
| **Auto-triggered?** | Yes (idle auto-suspend, auto-resume on request) | No — always explicit |
| **Use for** | Pausing an agent's environment between tasks; same URL | Checkpoints, forking work, reusable starting states |

The docs' own decision table:

| Scenario | Use Suspend | Use Snapshot |
|---|---|---|
| Pause and resume later | ✅ | ❌ |
| Save cost when idle | ✅ | ❌ |
| Keep agent memory alive | ✅ | ❌ |
| Retry from a checkpoint | ❌ | ✅ |
| Run experiments from same state | ❌ | ✅ |
| Clone environment | ❌ | ✅ |

Rule of thumb: **suspend** when you want *this* sandbox back later; **checkpoint** when you want a starting point you can restore, fork, or share.

## Sandbox Pools

A Sandbox Pool is a sandbox **template** (image, resources, entrypoint, timeout, network policy) plus a set of **pre-booted warm containers**. Creating a sandbox from a pool claims a warm container instead of cold-booting one, so the sandbox is ready almost instantly.

How it works:

- The pool keeps `warm_containers` idle containers booted and waiting.
- Creating a sandbox from the pool claims a warm container if one is available; otherwise a new container cold-starts on demand.
- After a claim, the pool boots a replacement to restore the warm buffer.
- `max_containers` caps the pool's total (warm + claimed) containers. At the cap, new sandboxes stay `pending` until a slot frees up.

Sandboxes claimed from a pool **inherit the pool's image, resources, entrypoint, timeout, and network policy — you cannot override them per sandbox.**

> Snapshot restores cold-boot; they do **not** claim warm containers.

### Creating a Pool

**Python:**

```python
from tensorlake.sandbox import SandboxClient

client = SandboxClient.for_cloud()

pool = client.create_pool(
    image="tensorlake/ubuntu-minimal",
    cpus=1.0,
    memory_mb=1024,
    warm_containers=2,
    max_containers=10,
)
print(pool.pool_id)
```

**TypeScript:**

```typescript
import { SandboxClient } from "tensorlake";

const client = new SandboxClient();

const pool = await client.createPool({
  image: "tensorlake/ubuntu-minimal",
  cpus: 1.0,
  memoryMb: 1024,
  warmContainers: 2,
  maxContainers: 10,
});
console.log(pool.poolId);
```

**HTTP:**

```bash
curl -X POST https://api.tensorlake.ai/sandbox-pools \
  -H "Authorization: Bearer $TL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "tensorlake/ubuntu-minimal",
    "resources": {"cpus": 1.0, "memory_mb": 1024},
    "warm_containers": 2,
    "max_containers": 10
  }'
```

**Not supported in the CLI.**

### Pool Configuration

| Field | Type | Default | Description |
|---|---|---|---|
| `image` | `str` | — | Sandbox image for containers in the pool. **Required.** |
| `cpus` | `float` | `1.0` | CPU cores per container (max 16) |
| `memory_mb` | `int` | `1024` | Memory per container in MB (max 65536; must be 1000–8192 MB per CPU core) |
| `warm_containers` | `int` | `None` | Idle, pre-booted containers to keep ready. Set `0` to scale to zero when idle. |
| `max_containers` | `int` | `None` (unbounded) | Cap on total containers, warm and claimed |
| `timeout_secs` | `int` | `0` (no timeout) | Timeout applied to sandboxes created from the pool |
| `entrypoint` | `list[str]` | `None` | Entrypoint command for pool containers |

The HTTP API additionally accepts `exposed_ports`, `network` (egress policy), and `allow_unauthenticated_access`, with the same semantics as sandbox creation. Root disk size is server-managed for pool containers; `ephemeral_disk_mb` is accepted but **ignored**.

### Creating a Sandbox from a Pool

Pass `pool_id` to `Sandbox.create()`:

```python
from tensorlake.sandbox import Sandbox

with Sandbox.create(pool_id=pool.pool_id) as sandbox:
    result = sandbox.run("echo", ["hello from the pool"])
    print(result.stdout)
# Sandbox terminates on exit; the pool boots a replacement warm container.
```

```typescript
const sandbox = await Sandbox.create({ poolId: pool.poolId });
const result = await sandbox.run("echo", { args: ["hello from the pool"] });
console.log(result.stdout);
await sandbox.terminate();
```

```bash
curl -X POST https://api.tensorlake.ai/sandbox-pools/<pool-id>/sandboxes \
  -H "Authorization: Bearer $TL_API_KEY"
# Returns sandbox_id with status `pending`; poll the sandbox until it is `running`.
```

> When claiming from a pool, the sandbox `name` and `file_systems` parameters are **ignored** — the container is already booted from the pool's template.

### Managing Pools

```python
# Get: returns the pool config plus its current containers.
# Containers with no sandbox_id are warm and unclaimed.
info = client.get_pool(pool.pool_id)
print(info.image, info.warm_containers, info.max_containers)
for c in info.containers or []:
    print(c.id, c.state, c.sandbox_id or "warm")

# List
for p in client.list_pools():
    print(p.pool_id, p.image)

# Update: replaces the pool configuration. `image` is required on update.
# The warm buffer reconciles to the new settings; already-claimed sandboxes are unaffected.
client.update_pool(
    pool_id=pool.pool_id,
    image="tensorlake/ubuntu-minimal",
    cpus=2.0,
    memory_mb=4096,
    warm_containers=5,
)

# Delete
from tensorlake.sandbox import PoolInUseError

try:
    client.delete_pool(pool.pool_id)
except PoolInUseError:
    # Terminate active sandboxes first, then retry.
    raise
```

```typescript
const info = await client.getPool(pool.poolId);
for (const c of info.containers ?? []) {
  console.log(c.id, c.state, c.sandboxId ?? "warm");
}

const pools = await client.listPools();

await client.updatePool(pool.poolId, {
  image: "tensorlake/ubuntu-minimal",
  cpus: 2.0,
  memoryMb: 4096,
  warmContainers: 5,
});

await client.deletePool(pool.poolId);   // throws PoolInUseError if sandboxes are still active
```

```bash
curl https://api.tensorlake.ai/sandbox-pools/<pool-id> -H "Authorization: Bearer $TL_API_KEY"
curl https://api.tensorlake.ai/sandbox-pools       -H "Authorization: Bearer $TL_API_KEY"
curl -X PUT https://api.tensorlake.ai/sandbox-pools/<pool-id> \
  -H "Authorization: Bearer $TL_API_KEY" -H "Content-Type: application/json" \
  -d '{"image": "tensorlake/ubuntu-minimal", "resources": {"cpus": 2.0, "memory_mb": 4096}, "warm_containers": 5}'
curl -X DELETE https://api.tensorlake.ai/sandbox-pools/<pool-id> -H "Authorization: Bearer $TL_API_KEY"
# Force-delete: also terminates active sandboxes from the pool
curl -X DELETE "https://api.tensorlake.ai/sandbox-pools/<pool-id>?force=true" -H "Authorization: Bearer $TL_API_KEY"
```

Deleting a pool tears down its warm containers. If sandboxes claimed from the pool are still active, the delete fails with `PoolInUseError` (HTTP `409`) — terminate them first, or pass `force=true` over HTTP to terminate them along with the pool.

**Async.** `AsyncSandboxClient` exposes the same pool methods (`create_pool`, `get_pool`, `list_pools`, `update_pool`, `delete_pool`, `claim`) as coroutines, and `AsyncSandbox.create(pool_id=...)` claims from a pool.

## Limitations

- **Suspend/resume requires named sandboxes.** Ephemeral sandboxes return `400` on suspend. Promote to named first via `sandbox.update(name="my-env")` / `tl sbx name <id> <new-name>`.
- **Terminated is final.** A terminated sandbox cannot be resumed. `checkpoint()` beforehand if you need a restore path.
- **Snapshot restore is to a new sandbox.** It does not mutate the original.
- **Restore semantics depend on snapshot type.** *Memory* snapshots restore as-is — image, resources, and entrypoint all come from the snapshot. *Filesystem* snapshots (the default) allow CPU/memory/disk changes (`disk_mb` growth-only); image is still locked. If you need a different image, or you have a memory snapshot and need different resources, create a fresh sandbox.
- **`tl sbx copy` has no Python or TypeScript SDK equivalent yet.** Use the CLI/HTTP API, or `checkpoint()` + `Sandbox.create(snapshot_id=...)`.
- **Pool-claimed sandboxes cannot override the template.** Image, resources, entrypoint, timeout, and network policy come from the pool; `name` and `file_systems` are ignored. Pools are not exposed in the CLI.

## See Also

- [sandbox_sdk.md](sandbox_sdk.md) — create, connect, run commands, file ops, processes, logs, networking, images
- [volumes_and_git.md](volumes_and_git.md) — Cloud Volumes and Git repositories: durable state that outlives any single sandbox
- [sandbox_usecases.md](sandbox_usecases.md) — skills-in-sandboxes, tool calls, CI/CD, Chrome over CDP, remote dev, agent integrations
- [computer_use.md](computer_use.md) — snapshot a warmed-up `tensorlake/ubuntu-vnc` desktop and fork parallel agent sessions
