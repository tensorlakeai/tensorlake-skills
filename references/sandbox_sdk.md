<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/introduction.md
  - https://docs.tensorlake.ai/sandboxes/quickstart.md
  - https://docs.tensorlake.ai/sandboxes/sdk-reference.md
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
  - https://docs.tensorlake.ai/sandboxes/file-operations.md
  - https://docs.tensorlake.ai/sandboxes/environment-variables.md
  - https://docs.tensorlake.ai/sandboxes/networking.md
  - https://docs.tensorlake.ai/sandboxes/images.md
  - https://docs.tensorlake.ai/sandboxes/pty-sessions.md
  - https://docs.tensorlake.ai/sandboxes/docker.md
  - https://docs.tensorlake.ai/sandboxes/async.md
  - https://docs.tensorlake.ai/sandboxes/tunnels.md
SDK version: tensorlake 0.5.44
Last verified: 2026-06-16
-->

# TensorLake Sandbox SDK Reference

TensorLake Sandboxes are MicroVMs backed by Firecracker and CloudHypervisor. The `tensorlake/ubuntu-minimal` base image starts up in a few hundred milliseconds; `tensorlake/ubuntu-systemd` takes around 1 second to boot. The platform is HIPAA and SOC 2 Type II compliant, supports EU data residency, and offers zero data retention.

