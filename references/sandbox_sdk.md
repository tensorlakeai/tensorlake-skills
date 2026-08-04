<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/introduction.md
  - https://docs.tensorlake.ai/sandboxes/quickstart.md
  - https://docs.tensorlake.ai/sandboxes/sdk-reference.md
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
  - https://docs.tensorlake.ai/sandboxes/process-logs.md
  - https://docs.tensorlake.ai/sandboxes/file-operations.md
  - https://docs.tensorlake.ai/sandboxes/environment-variables.md
  - https://docs.tensorlake.ai/sandboxes/networking.md
  - https://docs.tensorlake.ai/sandboxes/tensorlake-images.md
  - https://docs.tensorlake.ai/sandboxes/images.md
  - https://docs.tensorlake.ai/sandboxes/pty-sessions.md
  - https://docs.tensorlake.ai/sandboxes/docker.md
  - https://docs.tensorlake.ai/sandboxes/async.md
  - https://docs.tensorlake.ai/sandboxes/tunnels.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Sandbox SDK Reference

TensorLake Sandboxes are MicroVMs backed by Firecracker and CloudHypervisor. The default image `tensorlake/ubuntu-minimal` starts up in a few hundred milliseconds; `tensorlake/ubuntu-systemd` has a full init system and takes around 1 second to boot. The platform is HIPAA and SOC 2 Type II compliant, supports EU data residency, and offers zero data retention.

Related references:

- Suspend/resume, snapshots, clone/copy, sandbox pools → [sandbox_persistence.md](sandbox_persistence.md)
- Desktop automation / computer use (`tensorlake/ubuntu-vnc`, `connect_desktop()`) → [computer_use.md](computer_use.md)
- Mounting Cloud Volumes and Git repositories into a sandbox → [volumes_and_git.md](volumes_and_git.md)
- SSH-as-dev-environment, agent integrations, Harbor, browser automation → [sandbox_usecases.md](sandbox_usecases.md)

> **Two client surfaces, both current.** `Sandbox` is the handle used for create / connect / run / suspend / resume / checkpoint / files / processes / PTY / logs. `SandboxClient` (`SandboxClient.for_cloud()` in Python, `new SandboxClient()` in TypeScript) is the account-level client documented for **sandbox pools**, **log queries by sandbox ID**, and **`expose_ports` / `unexpose_ports`**. Snapshot creation is `sandbox.checkpoint()`; restore is `Sandbox.create(snapshot_id=...)`.

## Table of Contents