For state management (snapshots, suspend/resume, ephemeral vs named), see [sandbox_persistence.md](sandbox_persistence.md). For desktop automation / computer-use (the `tensorlake/ubuntu-vnc` image, `sandbox.connect_desktop()`, screenshot and keyboard/mouse APIs, noVNC bridge), see [computer_use.md](computer_use.md). For SSH access and using a sandbox as a remote dev environment, see [sandbox_usecases.md](sandbox_usecases.md#sandbox-as-a-dev-environment).

> `Sandbox` is the preferred handle for create/connect/run/suspend/resume/checkpoint, list (`Sandbox.list()`), info (`sandbox.info()`), and **rename and port exposure** via `sandbox.update(name=..., exposed_ports=..., allow_unauthenticated_access=...)`. `SandboxClient` still ships for legacy management calls but emits a `DeprecationWarning` on construction — every operation now has a `Sandbox`-level equivalent. `Sandbox.name` and `Sandbox.sandbox_id` are properties (no parens) in Python; `Sandbox.status` is a Python property returning a `SandboxStatus` enum (`SandboxStatus.RUNNING`, `.SUSPENDED`, etc. — use `sandbox.status.value` for the lowercase string form). In TypeScript, `sandboxId` and `name` are getters but **`status` is an async method**: `await sandbox.status()`. Snapshot creation is `sandbox.checkpoint()`; restore is `Sandbox.create(snapshot_id=...)`.

## Table of Contents

- [TensorLake Sandbox SDK Reference](#tensorlake-sandbox-sdk-reference)
  - [Table of Contents](#table-of-contents)
  - [Imports](#imports)
  - [Managing Sandboxes](#managing-sandboxes)
    - [Create a Sandbox](#create-a-sandbox)
    - [Connect to an Existing Sandbox](#connect-to-an-existing-sandbox)
    - [List, Inspect, Rename](#list-inspect-rename)
    - [Resource Limits and Timeouts](#resource-limits-and-timeouts)
  - [Working in a Sandbox](#working-in-a-sandbox)
    - [Suspend, Resume, Terminate](#suspend-resume-terminate)
    - [Checkpoint and Restore](#checkpoint-and-restore)
    - [Get and Delete Snapshots](#get-and-delete-snapshots)
    - [Run a Command](#run-a-command)
    - [File Operations](#file-operations)
    - [Environment Variables](#environment-variables)
    - [Background Processes](#background-processes)
    - [Managed Processes](#managed-processes)
    - [Writing to stdin](#writing-to-stdin)
    - [PTY Sessions](#pty-sessions)
    - [SSH](#ssh)
    - [Async SDK (Python)](#async-sdk-python)
  - [Sandbox Images](#sandbox-images)
    - [Define an Image](#define-an-image)
    - [Build / Register the Image](#build--register-the-image)
    - [Import an Image from a Registry](#import-an-image-from-a-registry)
    - [Public Images](#public-images)
    - [Base Images](#base-images)
    - [Image Builder Methods (chainable)](#image-builder-methods-chainable)
    - [Supported Build Operations](#supported-build-operations)
    - [Launching Sandboxes from Custom Images](#launching-sandboxes-from-custom-images)
    - [Running Docker Inside a Sandbox](#running-docker-inside-a-sandbox)
  - [Networking](#networking)
    - [Public URLs](#public-urls)
    - [Port Exposure](#port-exposure)
    - [Outbound Internet Control](#outbound-internet-control)
    - [Local Tunnels](#local-tunnels)
  - [Data Models](#data-models)
    - [SandboxInfo](#sandboxinfo)
    - [CommandResult](#commandresult)
    - [ProcessInfo](#processinfo)
    - [SnapshotInfo](#snapshotinfo)
    - [Process Status / Mode Enums](#process-status--mode-enums)
  - [CLI Quick Reference](#cli-quick-reference)

## Imports

**Python:**

```python
from tensorlake.sandbox import Sandbox
```

**TypeScript:**

```typescript
import { Sandbox } from "tensorlake";
```

## Managing Sandboxes

Creating, connecting to, listing, renaming, and managing snapshots are operations on the `Sandbox` class itself (called as `Sandbox.create(...)`, `Sandbox.connect(...)`, etc.) rather than on a specific sandbox handle.

### Create a Sandbox

**Python:**

```python
# Ephemeral sandbox — no name, cannot be suspended
sandbox = Sandbox.create(
    name=None,             # str | None — promote to named by passing a value
    cpus=1.0,              # float, 1.0–8.0
    memory_mb=1024,        # int, 1024–8192 per CPU
    disk_mb=10240,         # int, 10240–102400 (10–100 GiB) — root filesystem size in MiB
    timeout_secs=None,     # int | None — server default 600; pass an int to override
    image=None,            # str | None — registered image name or base image
    snapshot_id=None,      # str | None — restore from a snapshot
    secret_names=None,     # list[str] | None — secrets to inject as env vars
    entrypoint=None,       # list[str] | None — custom entrypoint command
    allow_internet_access=True,  # bool — see Networking
    allow_out=None,        # list[str] | None — see Networking
    deny_out=None,         # list[str] | None — see Networking
)

# Named sandbox — eligible for suspend/resume
named = Sandbox.create(name="my-agent-env", cpus=2.0, memory_mb=2048, timeout_secs=300)

print(named.sandbox_id)        # server-assigned UUID, e.g. "5gm9wex8dm6ko1ed441ym"
print(named.name)              # "my-agent-env"
print(named.status)            # SandboxStatus.RUNNING
print(named.status.value)      # "running"
```

**TypeScript:**

```typescript
const ephemeral = await Sandbox.create({
  cpus: 1.0,
  memoryMb: 1024,
  diskMb: 10240,         // 10240–102400 (10–100 GiB)
  timeoutSecs: 300,
});

const named = await Sandbox.create({
  name: "my-agent-env",
  cpus: 2.0,
  memoryMb: 2048,
  image: "data-tools-image",
  snapshotId: undefined,
  secretNames: ["OPENAI_API_KEY"],
});

console.log(named.sandboxId);
console.log(named.name);
console.log(named.status);
```

`Sandbox.create()` returns an operable `Sandbox` handle that is already connected — you can call methods on it directly without a separate `connect()` step. Port exposure is a post-create operation; see [Port Exposure](#port-exposure) under Networking.

### Connect to an Existing Sandbox

**Python:**

```python
# accepts sandbox_id (UUID) or name
sandbox = Sandbox.connect("my-agent-env")
print(sandbox.sandbox_id)  # server UUID, e.g. "s7jus08qec4axzgbpq76h"
print(sandbox.name)        # "my-agent-env"

result = sandbox.run("python", ["main.py"])
print(result.stdout)
```

**TypeScript:**

```typescript
// TypeScript Sandbox.connect takes an options object — not a bare string
const sandbox = await Sandbox.connect({ sandboxId: "my-agent-env" });

console.log(sandbox.sandboxId);
console.log(sandbox.name);
console.log(await sandbox.status());          // async method in TS — not a getter

const result = await sandbox.run("python", { args: ["main.py"] });
console.log(result.stdout);
```

### List, Inspect, Rename

Listing, inspecting, renaming, and port-exposure all live on `Sandbox` directly. `SandboxClient` is now fully deprecated — every operation has a `Sandbox`-level equivalent.

**Python:**

```python
from tensorlake.sandbox import Sandbox

# List all sandboxes in the namespace
for sb in Sandbox.list():                        # -> list[SandboxInfo]
    print(sb.sandbox_id, sb.status)

# Inspect a single sandbox's metadata (image, resources, timeouts, …)
info = sandbox.info()                            # -> SandboxInfo
print(info.image, info.resources.cpus, info.resources.memory_mb)

# Rename / promote ephemeral → named, or change exposed ports
info = sandbox.update(name="my-env")             # -> Traced[SandboxInfo]
sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
print(info.value.name, info.value.exposed_ports)
```

> If you only have a `sandbox_id`, bridge to the handle: `Sandbox.connect("sbx-123").update(name="my-env")`. The legacy `SandboxClient().update_sandbox("sbx-123", "my-env")` form still works but is deprecated.

**TypeScript:**

```typescript
import { Sandbox } from "tensorlake";

// List
const sandboxes = await Sandbox.list();
for (const sb of sandboxes) {
  // sb.status is a SandboxStatus enum whose values are lowercase strings:
  // "pending" | "running" | "snapshotting" | "suspending" | "suspended" | "terminated"
  console.log(sb.sandboxId, sb.name, sb.status, sb.createdAt);
}

// Inspect
const info = await sandbox.info();
console.log(info.image, info.resources.cpus, info.resources.memoryMb);

// Rename / port exposure
await sandbox.update({ name: "my-env" });
await sandbox.update({ exposedPorts: [8080], allowUnauthenticatedAccess: false });

// Filter then terminate — terminate is called on the handle
import { SandboxStatus } from "tensorlake";
const stale = sandboxes.filter((sb) => sb.status === SandboxStatus.SUSPENDED);
for (const sb of stale) {
  const handle = await Sandbox.connect({ sandboxId: sb.sandboxId });
  await handle.terminate();
}
```

> Termination is called on the handle (`sandbox.terminate()` / `await sandbox.terminate()`), not on the `Sandbox` class. There is **no `sandbox.destroy()`** — that name is a common hallucination from other SDKs (Playwright, Selenium, etc.); the only termination method is `sandbox.terminate()`. The `status` field on `SandboxInfo` is a `SandboxStatus` enum whose string values are lowercase (`"suspended"`, `"running"`, …) in both Python and TypeScript — compare against `SandboxStatus.SUSPENDED` (or the literal `"suspended"`) rather than `"Suspended"`. In Python, `sandbox.status.value` gives the same lowercase string.

Port exposure is also a `sandbox.update(...)` operation — see [Networking → Port Exposure](#port-exposure).

### Resource Limits and Timeouts

| Parameter   | Default  | Allowed range                                                              |
|-------------|----------|----------------------------------------------------------------------------|
| `cpus`      | `1.0`    | float                                                                      |
| `memory_mb` | `1024`   | **1024–8192 MB per CPU core**                                              |
| `disk_mb`   | `10240`  | 10240–102400 MiB (10–100 GiB). Growth-only on restore from a filesystem snapshot or `image=`. |
| `timeout_secs` | `600`  | idle threshold; **plan max**: Free (unverified) 1h, Free (verified) 2h, On-Demand 24h. `0` requests plan max. |

`timeout_secs` is an **idle threshold**, not a wall-clock lifetime — the sandbox stays running as long as any proxied traffic (SSH, PTY WebSocket, exposed-port HTTP, SDK/CLI calls) is in flight. `timeout_secs=0` requests the **plan maximum**, not "no timeout". For named sandboxes the timeout triggers a suspend; for ephemeral, a terminate. See [sandbox_persistence.md](sandbox_persistence.md#resource-limits-and-timeouts).

## Working in a Sandbox

Once you have a `Sandbox` handle (from `create` or `connect`), use these methods directly on it.

### Suspend, Resume, Terminate

**Python:**

```python
sandbox.suspend()    # named only — pause in place; keeps sandbox_id and name
sandbox.resume()     # bring same sandbox back to Running
sandbox.terminate()  # final state; cannot be reversed
```

**TypeScript:**

```typescript
await sandbox.suspend();
await sandbox.resume();
await sandbox.terminate();
```

Suspend/resume only works on **named** sandboxes. Ephemeral sandboxes return an error. To convert an ephemeral sandbox into a named one after creation, call `sandbox.update(name="my-env")` on the handle — same `sandbox_id` is preserved, no recreation needed. (The legacy `SandboxClient().update_sandbox(id, name)` form still works but is deprecated.) Note: this is fundamentally different from `sandbox.checkpoint()` + `Sandbox.create(snapshot_id=...)`, which produces a *new* sandbox with a *new* `sandbox_id`.

### Checkpoint and Restore

Snapshots persist a sandbox's filesystem, memory, and running processes into a reusable artifact. Unlike suspend, the source sandbox keeps running.

**Python:**

```python
snapshot = sandbox.checkpoint(
    timeout=300,        # float — max seconds to wait for completion (default 300)
    poll_interval=1.0,  # float — seconds between status polls (default 1.0)
)                                   # -> SnapshotInfo
print(snapshot.snapshot_id)

snapshots = sandbox.list_snapshots()   # snapshots created from THIS sandbox
for s in snapshots:
    print(s.snapshot_id, s.status, s.size_bytes)

# Restore to a NEW sandbox
restored = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

**TypeScript:**

```typescript
const snapshot = await sandbox.checkpoint();
console.log(snapshot.snapshotId);

const snapshots = await sandbox.listSnapshots();

const restored = await Sandbox.create({ snapshotId: snapshot.snapshotId });
```

Restore behavior depends on the snapshot type — see [sandbox_persistence.md → Snapshot Types](sandbox_persistence.md#snapshot-types--filesystem-default-vs-full) for the full table. In short: **filesystem snapshots (the default)** accept `cpus=`, `memory_mb=`, and `disk_mb=` overrides at restore (`disk_mb` is **growth-only**, range `10240`–`102400` MiB / 10–100 GiB) — useful for booting on bigger hardware than where the snapshot was baked. **Full snapshots** lock image, resources, entrypoint, and secrets to the snapshot; if you need different resources from a full snapshot, create a fresh sandbox instead. Image is locked to the snapshot in both cases.

### Get and Delete Snapshots

```python
info = Sandbox.get_snapshot("snap-xyz")          # -> SnapshotInfo
Sandbox.delete_snapshot("snap-xyz")              # -> None
```

```typescript
const info = await Sandbox.getSnapshot("snap-xyz");
await Sandbox.deleteSnapshot("snap-xyz");
```

### Run a Command

**Python:**

```python
result = sandbox.run(
    command,                             # str — e.g., "python", "bash"
    args=None,                           # list[str] | None — e.g., ["-c", "print('hi')"]
    env=None,                            # dict[str, str] | None
    working_dir=None,                    # str | None
    timeout=None,                        # float | None — seconds
)
result.exit_code   # int
result.stdout      # str
result.stderr      # str
```

> **Canonical forms — don't invent variants.** For LLM tool-use, the idiom is `sandbox.run("python", ["-c", code])`. There is no `sandbox.exec()`, `sandbox.python()`, `sandbox.eval()`, or `sandbox.repl()`. The return object exposes exactly `stdout`, `stderr`, `exit_code` (Python) / `stdout`, `stderr`, `exitCode` (TypeScript) — don't reference `.output`, `.result`, `.logs`, or streaming fields like `.stream` / `.lines` on the result. **The Python field is `exit_code`, NOT `returncode`** — `CommandResult` is a Pydantic model with no `subprocess.CompletedProcess`-style alias, so `result.returncode` raises `AttributeError`. For live stdout from a long-running process, use `start_process` + `follow_output` (see [Background Processes](#background-processes)), not a fabricated field on `run()`.

**TypeScript:**

```typescript
const result = await sandbox.run("python", {
  args: ["-c", "print('Hello from sandbox!')"],
  env: { MODE: "prod", DEBUG: "0" },
  workingDir: "/workspace",
  timeout: 10,
});
console.log(result.stdout);
console.log(result.exitCode);
```

Shell features (pipes, redirects, chaining) require wrapping in bash:

```python
sandbox.run("bash", ["-c", "ls -la /workspace | grep '.py'"])
sandbox.run("bash", ["-c", "cd /workspace && pip install -r requirements.txt && python main.py"])
```

```typescript
await sandbox.run("bash", { args: ["-lc", "ls -la /workspace | grep '.py' | wc -l"] });
```

### File Operations

**Python:**

```python
sandbox.write_file("/workspace/data.csv", b"name,score\nAlice,95")
data = bytes(sandbox.read_file("/workspace/data.csv"))   # read_file returns bytes-like; wrap with bytes(...)
print(data.decode())
for entry in sandbox.list_directory("/workspace").entries:  # entries[].name, .is_dir, .size
    print(entry.name, entry.is_dir, entry.size)
sandbox.delete_file("/workspace/data.csv")
```

**TypeScript:**

```typescript
await sandbox.writeFile(
  "/workspace/data.csv",
  new TextEncoder().encode("name,score\nAlice,95"),
);

const content = await sandbox.readFile("/workspace/data.csv");
console.log(new TextDecoder().decode(content));

await sandbox.deleteFile("/workspace/data.csv");
```

Best practice: use `/workspace` as the default working directory.

**CLI shortcut — `tl sbx cp`:** mirrors `scp` syntax for transferring files between your machine and a sandbox. The `<sandbox-id-or-name>:/path` form indicates the sandbox side; the bare path is local.

```bash
tl sbx cp ./data.csv <sandbox-id>:/workspace/input.csv     # Upload
tl sbx cp <sandbox-id>:/workspace/output.parquet ./out.pq  # Download
```

> **`tl sbx cp` is file-only today** — it does not support recursive directory copy. For directory transfers, use the Python SDK, TypeScript SDK, or the raw file API (e.g., tar the directory locally, upload the archive with `write_file`, then extract inside the sandbox with `sandbox.run("tar", [...])`).

### Environment Variables

Pass `env` per invocation — choose the scope that matches the lifetime you want:

| Scope   | API                                | Lifetime                            |
|---------|------------------------------------|-------------------------------------|
| Command | `sandbox.run(..., env={...})`      | Single command execution            |
| Process | `sandbox.start_process(..., env=)` | Life of the background process      |
| PTY     | `sandbox.create_pty(..., env=)`    | Life of the interactive terminal    |

```python
sandbox.run("bash", ["-lc", "echo $MODE"], env={"MODE": "prod"})

pty = sandbox.create_pty(
    command="/bin/bash",
    env={"TERM": "xterm-256color", "APP_ENV": "dev"},
    working_dir="/workspace",
    cols=80,
    rows=24,
)
```

```typescript
await sandbox.run("bash", {
  args: ["-lc", "echo $MODE"],
  env: { MODE: "prod" },
});

const pty = await sandbox.createPty({
  command: "/bin/bash",
  env: { TERM: "xterm-256color", APP_ENV: "dev" },
  workingDir: "/workspace",
});
```

**CLI:** both `tl sbx exec` and `tl sbx ssh` accept repeated `--env KEY=VALUE` flags:

```bash
tl sbx exec <sandbox-id> --env MODE=prod --env DEBUG=0 bash -lc 'echo $MODE'
tl sbx ssh  <sandbox-id> --env APP_ENV=dev
```

### Background Processes

**Python:**

```python
proc = sandbox.start_process(
    "python",
    args=["-c", "import time\nfor i in range(5):\n print(i); time.sleep(1)"],
    env=None,
    working_dir=None,
    stdin_mode=None,    # "pipe" to enable write_stdin
    stdout_mode=None,   # "capture" to retain stdout
    stderr_mode=None,
)
# proc.pid, proc.status, proc.stdin_writable
# proc.command, proc.args, proc.started_at, proc.ended_at
# proc.exit_code, proc.signal

procs = sandbox.list_processes()                # -> list[ProcessInfo]

# Stream output as it arrives (SSE)
for event in sandbox.follow_output(proc.pid):
    print(event.line, end="")

import signal
sandbox.send_signal(proc.pid, signal.SIGTERM)   # graceful stop
sandbox.send_signal(proc.pid, signal.SIGKILL)   # force kill
```

**TypeScript:**

```typescript
import { ProcessStatus } from "tensorlake";

const proc = await sandbox.startProcess("python", {
  args: ["-c", "import time\nfor i in range(5):\n print(i); time.sleep(1)"],
});

let info = await sandbox.getProcess(proc.pid);
while (info.status === ProcessStatus.RUNNING) {
  await new Promise((r) => setTimeout(r, 100));
  info = await sandbox.getProcess(proc.pid);
}

console.log((await sandbox.getStdout(proc.pid)).lines);
console.log((await sandbox.getStderr(proc.pid)).lines);
console.log((await sandbox.getOutput(proc.pid)).lines); // combined

for await (const event of sandbox.followOutput(proc.pid)) {
  process.stdout.write(event.line);
}

await sandbox.sendSignal(proc.pid, 15);   // SIGTERM
await sandbox.killProcess(proc.pid);       // dedicated kill (no Python equivalent)
```

### Writing to stdin

Use `stdin_mode="pipe"` (Python) / `stdinMode: "pipe"` (TypeScript) to write to a process's stdin:

```python
proc = sandbox.start_process("python", ["-i"], stdin_mode="pipe")
sandbox.write_stdin(proc.pid, b"print('hello')\n")
sandbox.close_stdin(proc.pid)   # delivers EOF without terminating the process
```

```typescript
const proc = await sandbox.startProcess("python", {
  args: ["-i"],
  stdinMode: "pipe",
});
await sandbox.writeStdin(proc.pid, new TextEncoder().encode("print('hello')\n"));
await sandbox.closeStdin(proc.pid);
```

REST equivalents:
- Stream output: `GET /api/v1/processes/<pid>/output/follow` (SSE — `output` and `eof` events)
- Write stdin: `POST /api/v1/processes/<pid>/stdin` (raw bytes)
- Close stdin: `POST /api/v1/processes/<pid>/stdin/close`
- Send signal: `POST /api/v1/processes/<pid>/signal` (`{"signal": 15}`)
- Kill process: `DELETE /api/v1/processes/<pid>`

### Managed Processes

A background process opts into supervision (auto-restart on crash or failed health check) when you pass a `name`, a `restart` policy, or a `health_check` to `start_process`. Managed processes share the same process API as plain background commands.

**Python:**

```python
from tensorlake.sandbox import (
    ProcessHealthCheck,
    ProcessHealthCheckType,
    RestartPolicy,
    RestartPolicyConfig,
    Sandbox,
)

proc = sandbox.start_process(
    "python",
    args=["-m", "http.server", "8080"],
    user="root",                # username, UID string, "uid:gid", or {"uid":..,"gid":..}; default is tl-user
    name="dev-server",
    restart=RestartPolicyConfig(
        policy=RestartPolicy.ALWAYS,   # NEVER | ON_FAILURE | ALWAYS
        max_restarts=10,
        initial_backoff_ms=500,
        max_backoff_ms=30_000,
    ),
    health_check=ProcessHealthCheck(
        type=ProcessHealthCheckType.HTTP,  # HTTP (local port + optional path) or TCP (local port)
        port=8080,
        path="/",
        interval_ms=1_000,
        failure_threshold=3,
    ),
)
print(proc.managed.status, proc.managed.health_status)

current = sandbox.get_process(proc.pid)
restarted = sandbox.restart_process(proc.pid)   # manual supervised restart
```

**TypeScript:**

```typescript
const proc = await sandbox.startProcess("python", {
  args: ["-m", "http.server", "8080"],
  user: "root",
  name: "dev-server",
  restart: { policy: "always", maxRestarts: 10, initialBackoffMs: 500, maxBackoffMs: 30_000 },
  healthCheck: { type: "http", port: 8080, path: "/", intervalMs: 1_000, failureThreshold: 3 },
});
console.log(proc.managed?.status, proc.managed?.healthStatus);

const current = await sandbox.getProcess(proc.pid);
const restarted = await sandbox.restartProcess(proc.pid);
```

**CLI:** managed-process flags require `--detach` (they start a background process). For blocking one-shot runs, use plain `tl sbx exec` / `sandbox.run(...)`.

```bash
tl sbx exec <id> --detach --name dev-server --restart always --health-http 8080 \
  python -m http.server 8080
tl sbx ps <id> <pid> --json         # inspect the managed process
tl sbx restart <id> <pid>           # restart through the supervisor
tl sbx kill <id> <pid>              # stop and remove from supervision
```

### PTY Sessions

```python
pty = sandbox.create_pty(
    command="/bin/bash",
    args=["-l"],
    env={"TERM": "xterm-256color"},
    working_dir="/workspace",
    cols=80,
    rows=24,
)
# pty exposes: send_input(), resize(), wait(), disconnect(), connect(), kill()
# Subscribe to output: pty.on_data(callback), pty.on_exit(callback)

pty.send_input("pwd\nexit\n")
exit_code = pty.wait()       # block until the PTY exits naturally
pty.kill()                   # idempotent; safe even if already exited
sandbox.terminate()          # final sandbox teardown

# Reconnect to an existing PTY session — only works if the previous
# client called pty.disconnect() (or crashed) rather than pty.kill()
pty = sandbox.connect_pty(session_id, token)
```

```typescript
// TypeScript: onData / onExit can be passed at creation time
const pty = await sandbox.createPty({
  command: "/bin/bash",
  args: ["-l"],
  env: { TERM: "xterm-256color" },
  workingDir: "/workspace",
  rows: 24,
  cols: 80,
  onData: (data) => process.stdout.write(Buffer.from(data)),
  onExit: (exitCode) => console.log("Exited:", exitCode),
});

await pty.sendInput("pwd\nexit\n");
const exitCode = await pty.wait();   // block until PTY exits
await pty.kill();                    // idempotent
await sandbox.terminate();
```

> **Python differs.** `create_pty()` in Python does not accept `on_data` / `on_exit` in its keyword arguments. Attach them after creation via `pty.on_data(callback)` and `pty.on_exit(callback)` instead. TypeScript supports both forms — at-creation in the options object, or post-creation via `pty.onData(...)` / `pty.onExit(...)`.

> **PTY lifecycle: four distinct methods, do not conflate them.**
> - `pty.wait()` — blocks until the PTY exits naturally and returns the exit code. **Does not initiate teardown** on its own; if the shell never exits, `wait()` never returns.
> - `pty.disconnect()` — closes the WebSocket but **leaves the PTY running server-side**. The session can be reattached later via `sandbox.connect_pty(session_id, token)`. Use this when your client is going away but the shell should keep running (e.g., your script may crash and restart).
> - `pty.kill()` — terminates the PTY session over HTTP. After `kill()`, `connect_pty(...)` will fail because the session is gone.
> - `sandbox.terminate()` — tears down the **entire sandbox**, killing any PTYs and processes inside it. There is no `sandbox.destroy()`.
>
> Typical patterns: agent driving a one-shot command → `wait()` → `kill()` → `terminate()`. Agent that needs to survive a client crash → `disconnect()` (no `kill`, no `terminate`) → reconnect later via `connect_pty(session_id, token)`.

### SSH

The sandbox proxy exposes a standard SSH endpoint at `sandbox.tensorlake.ai`. Use the **sandbox id as the SSH username**; your registered SSH key authenticates the connection. You land in `/home/tl-user` as the `tl-user` POSIX account (member of `sudo`); the in-sandbox hostname is `tl-sbx`.

**One-time setup — register your key** (per laptop, not per sandbox):

```bash
tl sbx ssh keys add --name laptop ~/.ssh/id_ed25519.pub
tl sbx ssh keys ls
```

> **`tl sbx ssh keys` requires user-level auth.** It does not work with `TENSORLAKE_API_KEY` (which takes precedence over `tl login`). Unset it for the registration step — `env -u TENSORLAKE_API_KEY tl sbx ssh keys add ...` — or use a fresh shell. After registration you can put `TENSORLAKE_API_KEY` back; SSH itself uses the registered key, not the API key.

**Connect:**

```bash
ssh <sandbox-id>@sandbox.tensorlake.ai
```

To target a specific port (default is the SSH server on `22`), prefix the username with the port: `ssh 8080-<sandbox-id>@sandbox.tensorlake.ai`.

**File transfer** — `scp`, `sftp`, and `rsync` ride the same connection:

```bash
scp ./script.py <sandbox-id>@sandbox.tensorlake.ai:/workspace/
rsync -avz ./src/ <sandbox-id>@sandbox.tensorlake.ai:/workspace/src/
sftp <sandbox-id>@sandbox.tensorlake.ai
```

**Port forwarding** — all four modes work (TCP and UNIX-socket, both directions):

```bash
# Local forward (-L): reach a service inside the sandbox from your laptop
ssh -L 8888:localhost:8000 <sandbox-id>@sandbox.tensorlake.ai

# Dynamic SOCKS (-D): route arbitrary traffic through the sandbox's network namespace
ssh -D 1080 -N -f <sandbox-id>@sandbox.tensorlake.ai

# Remote forward (-R): let processes inside the sandbox reach a service on your laptop
ssh -R 9000:localhost:9000 <sandbox-id>@sandbox.tensorlake.ai
```

**`~/.ssh/config` and VS Code Remote-SSH.** `tl sbx describe <sandbox-id-or-name>` prints an `SSH Config:` block you can paste into `~/.ssh/config`. The equivalent manual entry:

```sshconfig
Host my-sandbox
  HostName sandbox.tensorlake.ai
  User <sandbox-id>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
```

VS Code Remote-SSH, JetBrains Gateway, Cursor — all work the same way. Open `/home/tl-user/workspace` (writable by `tl-user`, persisted across snapshots). `/workspace` is **not** `tl-user`-writable, and `/tmp/*` is writable but excluded from snapshots. While Remote-SSH is connected, the open session counts as proxy traffic and prevents idle-suspend.

`tmux` and `screen` work normally inside the sandbox for sessions that survive an `ssh` disconnect. On auth failure the proxy disconnects with a specific message — key not registered (run `tl sbx ssh keys add`), sandbox not in any of your projects (verify with `tl sbx ls -r`), or sandbox not `running` (resume it). If your client offers multiple keys, constrain it with `IdentitiesOnly yes` / `IdentityFile` to avoid `Permission denied (publickey)`.

For the full "sandbox as portable dev workstation" workflow, see [sandbox_usecases.md → Sandbox as a Dev Environment](sandbox_usecases.md#sandbox-as-a-dev-environment).

### Async SDK (Python)

Python ships an async-native sandbox handle (`AsyncSandbox`) on top of asyncio. **Every method on the sync `Sandbox` handle has a one-to-one async counterpart on `AsyncSandbox` — same names, same parameters, just `async def` and awaited.** Reach for it when fanning out work across many sandboxes (`asyncio.gather`), when your app is already async (FastAPI, aiohttp, agent loops), or when streaming output from many processes concurrently. If you only ever drive one sandbox at a time, the sync `Sandbox` API is equivalent and simpler.

```python
from tensorlake.sandbox import AsyncSandbox

# create + connect
sandbox = await AsyncSandbox.create(cpus=2.0, memory_mb=2048)
# attach to an existing one
sandbox = await AsyncSandbox.connect("my-env")
```

`AsyncSandbox` is also an async context manager — `async with` terminates the sandbox automatically:

```python
async with await AsyncSandbox.create(cpus=2.0, memory_mb=2048) as sandbox:
    result = await sandbox.run("python", ["-c", "print('hello')"])
    print(result.stdout)
# sandbox terminated here
```

Fan-out with `asyncio.gather`:

```python
import asyncio
from tensorlake.sandbox import AsyncSandbox

async def evaluate(prompt: str) -> str:
    async with await AsyncSandbox.create(cpus=1.0, memory_mb=1024) as sandbox:
        result = await sandbox.run("python", ["-c", prompt])
        return result.stdout

outputs = await asyncio.gather(
    evaluate("print(2+2)"),
    evaluate("print(sum(range(100)))"),
    evaluate("import math; print(math.pi)"),
)
```

> **`sandbox_id` on a freshly connected handle.** Unlike sync `Sandbox.sandbox_id`, which transparently fetches sandbox info on first access, the async `AsyncSandbox.sandbox_id` cannot block on a network call. After `AsyncSandbox.connect(...)` call `await sandbox.info()` (or any awaited method that resolves the sandbox, like `status()`) once before reading `sandbox.sandbox_id`.

Background processes mirror the sync API; `follow_output(pid)` blocks until the process exits and returns an iterable of captured events:

```python
proc = await sandbox.start_process("python", ["-c", "for i in range(5): print(i)"])
events = await sandbox.follow_output(proc.pid)
for event in events:
    print(event.line, end="")
```

For long-running processes you want to stop yourself, send a signal directly — do not `follow_output` first (it blocks until exit):

```python
import signal
proc = await sandbox.start_process("python", ["-m", "http.server", "8080"])
# ... do work ...
await sandbox.send_signal(proc.pid, signal.SIGTERM)
```

File ops, suspend/resume, and checkpoint all have the same shape:

```python
await sandbox.write_file("/workspace/data.csv", b"name,score\nAlice,95\n")
content = await sandbox.read_file("/workspace/data.csv")

# suspend/resume require a named sandbox
sandbox = await AsyncSandbox.create(name="my-env", cpus=1.0)
await sandbox.suspend()
await sandbox.resume()

# checkpoint works on any sandbox, including ephemeral
snapshot = await sandbox.checkpoint()
restored = await AsyncSandbox.create(snapshot_id=snapshot.snapshot_id)
```

> **TypeScript is async by default** — there is no separate `AsyncSandbox`; the existing `Sandbox` methods all return Promises.

## Sandbox Images

A sandbox image is a project-scoped, named snapshot built from a base image plus build steps. Three definition formats — Python DSL, TypeScript DSL, Dockerfile — and three build paths.

### Define an Image

**Python:**

```python
from tensorlake import Image

image = (
    Image(name="data-tools-image", base_image="tensorlake/ubuntu-systemd")
    .copy("requirements.txt", "/tmp/requirements.txt")
    .run("apt-get update && apt-get install -y python3 python3-pip")
    .run("python3 -m pip install --break-system-packages -r /tmp/requirements.txt")
    .run("mkdir -p /workspace/cache")
    .env("APP_ENV", "prod")
    .workdir("/workspace")
)

image.build(registered_name="data-tools-image")
```

**TypeScript:**

```typescript
import { Image } from "tensorlake";

const image = new Image({
  name: "data-tools-image",
  baseImage: "tensorlake/ubuntu-systemd",
})
  .copy("requirements.txt", "/tmp/requirements.txt")
  .run("apt-get update && apt-get install -y python3 python3-pip")
  .run("python3 -m pip install --break-system-packages -r /tmp/requirements.txt")
  .run("mkdir -p /workspace/cache")
  .env("APP_ENV", "prod")
  .workdir("/workspace");

await image.build({ registeredName: "data-tools-image", contextDir: "." });
```

**Dockerfile:**

```dockerfile
FROM tensorlake/ubuntu-systemd

RUN apt-get update && apt-get install -y python3 python3-pip
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --break-system-packages -r /tmp/requirements.txt
RUN mkdir -p /workspace/cache
ENV APP_ENV=prod
WORKDIR /workspace
```

**Inline pip install (no `requirements.txt`):**

For ad-hoc package lists, chain everything in `.run(...)` steps. The base Ubuntu images ship a PEP 668-managed system Python, so `pip install` requires `--break-system-packages` (or an explicit venv) — do **not** sidestep this with `ensurepip` and a bare `pip install`, and do **not** assume a deadsnakes Python is needed.

```python
from tensorlake import Image
from tensorlake.sandbox import Sandbox

image = (
    Image(name="etl-tools", base_image="tensorlake/ubuntu-minimal")
    .run("apt-get update && apt-get install -y python3 python3-pip")
    .run("python3 -m pip install --break-system-packages pandas pyarrow duckdb")
)
image.build(registered_name="etl-tools")

sandbox = Sandbox.create(image="etl-tools", cpus=4.0, memory_mb=8192)
result = sandbox.run("python3", ["-c", "import pandas, pyarrow, duckdb; print('ok')"])
print(result.stdout, result.exit_code)
```

### Build / Register the Image

Build defaults are `cpus=2.0`, `memory_mb=4096`, and a generated root disk of `10240` MiB (10 GiB). Resources are passed to the build call (not the `Image(...)` constructor). `disk_mb` / `diskMb` sets the root disk of sandboxes created from the registered image; `builder_disk_mb` / `builderDiskMb` only sizes the temporary builder sandbox.

**Python:**

```python
image.build(registered_name="data-tools-image")        # use defaults

image.build(
    registered_name="data-tools-image",
    cpus=4.0,
    memory_mb=4096,
    disk_mb=25600,                              # 25 GiB root disk for launched sandboxes
    builder_disk_mb=32768,                      # 32 GiB disk for the builder sandbox only
)
```

**TypeScript:**

```typescript
await image.build({
  registeredName: "data-tools-image",
  cpus: 4.0,
  memoryMb: 4096,
  diskMb: 25600,
  builderDiskMb: 32768,
  contextDir: ".",        // resolves relative copy()/add() sources in SDK builds
});
```

**CLI (Dockerfile only):**

```bash
tl sbx image create ./Dockerfile --registered-name data-tools-image
tl sbx image create ./Dockerfile \
  --registered-name data-tools-image \
  --cpus 4 --memory 4096 --disk_mb 25600 --builder_disk_mb 32768
```

The positional argument is a Dockerfile path. The `-n/--registered-name` flag sets the registered name; if omitted, it defaults to the parent directory when the file is named `Dockerfile`, otherwise the file stem. Names must be unique within a project. Dockerfile builds use the Dockerfile's parent directory as the build context.

> **Disk size carries over to launched sandboxes.** Use a larger build-time `disk_mb` when you want to bake big dependencies into the image without forcing every consumer to override `disk_mb` at `Sandbox.create()` time. CPU and memory are *not* inherited — they fall back to `Sandbox.create()`'s own `cpus` / `memory_mb` (defaults `1.0` / `1024`) unless explicitly set at launch.

Before building, run `tl login` and `tl init` (or `npx tl init`) to select the target project.

**Register an existing snapshot as an image.** If you already have a `Completed` filesystem snapshot (with a durable `snapshot_uri`), name it without rebuilding:

```bash
tl sbx image register data-tools-image snap_01HX... --dockerfile ./Dockerfile
```

The first positional is the image name, the second the snapshot ID; `--dockerfile` is stored alongside for `tl sbx image describe`. Add `--public` to make it namespace-resolvable.

`tl sbx image ls` lists every image registered in the current project; `tl sbx image describe <name-or-template-id>` shows the Dockerfile, snapshot ID, and image size.

### Import an Image from a Registry

To use an existing registry image as a sandbox image *as-is* — no Dockerfile, no build steps — import it directly. Tensorlake pulls the referenced image's layers straight into the sandbox root filesystem (bypassing the Docker daemon); the reference is always pulled fresh. If you need to layer extra packages or files on top, write a Dockerfile with it as a `FROM` base instead (see [Base Images → OCI base images](#base-images)).

```bash
tl sbx image import pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime --registered-name pytorch-runtime
```

```python
from tensorlake import import_sandbox_image

import_sandbox_image(
    "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime",
    registered_name="pytorch-runtime",
)
```

```typescript
import { importSandboxImage } from "tensorlake";

await importSandboxImage(
  "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime",
  { registeredName: "pytorch-runtime" },
);
```

If you omit the registered name, it defaults to the reference's last path segment with any tag/digest stripped (`pytorch/pytorch:2.4.1` → `pytorch`). Imports honor the same `docker login` credentials, CPU/memory/disk options, and `--public` / `is_public` visibility as builds.

> You can't launch a sandbox directly from a raw Docker/registry reference — it must be registered as a Tensorlake image first. `tl sbx image import` is the one-step way to do that for an unmodified image.

### Public Images

A registered image is namespace-scoped by default. Pass `--public` (CLI), `is_public=True` (Python), or `isPublic: true` (TypeScript) to make the image name resolvable from any namespace — this is how the `tensorlake/*` base images work. Public names must be globally unique for the registry; collisions are rejected at creation time.

```bash
tl sbx image create ./Dockerfile --registered-name shared-base --public
```

```python
image.build(registered_name="shared-base", is_public=True)
```

```typescript
await image.build({ registeredName: "shared-base", isPublic: true, contextDir: "." });
```

### Base Images

| Base Image                    | Description                                                                                              |
|-------------------------------|----------------------------------------------------------------------------------------------------------|
| `tensorlake/ubuntu-minimal`   | Default. Minimal Ubuntu, no systemd, boots in hundreds of ms.                                            |
| `tensorlake/ubuntu-systemd`   | Ubuntu with systemd, supports Docker/K8s inside the sandbox.                                             |
| `tensorlake/ubuntu-vnc`       | Desktop-enabled (XFCE + TigerVNC + Firefox) — use with `sandbox.connect_desktop()` for computer-use.     |
| `tensorlake/debian-minimal`   | Minimal Debian 13.                                                                                       |

Use the fully-qualified names (`tensorlake/...`) in `base_image=` / `baseImage:`, in `FROM`, and in `image=` when launching from a base image.

**OCI base images.** You are not limited to `tensorlake/*` bases. The build base can be any standard OCI image reference — `python:3.12-slim`, `debian:bookworm-slim`, `node:22-alpine`, `ghcr.io/...`, `public.ecr.aws/...`, etc. The first build from a new OCI base takes longer because Tensorlake fetches and prepares the upstream image; subsequent sandbox launches use the registered snapshot.

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl
RUN python3 -m pip install pandas pyarrow duckdb
WORKDIR /workspace
```

```bash
tl sbx image create ./Dockerfile --registered-name py-data-tools
```

**Private registries.** Credentials are read from `~/.docker/config.json` (or `$DOCKER_CONFIG/config.json`). Any registry that works with `docker login` works here — Docker Hub, GHCR, ECR, GCR, Quay, self-hosted. In CI, make sure the runner has a populated Docker config before running `tl sbx image create`.

### Image Builder Methods (chainable)

- `.run(command)` — execute shell command during build
- `.env(key, value)` — set environment variable
- `.copy(src, dest)` — copy file from local build context
- `.add(src, dest)` — add file from local build context
- `.workdir(path)` — set working directory (Python and TypeScript)

### Supported Build Operations

Sandbox image builds support most standard Dockerfile commands, with these limitations:

- `$VAR` / environment-variable substitution does **not** work in `FROM` lines.
- `ONBUILD` instructions are ignored and do not run during child image builds.
- These commands build fine but have **no effect when running sandboxes** from the image (metadata only): `ONBUILD`, `SHELL`, `EXPOSE`, `HEALTHCHECK`, `LABEL`, `STOPSIGNAL`, `VOLUME`.

`RUN`, `WORKDIR`, `ENV`, `COPY`, and `ADD` are materialized into the snapshot. (Note: process-level `user=` selection at `start_process` is the supported way to run as a non-default user — see [Managed Processes](#managed-processes).)

### Launching Sandboxes from Custom Images

**Python:**

```python
sandbox = Sandbox.create(
    image="data-tools-image",
    cpus=4.0,
    memory_mb=4096,
    timeout_secs=1800,
)
result = sandbox.run("python3", ["-c", "import pandas; print('ready')"])
```

**TypeScript:**

```typescript
const sandbox = await Sandbox.create({
  image: "data-tools-image",
  cpus: 4.0,
  memoryMb: 4096,
  timeoutSecs: 1800,
});
```

**CLI:**

```bash
tl sbx create --image data-tools-image
tl sbx create --image data-tools-image --cpus 4.0 --memory 4096 --timeout 1800
```

`tl sbx image describe <name>` shows the registered Dockerfile and snapshot metadata for a sandbox image.

### Running Docker Inside a Sandbox

Docker requires systemd, so launch with the `ubuntu-systemd` base image and install Docker from the official Ubuntu repository inside the sandbox. See [sandboxes/docker.md](https://docs.tensorlake.ai/sandboxes/docker.md) for the full install script and a `docker run hello-world` verification step.

## Networking

| Python Parameter       | TypeScript Parameter        | Type        | Default | Description                                                  |
|------------------------|-----------------------------|-------------|---------|--------------------------------------------------------------|
| `allow_internet_access`| `allowInternetAccess`       | `bool`      | `True`  | Global outbound internet toggle                              |
| `deny_out`             | `denyOut`                   | `list[str]` | `[]`    | Blocked outbound destinations (domains/IPs/CIDRs)            |
| `allow_out`            | `allowOut`                  | `list[str]` | `[]`    | Allowed outbound destinations (when internet disabled)       |

These are parameters on `Sandbox.create()`. Port exposure (`exposed_ports`, `allow_unauthenticated_access`) is a separate post-create operation — see [Port Exposure](#port-exposure).

### Public URLs

- Management API: `https://<sandbox-id-or-name>.sandbox.tensorlake.ai` (port `9501`, always authenticated)
- User services: `https://<port>-<sandbox-id-or-name>.sandbox.tensorlake.ai`
- Supports HTTP/1.1, HTTP/2, WebSocket upgrades, gRPC

The hostname accepts either the sandbox ID or a sandbox name.

### Port Exposure

Prefer calling `update()` on the `Sandbox` handle:

```python
sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
sandbox.update(exposed_ports=[])  # remove all exposed ports
```

The legacy `SandboxClient` form still works:

```python
from tensorlake.sandbox import SandboxClient

client = SandboxClient()
client.expose_ports("my-env", [8080], allow_unauthenticated_access=False)
client.unexpose_ports("my-env", [8080])
```

```typescript
// Preferred: call update() on the Sandbox handle
await sandbox.update({ exposedPorts: [8080], allowUnauthenticatedAccess: false });
await sandbox.update({ exposedPorts: [] });   // remove all exposed ports

// Or via SandboxClient when you only have an id/name
const client = new SandboxClient();
await client.exposePorts("my-env", [8080], { allowUnauthenticatedAccess: false });
await client.unexposePorts("my-env", [8080]);
```

```bash
tl sbx port expose <sandbox-id> 8080
tl sbx port ls <sandbox-id>
tl sbx port rm <sandbox-id> 8080
```

The CLI `tl sbx port expose` workflow sets both `exposed_ports` and `allow_unauthenticated_access=true`, making traffic to the user port publicly reachable from the internet without TensorLake auth. Use `SandboxClient().expose_ports(..., allow_unauthenticated_access=False)` for the authenticated-only mode.

Idle auto-suspend and auto-resume for named sandboxes are covered in [sandbox_persistence.md](sandbox_persistence.md#idle-auto-suspend-and-auto-resume).

### Outbound Internet Control

```python
# Disable outbound internet entirely (good for untrusted code)
sandbox = Sandbox.create(allow_internet_access=False)

# Disable internet but allow specific destinations
sandbox = Sandbox.create(
    allow_internet_access=False,
    allow_out=["10.0.0.0/8", "8.8.8.8"],
)

# Internet on, but block specific destinations
sandbox = Sandbox.create(deny_out=["example.com"])
```

`allow_out` rules are evaluated before `deny_out`. Values may be IPs, CIDR ranges, or domain names.

### Local Tunnels

Tunnels forward a local TCP port on your laptop to a port inside a running sandbox over an authenticated WebSocket through the sandbox proxy. Your TensorLake credentials authenticate every connection — the remote port stays private to your account, **no entry in `exposed_ports` required**.

**When to use a tunnel.** The sandbox proxy at `*.sandbox.tensorlake.ai` only speaks HTTP, WebSocket, gRPC, and SSH. Anything else — VNC's RFB protocol, the Postgres wire protocol, MySQL, Redis RESP, MongoDB, custom binary protocols — needs a tunnel because the proxy cannot frame those bytes. You can also use a tunnel for HTTP/WS/gRPC traffic when you'd rather keep the port reachable only at `127.0.0.1` instead of through a public sandbox URL (e.g., driving Chrome's DevTools Protocol from your laptop). Tunnels and `exposed_ports` are independent — a tunnel works even when the port is not exposed.

**CLI** (simplest; works for any language):

```bash
# remote 5901 → local 15901 (default local port matches remote)
tl sbx tunnel <sandbox-id-or-name> 5901 --listen-port 15901

# default: local port matches remote
tl sbx tunnel <sandbox-id-or-name> 9222
```

The command keeps running and prints connection events. `Ctrl+C` stops the tunnel; the sandbox keeps running. The local listener is per-process — to share one tunnel across two clients, run the CLI once and connect both to the same `localhost:<port>`.

**TypeScript SDK:**

```typescript
import { Sandbox } from "tensorlake";

const sandbox = await Sandbox.connect({ sandboxId: "<sandbox-id>" });
const tunnel = await sandbox.createTunnel(5901, { localPort: 15901 });
const { host, port } = tunnel.address();
console.log(`tunnel listening on ${host}:${port}`);
// ... use it ...
await tunnel.close();
```

`createTunnel(remotePort, options)` returns a `TcpTunnel`. Useful options: `localHost` (defaults to `127.0.0.1`), `localPort` (pass `0` for an ephemeral port and read it back from `tunnel.address()`), `connectTimeout` (seconds to wait per WebSocket connection, defaults to `10`).

**Python SDK** does not yet ship a native tunnel helper — drive the CLI from a subprocess:

```python
import subprocess

tunnel = subprocess.Popen(
    ["tl", "sbx", "tunnel", "<sandbox-id>", "9222", "-l", "9222"],
)
try:
    # use http://127.0.0.1:9222 from your code
    ...
finally:
    tunnel.terminate()
    tunnel.wait()
```

**Common patterns:**

| Inside sandbox                     | Local port | Client                                                       |
|------------------------------------|------------|--------------------------------------------------------------|
| `5901` (TigerVNC)                  | `15901`    | macOS Screen Sharing, RealVNC, TigerVNC, Remmina             |
| `9222` (Chrome DevTools Protocol)  | `9222`     | Playwright `connect_over_cdp`, Puppeteer, raw WebSocket CDP  |
| `5432` (Postgres)                  | `5432`     | `psql`, DBeaver, TablePlus                                   |
| `3000` (dev server)                | `3000`     | Browser at `http://localhost:3000`                           |

**Troubleshooting:**

- **`Connection refused` from the local end.** The remote service inside the sandbox is not yet listening. Check with `tl sbx exec <id> -- bash -lc 'ss -ltnp'` and retry.
- **`502 Bad Gateway` during handshake.** The workload has not finished booting; the proxy returns 502 when nothing is listening on the remote port. Wait a few seconds and reconnect.
- **WebSocket auth failures.** Confirm `tl whoami` shows the right org/project, or that `TENSORLAKE_API_KEY` is set in the shell running the CLI.

## Data Models

### SandboxInfo

| Field                          | Type                     | Description                                          |
|--------------------------------|--------------------------|------------------------------------------------------|
| `sandbox_id` / `sandboxId`     | `str`                    | Server-assigned UUID                                 |
| `name`                         | `str \| None`            | Name, or `None` for ephemeral                        |
| `namespace`                    | `str`                    | Namespace                                            |
| `status`                       | `SandboxStatus`          | Lowercase enum values: `"pending" \| "running" \| "snapshotting" \| "suspending" \| "suspended" \| "terminated"` |
| `image`                        | `str \| None`            | Container image used                                 |
| `resources`                    | `ContainerResourcesInfo` | `.cpus`, `.memory_mb` (camelCase in TS)              |
| `timeout_secs`                 | `int \| None`            | Timeout in seconds                                   |
| `exposed_ports`                | `list[int] \| None`      | User ports routed by the proxy                       |
| `allow_unauthenticated_access` | `bool`                   | Whether exposed user ports skip TensorLake auth      |
| `ingress_endpoint`             | `str \| None`            | Base ingress origin for the sandbox's current placement |
| `sandbox_url`                  | `str \| None`            | Management URL (port `9501`) derived from `ingress_endpoint` |
| `entrypoint`                   | `list[str] \| None`      | Custom entrypoint command                            |
| `network`                      | `NetworkConfig \| None`  | Outbound config (`allow_internet_access`, `allow_out`, `deny_out`) |
| `created_at`                   | `datetime \| None`       | Creation timestamp                                   |
| `terminated_at`                | `datetime \| None`       | Termination timestamp                                |

### CommandResult

```python
result.stdout       # str
result.stderr       # str
result.exit_code    # int
```

```typescript
result.stdout       // string
result.stderr       // string
result.exitCode     // number
```

### ProcessInfo

`pid`, `command`, `args`, `status`, `exit_code`, `signal`, `started_at`, `ended_at`, `stdin_writable`.

### SnapshotInfo

`snapshot_id` / `snapshotId`, `sandbox_id`, `snapshot_type` (`"memory" | "filesystem"` — `SnapshotType` enum), `status` (`SnapshotStatus`: `"in_progress" | "completed" | "failed"`), `size_bytes`, `rootfs_disk_bytes`, `base_image`, `created_at`.

### Process Status / Mode Enums

Imported from `tensorlake.sandbox.models` (or `tensorlake.sandbox`):

- **`ProcessStatus`** — `running`, `exited`, `signaled`
- **`StdinMode`** — `closed` (default), `pipe`
- **`OutputMode`** — `capture`, `discard`

## CLI Quick Reference

```bash
tl sbx create                            # Create ephemeral sandbox
tl sbx create my-env                     # Create named sandbox
tl sbx create --image data-tools-image --cpus 2 --memory 2048 --timeout 600
tl sbx ls                                # List active sandboxes
tl sbx ls --running                      # Running sandboxes only
tl sbx ls --all                          # Include suspended/terminated
tl sbx ls -r                             # Running sandboxes in active project (for SSH troubleshooting)
tl sbx exec <id> <command>               # Execute command
tl sbx exec <id> --detach --name N --restart always --health-http 8080 <cmd>  # Managed process
tl sbx run <command>                     # Create, run, teardown
tl sbx run --keep <command>              # One-shot run but keep the sandbox afterwards
tl sbx ps <id> <pid> --json              # Inspect a managed process
tl sbx restart <id> <pid>                # Restart a managed process via supervisor
tl sbx kill <id> <pid>                   # Stop + remove a managed process from supervision
tl sbx ssh <id>                          # Interactive shell
tl sbx cp file.txt <id>:/path            # Upload file (file-only, no dirs)
tl sbx cp <id>:/path ./local             # Download file
tl sbx checkpoint <id>                   # Create snapshot from running sandbox
tl sbx checkpoint <id> --timeout 600
tl sbx clone <id>                        # Snapshot + boot new sandbox in one shot (CLI-only)
tl sbx clone <id> --timeout 600
tl sbx suspend <id>                      # Suspend named sandbox
tl sbx resume <id>                       # Resume named sandbox
tl sbx terminate <id>                    # Terminate sandbox (by name or ID)
tl sbx name <id> <new-name>              # Rename or promote ephemeral → named
tl sbx image create Dockerfile --registered-name NAME   # Build image from Dockerfile
tl sbx image import REF --registered-name NAME          # Register a registry image as-is (no Dockerfile)
tl sbx image register NAME <snapshot-id> --dockerfile ./Dockerfile  # Name an existing snapshot
tl sbx image ls                          # List images registered in the project
tl sbx image describe NAME               # Show registered Dockerfile + metadata
tl sbx port expose <id> 8080             # Expose port (sets allow_unauthenticated_access=true)
tl sbx port ls <id>
tl sbx port rm <id> 8080
```