- [Imports](#imports)
- [Managing Sandboxes](#managing-sandboxes)
  - [Create a Sandbox](#create-a-sandbox)
  - [Connect to an Existing Sandbox](#connect-to-an-existing-sandbox)
  - [List, Inspect, Rename](#list-inspect-rename)
  - [Resource Limits and Timeouts](#resource-limits-and-timeouts)
- [Default User and Working Directory](#default-user-and-working-directory)
- [Working in a Sandbox](#working-in-a-sandbox)
  - [Run a Command](#run-a-command)
  - [File Operations](#file-operations)
  - [Environment Variables](#environment-variables)
  - [Background Processes](#background-processes)
  - [Managed Processes](#managed-processes)
  - [Writing to stdin](#writing-to-stdin)
  - [Retained Process Logs](#retained-process-logs)
  - [PTY Sessions](#pty-sessions)
  - [SSH](#ssh)
  - [Async SDK (Python)](#async-sdk-python)
- [Sandbox Images](#sandbox-images)
  - [Tensorlake Managed Images](#tensorlake-managed-images)
  - [Define an Image](#define-an-image)
  - [Build / Register the Image](#build--register-the-image)
  - [Import an Image from a Registry](#import-an-image-from-a-registry)
  - [Inspect and List Registered Images](#inspect-and-list-registered-images)
  - [Public Images](#public-images)
  - [Supported Build Operations](#supported-build-operations)
  - [Running Docker Inside a Sandbox](#running-docker-inside-a-sandbox)
- [Networking](#networking)
  - [Public URLs](#public-urls)
  - [Port Exposure](#port-exposure)
  - [Authenticated Requests](#authenticated-requests)
  - [Outbound Internet Control](#outbound-internet-control)
  - [Local Tunnels](#local-tunnels)
- [Data Models](#data-models)
- [CLI Quick Reference](#cli-quick-reference)

## Imports

**Python:**

```python
from tensorlake.sandbox import Sandbox            # sync handle
from tensorlake.sandbox import AsyncSandbox       # async handle
from tensorlake.sandbox import SandboxClient      # account-level client (pools, logs, port exposure)
```

**TypeScript:**

```typescript
import { Sandbox, SandboxClient } from "tensorlake";
```

The [platform authentication](https://docs.tensorlake.ai/platform/authentication.md) page also shows `from tensorlake import Sandbox` with an explicit `Sandbox.create(api_key=...)`. Every sandbox page uses `from tensorlake.sandbox import Sandbox` with auth taken from `tl login` or `TENSORLAKE_API_KEY`; prefer that form.

## Managing Sandboxes

`Sandbox.create()` returns a live, already-connected handle — no separate `connect()` step.

### Create a Sandbox

**Python:**

```python
# Ephemeral sandbox — no name, cannot be suspended
sandbox = Sandbox.create(
    name=None,             # str | None — pass a value for a named (suspendable) sandbox
    cpus=1.0,              # float, default 1.0
    memory_mb=1024,        # int, default 1024. Must be 1024–8192 MB per CPU core
    disk_mb=10240,         # int, default 10240 (10 GiB). Range 10240–102400 (10–100 GiB)
    timeout_secs=600,      # int, default 600 — idle threshold
    image=None,            # str | None — registered image name or a tensorlake/* image
    snapshot_id=None,      # str | None — restore from a snapshot instead of a fresh boot
    pool_id=None,          # str | None — claim a warm container from a sandbox pool
    entrypoint=None,       # list[str] | None — custom entrypoint command
    allow_internet_access=True,  # bool — see Networking
    allow_out=None,        # list[str] | None — see Networking
    deny_out=None,         # list[str] | None — see Networking
)

named = Sandbox.create(name="my-agent-env", cpus=2.0, memory_mb=2048, timeout_secs=1800)

print(named.sandbox_id)   # server-assigned UUID, e.g. "s7jus08qec4axzgbpq76h"
print(named.name)         # "my-agent-env"
print(named.status)       # Python property; fetches fresh from the server
```

**TypeScript:**

```typescript
const ephemeral = await Sandbox.create({
  cpus: 1.0,
  memoryMb: 1024,
  diskMb: 10240,
  timeoutSecs: 600,
});

const named = await Sandbox.create({
  name: "my-agent-env",
  cpus: 2.0,
  memoryMb: 2048,
  image: "data-tools-image",
});

console.log(named.sandboxId, named.status);
```

Port exposure is a **post-create** operation — see [Port Exposure](#port-exposure). Resources (`cpus`, `memory_mb`, `disk_mb`) are fixed at creation and cannot be changed afterwards; create a new sandbox if you need different resources.

> **`file_systems`.** The [pools page](https://docs.tensorlake.ai/sandboxes/pools.md) notes that "the sandbox `name` and `file_systems` parameters are ignored" when claiming from a pool, which is the only place the sandbox docs name a `file_systems` create parameter. Its accepted value shape is not documented; the documented way to attach a Cloud Volume or repository to a sandbox is `tl fs mount` / `tl git mount` inside the sandbox (see [volumes_and_git.md](volumes_and_git.md)). Don't invent a `file_systems=` payload.

> `secret_names` is **not** a documented `Sandbox.create()` parameter. Sandbox secrets are passed as environment variables per command / per PTY (see [Environment Variables](#environment-variables)). `secrets=[...]` is an Applications `@function()` parameter, not a sandbox one.

### Connect to an Existing Sandbox

**Python:**

```python
# accepts sandbox_id (UUID) or name
sandbox = Sandbox.connect("my-env")
# keyword form is also documented:
sandbox = Sandbox.connect(identifier="my-env")

print(sandbox.sandbox_id)  # always the UUID, even when you connected by name
print(sandbox.name)        # "my-env"

result = sandbox.run("python", ["main.py"])
print(result.stdout)
```

**TypeScript:**

```typescript
// Bare-identifier form (lifecycle + SDK reference pages)
const sandbox = await Sandbox.connect("my-env");

// Options-object form (tunnels page)
const byId = await Sandbox.connect({ sandboxId: "<sandbox-id>" });

console.log(sandbox.sandboxId);        // getter
console.log(sandbox.name);             // getter
console.log(await sandbox.status());   // async method in TS — not a getter
```

### List, Inspect, Rename

**Python:**

```python
for sb in Sandbox.list():                 # -> list[SandboxInfo]
    print(sb.sandbox_id, sb.status)

info = sandbox.info()                     # -> SandboxInfo
print(info.image, info.resources.cpus, info.resources.memory_mb)

# Rename / promote ephemeral → named, or change exposed ports
named_sbx = sandbox.update(name="my-env")
print(named_sbx.name)
sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
```

**TypeScript:**

```typescript
const sandboxes = await Sandbox.list();
for (const sb of sandboxes) {
  console.log(sb.sandboxId, sb.name, sb.status, sb.createdAt);
}

const info = await sandbox.info();
console.log(info.image, info.resources.cpus, info.resources.memoryMb);

await sandbox.update({ name: "my-env" });
await sandbox.update({ exposedPorts: [8080], allowUnauthenticatedAccess: false });
```

`sandbox.update()` is the unified call for name, `exposed_ports`, and `allow_unauthenticated_access`. Assigning a name to an ephemeral sandbox converts it to a named sandbox that supports suspend/resume — same `sandbox_id`, no recreation. If you only have an ID, connect first and chain: `Sandbox.connect("sbx-123").update(name="my-env", exposed_ports=[8080])`.

> Termination is called on the handle: `sandbox.terminate()` / `await sandbox.terminate()`. There is **no `sandbox.destroy()`**. `Terminated` is final and cannot be reversed. `SandboxStatus` values are lowercase: `pending`, `running`, `snapshotting`, `suspending`, `suspended`, `terminated` — compare against `SandboxStatus.SUSPENDED` or the literal `"suspended"`, never `"Suspended"`. In Python, `sandbox.status.value` gives the lowercase string.

### Resource Limits and Timeouts

| Parameter      | Default | Allowed range / notes |
|----------------|---------|------------------------|
| `cpus`         | `1.0`   | float |
| `memory_mb`    | `1024`  | **1024–8192 MB per CPU core** |
| `disk_mb`      | `10240` | 10240–102400 MiB (10–100 GiB). Accepted on fresh creates. With `image` or a **filesystem** `snapshot_id`, it can grow the root disk (growth-only). The CLI flag is `--disk_mb`, in MiB. |
| `timeout_secs` | `600`   | Idle threshold. Plan max: Free (unverified) 1h, Free (verified) 2h, On-Demand (pay-as-you-go) 24h. `timeout_secs=0` requests the **plan maximum**, not "no timeout". |

`timeout_secs` is an **idle threshold, not a wall-clock lifetime**. The sandbox stays running as long as proxied traffic is in flight — an open SSH session, a connected WebSocket PTY, a request to an exposed user port, or any SDK/CLI call. Once nothing has been in flight for `timeout_secs`:

- **Named** sandboxes suspend (filesystem, memory, and running processes preserved).
- **Ephemeral** sandboxes terminate (final; cannot be resumed).

## Default User and Working Directory

By default the `tensorlake/*` images execute commands as **`tl-user`** (UID `1000`, home `/home/tl-user`), a non-root account with passwordless sudo. This differs from typical Docker images that run as root:

- Tools hardcoded to write to root-owned paths such as `/workspace` hit `Permission denied`.
- **Non-interactive commands start from the filesystem root `/`**, so a relative command like `touch output.txt` can fail. Interactive PTY and SSH sessions default to `/home/tl-user`.

Fixes documented on the [Tensorlake Images](https://docs.tensorlake.ai/sandboxes/tensorlake-images.md) page:

```bash
# Run from a writable working directory (working_dir in Python, workingDir in TypeScript)
tl sbx exec <sandbox-id> --workdir /home/tl-user -- touch output.txt

# Escalate with sudo (works in run() too, which always executes as tl-user)
tl sbx exec <sandbox-id> -- sudo apt-get update

# Or run the whole command as root
tl sbx exec <sandbox-id> --user root -- mkdir -p /opt/tools

# Make a system path writable for tl-user
tl sbx exec <sandbox-id> -- bash -c 'sudo mkdir -p /workspace && sudo chown tl-user:tl-user /workspace'
```

For a workload that always needs such a path, bake it into a custom image instead of reconfiguring every sandbox:

```dockerfile
FROM tensorlake/ubuntu-minimal

RUN mkdir -p /workspace && chown tl-user:tl-user /workspace
WORKDIR /workspace
```

> **Two doc statements to reconcile.** [File Operations](https://docs.tensorlake.ai/sandboxes/file-operations.md) lists "use `/workspace` as the default directory for application files" under Best Practices, and its examples read and write `/workspace/...` through `write_file` / `read_file` (which are not subject to the `tl-user` shell context). [Tensorlake Images](https://docs.tensorlake.ai/sandboxes/tensorlake-images.md) states `/workspace` is **not** `tl-user`-writable on the managed images. For shell commands run as the default user, prefer `/home/tl-user/...`, or chown `/workspace` first, or pass `--user root`.
>
> The `tl-user` default applies only when you run a `tensorlake/*` image **directly**. An image you build **from** one runs with whatever `USER` and `WORKDIR` its Dockerfile sets (or Docker defaults). Third-party integrations that assume root and default their workdir to `/workspace/<name>` should be pointed at `/home/tl-user/<name>` or given a custom image.

For SSH/Remote-SSH work, `/home/tl-user/workspace` is writable by `tl-user` and persisted across filesystem snapshots; `/tmp/*` is writable but excluded from snapshots.

## Working in a Sandbox

### Run a Command

**Python:**

```python
result = sandbox.run(
    command,             # str — e.g. "python", "bash"
    args=None,           # list[str] | None
    env=None,            # dict[str, str] | None
    working_dir=None,    # str | None
    timeout=None,        # float | None — seconds
)
result.stdout      # str
result.stderr      # str
result.exit_code   # int
```

**TypeScript:**

```typescript
const result = await sandbox.run("python", {
  args: ["-c", "print('Hello from sandbox!')"],
  env: { MODE: "prod", DEBUG: "0" },
  workingDir: "/home/tl-user",
  timeout: 10,
});
console.log(result.stdout, result.stderr, result.exitCode);
```

Shell features (pipes, redirects, chaining) require wrapping in bash:

```python
sandbox.run("bash", ["-c", "ls -la /workspace | grep '.py' | wc -l"])
sandbox.run("bash", ["-c", "cd /workspace && pip install -r requirements.txt && python main.py"])
```

> **Canonical forms — don't invent variants.** For LLM tool-use the idiom is `sandbox.run("python", ["-c", code])`. There is no `sandbox.exec()`, `sandbox.python()`, `sandbox.eval()`, or `sandbox.repl()`. The result object exposes exactly `stdout`, `stderr`, `exit_code` (Python) / `stdout`, `stderr`, `exitCode` (TypeScript) — not `.output`, `.result`, `.logs`, `.stream`, or `.lines`. **The Python field is `exit_code`, NOT `returncode`.** For live stdout from a long-running process use `start_process` + `follow_output`.
>
> The [Orchestration + Sandboxes](https://docs.tensorlake.ai/applications/sandboxes.md) page contains an illustrative snippet using `sandbox.execute(...)`, `result.output`, and `sandbox_client.delete(...)`. Those symbols appear nowhere in the Sandbox SDK reference — use `sandbox.run(...)`, `result.stdout`, and `sandbox.terminate()`.

Error handling is by exit code; `run()` does not raise on non-zero:

```python
result = sandbox.run("python", ["-c", "import nonexistent_module"])
if result.exit_code != 0:
    print(f"failed ({result.exit_code}): {result.stderr}")
```

### File Operations

**Python:**

```python
sandbox.write_file("/workspace/data.csv", b"name,score\nAlice,95\nBob,87")

content = sandbox.read_file("/workspace/data.csv")     # bytes-like
print(bytes(content).decode("utf-8"))

entries = sandbox.list_directory("/workspace")
for entry in entries.entries:                          # .entries[].name, .is_dir, .size
    print(entry.name, entry.is_dir, entry.size)

sandbox.delete_file("/workspace/data.csv")
```

**TypeScript:**

```typescript
await sandbox.writeFile(
  "/workspace/data.csv",
  new TextEncoder().encode("name,score\nAlice,95\nBob,87"),
);

const content = await sandbox.readFile("/workspace/data.csv");
console.log(new TextDecoder().decode(content));

const listing = await sandbox.listDirectory("/workspace");
for (const entry of listing.entries) {
  console.log(entry.name, entry.size ?? 0);
}

await sandbox.deleteFile("/workspace/data.csv");
```

Directory creation and moves go through `run()` — there is no `mkdir`/`mv` file API:

```python
sandbox.run("mkdir", ["-p", "/workspace/src/components"])
sandbox.run("mv", ["/workspace/old.txt", "/workspace/new.txt"])
```

**CLI — `tl sbx cp`** mirrors `scp` syntax; the `<sandbox-id-or-name>:/path` side is the sandbox:

```bash
tl sbx cp ./data.csv <sandbox-id>:/workspace/input.csv     # upload
tl sbx cp <sandbox-id>:/workspace/output.parquet ./out.pq  # download
```

> **`tl sbx cp` is file-only today** — no recursive directory copy. For directories use the Python SDK, the TypeScript SDK, or the raw file API (e.g. tar locally, `write_file` the archive, extract with `sandbox.run("tar", [...])`). `scp -r` over the [SSH](#ssh) endpoint also works.

**HTTP:** file APIs live on the sandbox management URL (port `9501`, always authenticated):

```
GET/PUT/DELETE https://<sandbox-id-or-name>.sandbox.tensorlake.ai/api/v1/files?path=/workspace/data.csv
GET            https://<sandbox-id-or-name>.sandbox.tensorlake.ai/api/v1/files/list?path=/workspace
```

### Environment Variables

Choose the scope that matches the lifetime you want:

| Scope   | API                                          | Lifetime                         |
|---------|----------------------------------------------|----------------------------------|
| Command | `sandbox.run(..., env={...})`                | Single command execution         |
| Process | `sandbox.start_process(..., env=...)`        | Life of the background process   |
| PTY     | `sandbox.create_pty(..., env=...)`           | Life of the interactive terminal |

```python
sandbox.run("bash", ["-lc", "echo MODE=$MODE"], env={"MODE": "prod"})

pty = sandbox.create_pty(
    command="/bin/bash",
    args=["-l"],
    env={"TERM": "xterm-256color", "APP_ENV": "dev"},
    working_dir="/workspace",
    rows=24,
    cols=80,
)
```

**CLI:** `tl sbx exec`, `tl sbx run`, and `tl sbx ssh` all accept repeated `--env KEY=VALUE`:

```bash
tl sbx exec <sandbox-id> --env MODE=prod --env DEBUG=0 bash -lc 'echo MODE=$MODE DEBUG=$DEBUG'
tl sbx run  --env MODE=prod bash -lc 'echo $MODE'
tl sbx ssh  <sandbox-id> --env APP_ENV=dev --env TERM=screen-256color
```

`tl sbx ssh` always sets PTY defaults such as `TERM` and `COLORTERM=truecolor`; your `--env` values are merged in and can override them. `tl sbx ssh` also takes `--shell`, `--shell-arg`, and `--workdir`.

### Background Processes

**Python:**

```python
proc = sandbox.start_process(
    "python",
    args=["-m", "http.server", "8080"],
    env=None,
    working_dir=None,
    stdin_mode=None,     # "pipe" to enable write_stdin
    stdout_mode=None,    # "capture" to retain stdout
    stderr_mode=None,
)
print(proc.pid)

for p in sandbox.list_processes():          # -> list[ProcessInfo]
    print(p.pid, p.command, p.status)

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
  args: ["-m", "http.server", "8080"],
});

let info = await sandbox.getProcess(proc.pid);
while (info.status === ProcessStatus.RUNNING) {
  await new Promise((r) => setTimeout(r, 100));
  info = await sandbox.getProcess(proc.pid);
}

console.log((await sandbox.getStdout(proc.pid)).lines);
console.log((await sandbox.getStderr(proc.pid)).lines);
console.log((await sandbox.getOutput(proc.pid)).lines);   // combined

for await (const event of sandbox.followOutput(proc.pid)) {
  process.stdout.write(event.line);
}

await sandbox.sendSignal(proc.pid, 15);   // SIGTERM
await sandbox.killProcess(proc.pid);      // dedicated kill (no Python equivalent)
```

REST equivalents on the management URL:

- Start: `POST /api/v1/processes` (`command`, `args`, `env`, `working_dir`, `stdin_mode`, `stdout_mode`, `stderr_mode`)
- List: `GET /api/v1/processes`; get one: `GET /api/v1/processes/<pid>`
- Buffered output: `GET /api/v1/processes/<pid>/stdout` | `/stderr` | `/output` → `{pid, lines, line_count}`
- Follow (SSE): `GET /api/v1/processes/<pid>/stdout/follow` | `/output/follow` → `output` events then `eof`
- Write stdin: `POST /api/v1/processes/<pid>/stdin` (raw bytes); close: `POST .../stdin/close`
- Signal: `POST /api/v1/processes/<pid>/signal` (`{"signal": 15}`); kill: `DELETE /api/v1/processes/<pid>`
- Managed restart: `POST /api/v1/processes/<pid>/restart`

### Managed Processes

A background process opts into supervision (auto-restart on crash or failed health check) when you pass a `name`, a `restart` policy, or a `health_check` to `start_process`.

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
    user="root",                # username, UID string, "uid:gid", or {"uid":..,"gid":..}; default tl-user
    name="dev-server",
    restart=RestartPolicyConfig(
        policy=RestartPolicy.ALWAYS,   # NEVER | ON_FAILURE | ALWAYS  ("never" | "on_failure" | "always")
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

The `managed` object carries `id`, `name`, `status`, `restart_count`, `restart`, `health_status`, and `consecutive_health_failures`.

**CLI:** managed-process flags require `--detach` (they start a background process). For blocking one-shot runs use plain `tl sbx exec` / `sandbox.run(...)`.

```bash
tl sbx exec <id> --detach --name dev-server --restart always --health-http 8080 \
  python -m http.server 8080
tl sbx ps <id> <pid> --json         # inspect the managed process
tl sbx restart <id> <pid>           # restart through the supervisor
tl sbx kill <id> <pid>              # stop and remove from supervision
```

### Writing to stdin

Use `stdin_mode="pipe"` (Python) / `stdinMode: StdinMode.PIPE` (TypeScript):

```python
proc = sandbox.start_process("python", ["-i"], stdin_mode="pipe")
sandbox.write_stdin(proc.pid, b"print('hello')\n")
sandbox.close_stdin(proc.pid)   # delivers EOF without terminating the process
```

```typescript
import { StdinMode } from "tensorlake";

const proc = await sandbox.startProcess("python", {
  args: ["-i"],
  stdinMode: StdinMode.PIPE,
});
await sandbox.writeStdin(proc.pid, new TextEncoder().encode("print('hello')\n"));
await sandbox.closeStdin(proc.pid);
```

### Retained Process Logs

Retained process logs are searchable telemetry for a sandbox — distinct from the per-process output APIs above. Process output is the buffered stream of one tracked process (best when your code needs to wait for or stream a specific process); process logs are retained history for the whole sandbox (best for browsing, filtering, and debugging after the fact). Logs appear once a process writes to stdout/stderr and the pipeline ingests it, so very recent output can lag briefly.

**Python:**

```python
logs = sandbox.get_logs(tail=100, levels=["info", "warn"]).value
for log in logs.logs:
    print(log.body)
    print(log.log_attributes)

processes = sandbox.list_log_processes().value.processes
for process in processes:
    print(process.process_id, process.process_pid, process.process_command)

page = sandbox.get_logs(body="connection refused", tail=100).value
if page.next_token:
    next_page = sandbox.get_logs(body="connection refused", tail=100, next_token=page.next_token).value

# By sandbox ID, without a handle:
from tensorlake.sandbox import SandboxClient
client = SandboxClient.for_cloud()
logs = client.get_logs("<sandbox-id>", levels=["error"], tail=50).value
```

**TypeScript:**

```typescript
const logs = await sandbox.getLogs({ levels: ["info", "warn"], tail: 100 });
for (const log of logs.logs) {
  console.log(log.body);
  console.log(JSON.parse(log.logAttributes));
}

const processes = await sandbox.listLogProcesses();
for (const p of processes.processes) {
  console.log(p.processId, p.processPid, p.processCommand);
}

const page = await sandbox.getLogs({ body: "connection refused", tail: 100 });
if (page.nextToken) {
  await sandbox.getLogs({ body: "connection refused", tail: 100, nextToken: page.nextToken });
}
```

Python `get_logs()` / `list_log_processes()` return a traced wrapper — read `.value`. Filters are `tail`, `levels` / `level`, `process_ids` / `processIds`, `body` (text in the extracted message), and `next_token` / `nextToken`.

**Structured JSON logs.** Print one complete JSON object per line to stdout/stderr and Tensorlake parses it: `message` becomes the displayed body, `level` sets severity when it is one of `trace`/`debug`/`info`/`warn`/`error`, `timestamp` sets the time when parseable, and remaining keys are kept in `logAttributes` (nested objects and arrays preserved, `null` values omitted). With no `message`, `event` is used, with underscores shown as spaces (`"event": "tool_call_started"` → `tool call started`). Malformed JSON is treated as plain text.

**CLI:**

```bash
tl sbx logs <sandbox-id-or-name> --tail 100
tl sbx logs <sandbox-id-or-name> --level error --tail 100
tl sbx logs <sandbox-id-or-name> --body "connection refused" --tail 100
tl sbx logs <sandbox-id-or-name> --tail 25 --json          # timestamps, levels, attributes, pagination
tl sbx logs streams <sandbox-id-or-name>                   # list stable process IDs
tl sbx logs <sandbox-id-or-name> --process-id <process-id> --tail 100
tl sbx logs <sandbox-id-or-name> --tail 100 --next-token "<next-token>"
```

**HTTP** (note the namespace-scoped path, distinct from the sandbox proxy):

```bash
curl "https://api.tensorlake.ai/v1/namespaces/$PROJECT_ID/sandboxes/$SANDBOX_ID/logs?tail=100" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
curl "https://api.tensorlake.ai/v1/namespaces/$PROJECT_ID/sandboxes/$SANDBOX_ID/processes" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

Log levels are numeric over HTTP: `1` trace, `2` debug, `3` info, `4` warn, `5` error, `6` fatal. The `processId` filter uses the **stable process ID**, not necessarily the OS PID — a managed process that restarts gets a new PID but keeps its process ID. Retention follows the environment's log retention policy. Console: project → **Sandboxes** → select sandbox → **Logs** tab.

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

pty.on_data(lambda data: print(data.decode("utf-8"), end=""))
pty.on_exit(lambda code: print(f"\nExited: {code}"))

pty.send_input("pwd\n")
pty.resize(120, 40)
pty.send_input("exit\n")
exit_code = pty.wait()

# Reconnect later — only if the previous client called disconnect() (or crashed), not kill()
pty = sandbox.connect_pty(session_id, token)
```

```typescript
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
await pty.resize(120, 40);
const exitCode = await pty.wait();
await pty.kill();

// Reattach: keep pty.sessionId and pty.token
const again = await sandbox.connectPty(sessionId, token, {
  onData: (data) => process.stdout.write(Buffer.from(data)),
});
```

> **Python differs.** Python's `create_pty()` does not accept `on_data` / `on_exit` keyword arguments — attach them after creation via `pty.on_data(cb)` / `pty.on_exit(cb)`. TypeScript supports both forms.

> **PTY lifecycle: four distinct methods, do not conflate them.**
> - `pty.wait()` — blocks until the PTY exits naturally and returns the exit code. **Does not initiate teardown**; if the shell never exits, `wait()` never returns.
> - `pty.disconnect()` — closes the WebSocket but **leaves the PTY running server-side**. Reattach later via `sandbox.connect_pty(session_id, token)`.
> - `pty.kill()` — terminates the PTY session over HTTP. After `kill()`, `connect_pty(...)` fails; the session is gone.
> - `sandbox.terminate()` — tears down the **entire sandbox**, killing every PTY and process inside it.
>
> `createPty()` / `create_pty()` open the WebSocket and send `READY` for you; use `connectPty()` / `connect_pty()` only to reattach. Closing the WebSocket does not kill the session. Persist the original token if you plan to reconnect — Get and List PTY Session do not return it again. **PTY sessions with no connected clients are killed after 300 seconds of inactivity.**

**Raw HTTP + WebSocket protocol** (management URL, not `api.tensorlake.ai`):

1. `POST /api/v1/pty` with `{command, args, env, working_dir, rows, cols}` → `{session_id, token}`
2. Attach `wss://<sandbox-id>.sandbox.tensorlake.ai/api/v1/pty/<session-id>/ws` with header `X-PTY-Token: <token>` (or `?token=<token>` if headers aren't settable)
3. Frames:

| Direction | Bytes | Meaning |
|---|---|---|
| Client → server | `02` | `READY`: flush buffered output |
| Client → server | `00` + UTF-8 bytes | Terminal input |
| Client → server | `01` + `cols` + `rows` | Resize (each big-endian `u16`) |
| Server → client | `00` + raw bytes | Terminal output |
| Server → client | `03` + 4-byte big-endian signed int | Process exit code |

Examples: `READY` = `02`; `pwd\n` = `00 70 77 64 0a`; resize to 120x40 = `01 00 78 00 28`; exit code 0 = `03 00 00 00 00`. Terminate immediately: `DELETE /api/v1/pty/<session-id>`. Resize can also use the [Resize PTY Session](https://docs.tensorlake.ai/api-reference/v2/pty/resize) endpoint.

### SSH

The sandbox proxy exposes a standard SSH endpoint at `sandbox.tensorlake.ai`. Use the **sandbox ID as the SSH username**; your registered SSH key authenticates. You land in `/home/tl-user` as `tl-user` (member of the `sudo` group); the in-sandbox hostname is `tl-sbx`.

**One-time setup — register your key** (per laptop, not per sandbox; the key is associated with your user across every project you belong to):

```bash
tl login
tl sbx ssh keys add --name laptop ~/.ssh/id_ed25519.pub
tl sbx ssh keys ls
```

> **`tl sbx ssh keys` requires user-level auth.** It does not work with `TENSORLAKE_API_KEY` (which takes precedence over `tl login`). Unset it for the registration step — `env -u TENSORLAKE_API_KEY tl sbx ssh keys add --name laptop ~/.ssh/id_ed25519.pub` — or use a fresh shell. Afterwards you can restore it; SSH itself uses the registered key.

**Connect:**

```bash
ssh <sandbox-id>@sandbox.tensorlake.ai
ssh 8080-<sandbox-id>@sandbox.tensorlake.ai   # target a specific port (default is SSH on 22)
```

**File transfer** — `scp`, `sftp`, and `rsync` ride the same connection:

```bash
scp ./script.py <sandbox-id>@sandbox.tensorlake.ai:/workspace/
scp -r <sandbox-id>@sandbox.tensorlake.ai:/workspace/results ./
sftp <sandbox-id>@sandbox.tensorlake.ai
rsync -avz ./src/ <sandbox-id>@sandbox.tensorlake.ai:/workspace/src/
```

**Port forwarding** — all four standard modes (TCP and UNIX socket, each direction):

```bash
ssh -L 8888:localhost:8000 <sandbox-id>@sandbox.tensorlake.ai   # local forward
ssh -D 1080 -N -f <sandbox-id>@sandbox.tensorlake.ai            # dynamic SOCKS
ssh -R 9000:localhost:9000 <sandbox-id>@sandbox.tensorlake.ai   # remote forward
ssh -L /tmp/local.sock:/tmp/remote.sock <sandbox-id>@sandbox.tensorlake.ai
ssh -R /tmp/remote.sock:/tmp/local.sock <sandbox-id>@sandbox.tensorlake.ai
```

**`~/.ssh/config` and VS Code Remote-SSH.** `tl sbx describe <sandbox-id-or-name>` prints an `SSH Config:` block you can paste into `~/.ssh/config`:

```sshconfig
Host my-sandbox
  HostName sandbox.tensorlake.ai
  User <sandbox-id>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```

VS Code Remote-SSH, JetBrains Gateway, and Cursor all work this way; VS Code installs its server inside the sandbox automatically. Open `/home/tl-user/workspace`. While a Remote-SSH client is connected the session counts as proxy traffic and prevents idle-suspend; after disconnect a **named** sandbox suspends after `timeout_secs`, and `tl sbx resume <name>` brings it back with the same sandbox ID and `Host` entry.

`tmux` and `screen` work normally for sessions that survive an `ssh` disconnect.

**Troubleshooting** — auth failures disconnect with one of three specific messages: key not registered (run `tl sbx ssh keys add ~/.ssh/id_ed25519.pub`), sandbox not in any of your projects (verify with `tl sbx ls -r`), or sandbox not running (`tl sbx resume <id>`). If your client offers multiple keys you may see the banner followed by `Permission denied (publickey)` — constrain it:

```sshconfig
Host *.tensorlake.ai
  IdentitiesOnly yes
  IdentityFile ~/.ssh/id_ed25519
```

`tl sbx ssh <id>` is a separate CLI shortcut that opens an interactive PTY over the WebSocket flow. It requires an interactive terminal, auto-resumes a suspended sandbox, and does **not** support port forwarding or file transfer — use real `ssh`/`scp` for those.

### Async SDK (Python)

Python ships an async-native handle, `AsyncSandbox`. **Every method on the sync `Sandbox` handle has a one-to-one async counterpart — same names, same parameters, just awaited.** Reach for it when fanning out across many sandboxes (`asyncio.gather`), when your app is already async (FastAPI, aiohttp, agent loops), or when streaming output from many processes concurrently.

```python
import asyncio
from tensorlake.sandbox import AsyncSandbox

sandbox = await AsyncSandbox.create(cpus=2.0, memory_mb=2048)
sandbox = await AsyncSandbox.connect("my-env")
```

`AsyncSandbox` is an async context manager — `async with` terminates the sandbox on exit:

```python
async with await AsyncSandbox.create(cpus=2.0, memory_mb=2048) as sandbox:
    result = await sandbox.run("python", ["-c", "print('hello')"])
    print(result.stdout)
# sandbox terminated here
```

Fan-out:

```python
async def evaluate(prompt: str) -> str:
    async with await AsyncSandbox.create(cpus=1.0, memory_mb=1024) as sandbox:
        result = await sandbox.run("python", ["-c", prompt])
        return result.stdout

outputs = await asyncio.gather(*(evaluate(p) for p in prompts))
```

> **`sandbox_id` on a freshly connected handle.** Unlike sync `Sandbox.sandbox_id`, which transparently fetches info on first access, `AsyncSandbox.sandbox_id` cannot block on a network call. After `AsyncSandbox.connect(...)`, `await sandbox.info()` (or any awaited method that resolves the sandbox, like `status()`) once before reading `sandbox.sandbox_id`.

Background processes mirror the sync API; `follow_output(pid)` blocks until the process exits and returns an iterable of captured events:

```python
proc = await sandbox.start_process("python", ["-c", "for i in range(5): print(i)"])
events = await sandbox.follow_output(proc.pid)
for event in events:
    print(event.line, end="")
```

For long-running processes you intend to stop yourself, signal directly — do **not** `follow_output` first (it blocks until exit):

```python
import signal
proc = await sandbox.start_process("python", ["-m", "http.server", "8080"])
await sandbox.send_signal(proc.pid, signal.SIGTERM)
```

File ops, suspend/resume, and checkpoint have the same shape; async file results are traced wrappers, so read `.value`:

```python
await sandbox.write_file("/workspace/data.csv", b"name,score\nAlice,95\n")
content = await sandbox.read_file("/workspace/data.csv")
print(content.value.decode("utf-8"))

listing = await sandbox.list_directory("/workspace")
for entry in listing.value.entries:
    print(entry.name, entry.is_dir, entry.size)

# suspend/resume require a named sandbox
sandbox = await AsyncSandbox.create(name="my-env", cpus=1.0)
await sandbox.suspend()
await sandbox.resume()

# checkpoint works on any sandbox, including ephemeral
snapshot = await sandbox.checkpoint()
restored = await AsyncSandbox.create(snapshot_id=snapshot.snapshot_id)
```

`AsyncSandboxClient` exposes the pool methods as coroutines — see [sandbox_persistence.md](sandbox_persistence.md#sandbox-pools).

> **TypeScript is async by default** — there is no separate `AsyncSandbox`; the `Sandbox` methods already return Promises.

## Sandbox Images

### Tensorlake Managed Images

Managed, globally available in every project, no build or registration step. Creating a sandbox without `image` uses `tensorlake/ubuntu-minimal`.

| Image | Description |
|---|---|
| `tensorlake/ubuntu-minimal` | **Default.** Minimal Ubuntu, systemd excluded. Lowest cold-start latency. |
| `tensorlake/ubuntu-systemd` | Ubuntu with systemd. Required for service management inside the sandbox (Docker, Kubernetes). |
| `tensorlake/debian-minimal` | Base Debian 13, minimal profile. |
| `tensorlake/ubuntu-vnc` | Desktop-enabled Ubuntu derived from `ubuntu-systemd`, preinstalled with XFCE, TigerVNC, and Firefox. Where desktop automation is enabled. See [computer_use.md](computer_use.md). |

Use the fully-qualified `tensorlake/...` name in `image=`, in `base_image=` / `baseImage:`, and in `FROM`.

**Python packages.** Tensorlake Ubuntu and Debian images ship a **PEP 668-managed** system Python. `pip install` requires `--break-system-packages` unless you create a virtual environment; omitting it produces `externally-managed-environment`:

```python
sandbox.run("python3", ["-m", "pip", "install", "--break-system-packages", "pandas", "pyarrow", "duckdb"])
```

> Do **not** sidestep PEP 668 by switching Python versions — `python3.11 -m pip install ...` or another alternate system Python can produce the same error. Use `--break-system-packages` with the system `python3`, or an explicit venv. For repeatable installs, put packages in `requirements.txt` and install during an image build.

See also [Default User and Working Directory](#default-user-and-working-directory).

### Define an Image

Any image the build can pull can be the `FROM` base: a `tensorlake/*` image, a public OCI reference (`python:3.12-slim`, `debian:bookworm-slim`, `node:22-alpine`, `ghcr.io/...`, `public.ecr.aws/...`), or a private registry image. The first build from a new OCI base takes longer because the upstream image must be fetched and prepared.

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

image.build(registered_name="data-tools-image", context_dir=".")
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
ENV APP_ENV=prod
WORKDIR /workspace
```

Chainable builder methods: `.run(command)`, `.env(key, value)`, `.copy(src, dest)`, `.add(src, dest)`, `.workdir(path)`.

`context_dir` / `contextDir` is optional and works like the build context in `docker build <context>`. Pass it when the `Image` reads host files (`copy()`, `add()`, or `RUN --mount=type=bind`) so those sources resolve relative to it; omit it otherwise.

> **Building on a `tensorlake/*` base does not carry over its runtime behavior.** The `tl-user` default user and working directory apply only when you run a Tensorlake image directly. Your built image runs with whatever `USER` and `WORKDIR` its Dockerfile sets, or Docker defaults otherwise.

### Build / Register the Image

Build defaults are `cpus=2.0`, `memory=4096 MB`, and a generated root disk of `10240 MiB` (10 GiB). Resources are passed to the **build call**, not the `Image(...)` constructor.

**Python / TypeScript / CLI:**

```python
image.build(
    registered_name="data-tools-image",
    cpus=4.0,
    memory_mb=4096,
    disk_mb=25600,          # root disk of sandboxes created from this image
    builder_disk_mb=32768,  # temporary builder sandbox only
)
```

```typescript
await image.build({
  registeredName: "data-tools-image",
  cpus: 4.0,
  memoryMb: 4096,
  diskMb: 25600,
  builderDiskMb: 32768,
  contextDir: ".",
});
```

```bash
tl sbx image create ./Dockerfile --registered-name data-tools-image
tl sbx image create ./Dockerfile \
  --registered-name data-tools-image \
  --cpus 4 --memory 4096 --disk_mb 25600 --builder_disk_mb 32768
```

The CLI positional argument is a Dockerfile path; Dockerfile builds use the Dockerfile's parent directory as the build context. `-n/--registered-name` sets the name — if omitted it defaults to the parent directory when the file is named `Dockerfile`, otherwise the file stem. Names must be unique within a project.

> **Disk size carries over to launched sandboxes; CPU and memory do not.** Use a larger build-time `disk_mb` to bake big dependencies in without forcing consumers to override `disk_mb` at create time. CPU and memory fall back to `Sandbox.create()`'s own `cpus` / `memory_mb` (defaults `1.0` / `1024`) unless set at launch.

**Docker compatibility mode.** `--docker_compat` / `docker_compat=True` / `dockerCompat: true` runs the build or import with standard Docker/BuildKit instead of Tensorlake's default builder. Turn it on only if a build or import fails or produces an unexpected result under the default builder — it trades speed and disk for maximum compatibility, so budget at least 3× the builder disk and memory. Works on both builds and imports.

```bash
tl sbx image create ./Dockerfile --registered-name data-tools-image --docker_compat
```

**Private registries.** If you can `docker pull` it, you can use it. Authenticate with `docker login`, then build; the CLI and SDKs read credentials from `~/.docker/config.json` (or `$DOCKER_CONFIG/config.json`). Works with Docker Hub, GHCR, ECR, GCR, Quay, and self-hosted, and in CI (e.g. `amazon-ecr-login` in GitHub Actions). A missing or expired credential fails the build at pull time.

**Register an existing snapshot as an image** — name a completed filesystem snapshot without rebuilding:

```bash
tl sbx image register data-tools-image snap_01HX... --dockerfile ./Dockerfile
```

First positional is the image name, second is the completed snapshot ID; `--dockerfile` is stored so `tl sbx image describe` can show how it was built. The snapshot must be in `Completed` status with a durable `snapshot_uri`. Add `--public` to make it namespace-resolvable.

### Import an Image from a Registry

To use an existing registry image **as-is** — no Dockerfile, no build steps, no build context — import it. The reference is always pulled fresh, and sandboxes run it with whatever user, working directory, and environment it defines. To layer packages on top, write a Dockerfile with it as `FROM` instead.

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

Omitting the registered name defaults it to the reference's last path segment with any tag or digest stripped (`pytorch/pytorch:2.4.1` → `pytorch`, `ghcr.io/org/app@sha256:...` → `app`). Imports honor the same `docker login` credentials, CPU/memory/disk options, and `--public` / `is_public` visibility as builds.

> You can't launch a sandbox directly from a raw Docker/registry reference — it must be registered as a Tensorlake image first, and `tl sbx image import` is the one-step way to do that for an unmodified image. (Docs note that direct launching of public registry images is being worked on.)

### Inspect and List Registered Images

```bash
tl sbx image ls                        # every image registered in the current project
tl sbx image describe data-tools-image # Dockerfile, snapshot ID, image size
```

`describe` accepts either the registered image name or the underlying sandbox-template ID.

```python
from tensorlake import find_sandbox_image_by_name, list_sandbox_images

images = list_sandbox_images()
image = find_sandbox_image_by_name("data-tools-image")   # None if no such image
if image is not None:
    print(image["id"], image["snapshot_id"])
```

```typescript
import { findSandboxImageByName, listSandboxImages } from "tensorlake";

const images = await listSandboxImages();
const image = await findSandboxImageByName("data-tools-image");  // null if none
if (image) {
  console.log(image.id, image.snapshotId);
}
```

The SDK list and lookup calls require organization and project context: `TENSORLAKE_ORGANIZATION_ID` and `TENSORLAKE_PROJECT_ID`.

### Public Images

A registered image is namespace-scoped by default. `--public` (CLI), `is_public=True` (Python), or `isPublic: true` (TypeScript) makes the name resolvable from any namespace — this is how the `tensorlake/*` images work. Public names must be globally unique for the registry; collisions are rejected at creation time.

### Supported Build Operations

Builds support most standard Dockerfile commands, with these limitations:

- `$VAR` / environment-variable substitution does **not** work in `FROM` lines.
- `ONBUILD` instructions are ignored and do not run during child image builds.
- These build fine but have **no effect when running sandboxes** from the image: `ONBUILD`, `SHELL`, `EXPOSE`, `HEALTHCHECK`, `LABEL`, `STOPSIGNAL`, `VOLUME`.

`RUN`, `WORKDIR`, `ENV`, `COPY`, and `ADD` are materialized into the snapshot. Process-level `user=` at `start_process` is the supported way to run as a different user — see [Managed Processes](#managed-processes).

**Skills image** — preload the Tensorlake skills repo so coding agents auto-discover it at startup:

```dockerfile
FROM tensorlake/ubuntu-systemd

RUN apt-get update && apt-get install -y git nodejs npm python3 python3-pip
RUN npm install -g skills
RUN skills add tensorlakeai/tensorlake-skills --all -y --copy
RUN python3 -m pip install --break-system-packages tensorlake
```

### Running Docker Inside a Sandbox

Docker requires systemd, so launch with `tensorlake/ubuntu-systemd` and install Docker from the official Ubuntu repository inside the sandbox:

```bash
tl sbx create my-docker-sandbox --image tensorlake/ubuntu-systemd --cpus 2.0 --memory 2048
tl sbx exec my-docker-sandbox bash -c '
set -e
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
'
tl sbx exec my-docker-sandbox docker run hello-world
```

Over SSH, use `sudo docker run hello-world`.

## Networking

Two independent features: routing internet traffic **into** sandbox services, and restricting the sandbox's **own outbound** access.

### Public URLs

- Management API: `https://<sandbox-id-or-name>.sandbox.tensorlake.ai` → port `9501`, **always authenticated**
- User services: `https://<port>-<sandbox-id-or-name>.sandbox.tensorlake.ai` → a service listening on `<port>` inside the sandbox

The proxy preserves path and query string, supports WebSocket upgrades, and forwards gRPC over HTTP/2. The hostname accepts either the sandbox ID or a sandbox name (names are resolved to the canonical ID before forwarding). `SandboxInfo.sandbox_url` is the management URL, derived from `ingress_endpoint`.

### Port Exposure

Port `9501` is the built-in management API and is always routable through the bare hostname. **Any other port is only forwarded if it is listed in `exposed_ports`.** `allow_unauthenticated_access` does not expose a port by itself.

Via the `Sandbox` handle:

```python
sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
sandbox.update(exposed_ports=[])   # remove all exposed ports
```

```typescript
await sandbox.update({ exposedPorts: [8080], allowUnauthenticatedAccess: false });
await sandbox.update({ exposedPorts: [] });
```

Via `SandboxClient`, when you have an ID or name rather than a handle:

```python
sandbox = client.expose_ports("my-env", [8080], allow_unauthenticated_access=False)
print(sandbox.exposed_ports)
sandbox = client.unexpose_ports("my-env", [8080])
```

```typescript
const sandbox = await client.exposePorts("my-env", [8080], { allowUnauthenticatedAccess: false });
const updated = await client.unexposePorts("my-env", [8080]);
```

HTTP: `PATCH https://api.tensorlake.ai/sandboxes/<sandbox-id-or-name>` with `{"exposed_ports": [8080], "allow_unauthenticated_access": false}`.

CLI:

```bash
tl sbx port expose <sandbox-id-or-name> 8080
tl sbx port ls <sandbox-id-or-name>
tl sbx port rm <sandbox-id-or-name> 8080
```

The CLI `port expose` workflow sets **both** `exposed_ports` **and** `allow_unauthenticated_access=true`, making the user port publicly reachable without TensorLake auth. Use `expose_ports(..., allow_unauthenticated_access=False)` for authenticated-only exposure. Unauthenticated access never applies to port `9501`. If a named sandbox is suspended, the proxy can auto-resume it when a request arrives for an exposed port.

### Authenticated Requests

Authenticated routing is the default model. The proxy accepts:

- API key: `Authorization: Bearer <api-key>`
- Personal access token: `Authorization: Bearer tl_pat...` plus `X-Forwarded-Organization-Id` and `X-Forwarded-Project-Id`
- Session cookie: `tl.session_token` (or legacy `tl-session`) plus the same forwarded organization/project headers

For browser WebSocket clients that cannot set custom `X-Forwarded-*` headers, the proxy also accepts `organizationId` and `projectId` in the query string.

```bash
curl https://8080-<sandbox-id-or-name>.sandbox.tensorlake.ai/health \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"

grpcurl -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  50051-<sandbox-id-or-name>.sandbox.tensorlake.ai:443 list

wscat -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  -c "wss://3000-<sandbox-id-or-name>.sandbox.tensorlake.ai/socket"
```

### Outbound Internet Control

| Parameter | TypeScript | Type | Default | Description |
|---|---|---|---|---|
| `allow_internet_access` | `allowInternetAccess` | `bool` | `true` | Allows internet access, including DNS. If `false`, all outbound traffic except destinations in `allow_out` is blocked, **including DNS**. If `allow_out` is non-empty and this is `true`, **only** the listed destinations and DNS are allowed. |
| `allow_out` | `allowOut` | `list[str]` | `[]` | Allowed **domains, IPv4 addresses, or IPv4 CIDRs**. A non-empty list allows the listed destinations and DNS when `allow_internet_access` is `true`. |
| `deny_out` | `denyOut` | `list[str]` | `[]` | Denied domains, IPv4 addresses, or IPv4 CIDRs. |
| `exposed_ports` | `exposedPorts` | `list[int] \| null` | `null` | User ports the proxy may route to. |
| `allow_unauthenticated_access` | `allowUnauthenticatedAccess` | `bool` | `false` | Skip TensorLake auth for exposed user ports. Never applies to `9501`. |

```python
# Disable outbound internet entirely (good for untrusted code)
sandbox = Sandbox.create(allow_internet_access=False)

# Allowlist specific destinations — note this narrows egress even with internet access on
sandbox = Sandbox.create(
    allow_internet_access=True,
    allow_out=["example.com", "203.0.113.10", "10.0.0.0/8"],
)

# Internet on, but block specific destinations
sandbox = Sandbox.create(deny_out=["example.com"])
```

`allow_out` rules are evaluated before `deny_out`. Over HTTP these are nested under a `network` object: `{"network": {"allow_internet_access": false}}`. Not supported in the CLI.

### Local Tunnels

Tunnels forward a local TCP port to a port inside a running sandbox over an authenticated WebSocket through the sandbox proxy. Your credentials authenticate every connection, so the remote port stays private to your account — **no entry in `exposed_ports` required**. Tunnels and exposed ports are independent.

**When to use a tunnel.** The proxy at `*.sandbox.tensorlake.ai` only speaks HTTP, WebSocket, gRPC, and SSH. Anything else — VNC's RFB protocol, Postgres wire protocol, MySQL, Redis RESP, MongoDB, custom binary protocols — needs a tunnel because the proxy cannot frame those bytes. You can also use one for HTTP/WS/gRPC when you'd rather keep the port reachable only at `127.0.0.1` (e.g. driving Chrome's DevTools Protocol from your laptop).

**CLI** (simplest; works for any language):

```bash
tl sbx tunnel <sandbox-id-or-name> 5901 --listen-port 15901
tl sbx tunnel <sandbox-id-or-name> 9222     # local port defaults to the remote port
```

The command keeps running and prints connection events; `Ctrl+C` stops the tunnel and the sandbox keeps running. The local listener is per-process — to share one tunnel across two clients, run the CLI once and connect both to the same `localhost:<port>`.

**TypeScript/JavaScript SDK:**

```typescript
const sandbox = await Sandbox.connect({ sandboxId: "<sandbox-id>" });
const tunnel = await sandbox.createTunnel(5901, { localPort: 15901 });
const { host, port } = tunnel.address();
console.log(`tunnel listening on ${host}:${port}`);
await tunnel.close();
```

`createTunnel(remotePort, options)` returns a `TcpTunnel`. Options: `localHost` (default `127.0.0.1`), `localPort` (pass `0` for an ephemeral port and read it back from `tunnel.address()`), `connectTimeout` (seconds per WebSocket connection, default `10`).

**Python has no native tunnel helper** — drive the CLI from a subprocess:

```python
import subprocess

tunnel = subprocess.Popen(["tl", "sbx", "tunnel", "<sandbox-id>", "9222", "-l", "9222"])
try:
    ...  # use http://127.0.0.1:9222
finally:
    tunnel.terminate()
    tunnel.wait()
```

**Common patterns:**

| Inside sandbox | Local port | Client |
|---|---|---|
| `5901` (TigerVNC) | `15901` | macOS Screen Sharing, RealVNC, TigerVNC, Remmina |
| `9222` (Chrome DevTools Protocol) | `9222` | Playwright `connect_over_cdp`, Puppeteer, `chrome-remote-interface` |
| `5432` (Postgres) | `5432` | `psql`, DBeaver, TablePlus |
| `3000` (dev server) | `3000` | Browser at `http://localhost:3000` |

**Troubleshooting:**

- **`Connection refused` locally** — the remote service isn't listening yet. Check `tl sbx exec <id> -- bash -lc 'ss -ltnp'` and retry.
- **`502 Bad Gateway` during handshake** — the workload hasn't finished booting; the proxy returns 502 when nothing is listening on the remote port.
- **WebSocket auth failures** — confirm `tl whoami` shows the right organization and project, or that `TENSORLAKE_API_KEY` is set in the shell running the CLI.

## Data Models

Field names are Python `snake_case`; TypeScript uses the `camelCase` equivalent.

### SandboxInfo

Returned by `Sandbox.create()`, `sandbox.info()`, `Sandbox.list()`, and the suspend/resume/expose calls.

| Field | Type | Description |
|---|---|---|
| `sandbox_id` | `str` | Server-assigned UUID |
| `name` | `str \| None` | Name, or `None` for ephemeral |
| `namespace` | `str` | Namespace owning the sandbox |
| `status` | `SandboxStatus` | `pending` \| `running` \| `snapshotting` \| `suspending` \| `suspended` \| `terminated` |
| `image` | `str \| None` | Sandbox image in use |
| `resources` | `ContainerResourcesInfo` | `.cpus: float`, `.memory_mb: int` |
| `timeout_secs` | `int \| None` | Auto-suspend / auto-terminate timeout |
| `exposed_ports` | `list[int] \| None` | Public-routed user ports |
| `allow_unauthenticated_access` | `bool` | Whether exposed ports skip TensorLake auth |
| `ingress_endpoint` | `str \| None` | Base ingress origin for the sandbox's current placement |
| `sandbox_url` | `str \| None` | Management URL (port `9501`) derived from `ingress_endpoint` |
| `entrypoint` | `list[str] \| None` | Custom entrypoint command |
| `network` | `NetworkConfig \| None` | `allow_internet_access`, `allow_out`, `deny_out` |
| `created_at` | `datetime \| None` | Creation timestamp |
| `terminated_at` | `datetime \| None` | Termination timestamp |

### Sandbox

The handle returned by `Sandbox.create()` / `Sandbox.connect()`. Both properties resolve from the server on first access and are cached for the object's lifetime.

| Python | TypeScript | Type | Description |
|---|---|---|---|
| `sandbox_id` | `sandboxId` | `str` | Server-assigned UUID — always a UUID, never a name |
| `name` | `name` | `str \| None` | Human-readable name, or `None` for ephemeral |

In Python `status` is a property returning a `SandboxStatus`; in TypeScript `status()` is an async method.

### CommandResult

Returned by `run()`. `stdout: str`, `stderr: str`, `exit_code: int` / `exitCode: number`.

### ProcessInfo

Returned by `start_process()`, `get_process()`, and `list_processes()`.

| Field | Type | Description |
|---|---|---|
| `pid` | `int` | Process ID inside the sandbox |
| `command` | `str` | Executed command |
| `args` | `list[str]` | Command arguments |
| `status` | `ProcessStatus` | `running` \| `exited` \| `signaled` |
| `exit_code` | `int \| None` | Exit code once exited |
| `signal` | `int \| None` | Signal number if terminated by a signal |
| `stdin_writable` | `bool` | Whether stdin is in pipe mode |
| `started_at` | `datetime` | Start time |
| `ended_at` | `datetime \| None` | End time |
| `managed` | object | Present for supervised processes: `id`, `name`, `status`, `restart_count`, `restart`, `health_status`, `consecutive_health_failures` |

### SnapshotInfo

`snapshot_id`, `sandbox_id`, `snapshot_type` (`"memory"` \| `"filesystem"`), `status` (`in_progress` \| `completed` \| `failed`), `size_bytes`, `base_image`, `created_at`. See [sandbox_persistence.md](sandbox_persistence.md).

### Process Status / Mode Enums

Imported from `tensorlake.sandbox` (Python) / `tensorlake` (TypeScript):

- **`ProcessStatus`** — `running`, `exited`, `signaled`
- **`StdinMode`** — `closed` (default), `pipe`
- **`OutputMode`** — `capture`, `discard`
- **`RestartPolicy`** — `never`, `on_failure`, `always`
- **`ProcessHealthCheckType`** — `http`, `tcp`
- **`CheckpointType`** — `filesystem`, `memory`
- **`SandboxStatus`** — see [SandboxInfo](#sandboxinfo)

## CLI Quick Reference

```bash
tl login                                 # user-level auth
tl init                                  # select the target project
tl whoami                                # show current org/project

tl sbx create                            # create ephemeral sandbox
tl sbx create my-env                     # create named sandbox
tl sbx create --image data-tools-image --cpus 2 --memory 2048 --disk_mb 25600 --timeout 600
tl sbx create --snapshot <snapshot-id>   # restore from a snapshot
tl sbx ls                                # list active sandboxes
tl sbx ls --running                      # running only
tl sbx ls --all                          # every state
tl sbx ls -r                             # running sandboxes in active project (SSH troubleshooting)
tl sbx describe <id>                     # details incl. a pasteable SSH Config block
tl sbx exec <id> <command>               # execute a command (streams combined output)
tl sbx exec <id> --timeout 10 --workdir /home/tl-user --env K=V <command>
tl sbx exec <id> --user root -- <command>
tl sbx exec <id> --detach --name N --restart always --health-http 8080 <cmd>   # managed process
tl sbx run <command>                     # create, run, tear down
tl sbx run --keep <command>              # one-shot run, keep the sandbox
tl sbx ps <id> <pid> --json              # inspect a managed process
tl sbx restart <id> <pid>                # restart via supervisor
tl sbx kill <id> <pid>                   # stop + remove from supervision
tl sbx logs <id> --tail 100 [--level error] [--body "text"] [--process-id P] [--json]
tl sbx logs streams <id>                 # list retained log streams / process IDs
tl sbx ssh <id>                          # interactive PTY (also --shell, --shell-arg, --workdir, --env)
tl sbx ssh keys add --name laptop ~/.ssh/id_ed25519.pub
tl sbx ssh keys ls
tl sbx cp file.txt <id>:/path            # upload (file-only, no dirs)
tl sbx cp <id>:/path ./local             # download
tl sbx tunnel <id> <remote-port> [--listen-port <local>]
tl sbx checkpoint <id> [--checkpoint-type filesystem|memory] [--timeout 600]
tl sbx checkpoint ls                     # list snapshots
tl sbx checkpoint rm <snapshot-id>       # delete a snapshot
tl sbx copy <id> [-n 4] [--timeout 600]  # clone into new warm-started sandbox(es)
tl sbx suspend <id>                      # suspend named sandbox
tl sbx resume <id>                       # resume named sandbox
tl sbx terminate <id>                    # terminate (by name or ID)
tl sbx name <id> <new-name>              # rename or promote ephemeral → named
tl sbx port expose <id> 8080             # expose (also sets allow_unauthenticated_access=true)
tl sbx port ls <id>
tl sbx port rm <id> 8080
tl sbx image create ./Dockerfile --registered-name NAME [--docker_compat]
tl sbx image import REF --registered-name NAME          # register a registry image as-is
tl sbx image register NAME <snapshot-id> --dockerfile ./Dockerfile
tl sbx image ls
tl sbx image describe NAME
```

CLI verbs accept a sandbox **name** anywhere an ID is accepted, for named sandboxes.
