<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/introduction.md
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
  - https://docs.tensorlake.ai/sandboxes/file-operations.md
  - https://docs.tensorlake.ai/sandboxes/snapshots.md
  - https://docs.tensorlake.ai/sandboxes/processes.md
  - https://docs.tensorlake.ai/sandboxes/networking.md
  - https://docs.tensorlake.ai/sandboxes/images.md
SDK version: tensorlake 0.4.39
Last verified: 2026-04-07
-->

# TensorLake Sandbox SDK Reference

## Imports

```python
from tensorlake.sandbox import SandboxClient
```

## SandboxClient — Lifecycle Management

```python
client = SandboxClient()
```

### Create Sandboxes

```python
# Ephemeral sandbox — no name, cannot be suspended
sandbox = client.create(
    cpus: float = 1.0,                    # CPU cores
    memory_mb: int = 1024,                # Memory in MiB (1024-8192 per CPU)
    timeout_secs: int = 0,                # 0 = no timeout
    secret_names: list[str] | None = None,
    allow_internet_access: bool = True,
    deny_out: list[str] | None = None,    # Blocked outbound destinations (domains/IPs/CIDRs)
)

# Named sandbox — can be suspended and resumed
sandbox = client.create(name="my-agent-env", cpus=2.0, memory_mb=2048)

sandbox_id = sandbox.sandbox_id
print(sandbox.status)
```

### Query & Delete

```python
info = client.get(sandbox_id)          # -> SandboxInfo
sandboxes = client.list()              # -> list[SandboxInfo]
client.delete(sandbox_id)              # Terminates the sandbox (idempotent)
```

### SandboxInfo Attributes

`sandbox_id`, `name`, `namespace`, `status`, `image`, `resources` (`ContainerResourcesInfo`: `.cpus`, `.memory_mb`), `secret_names`, `timeout_secs`, `entrypoint`, `created_at`, `terminated_at`

### Ephemeral vs Named Sandboxes

- **Ephemeral**: Created without `name`. Auto-terminate on completion. Cannot be suspended.
- **Named/Persistent**: Created with `name` parameter. Support suspend/resume.

### Connect to a Sandbox

```python
# Context manager (auto-terminates on exit)
with client.create_and_connect(
    name: str | None = None,
    cpus: float = 1.0,
    memory_mb: int = 1024,
    timeout_secs: int | None = None,
    secret_names: list[str] | None = None,
    allow_internet_access: bool = True,
    deny_out: list[str] | None = None,
    snapshot_id: str | None = None,
) as sandbox:
    result = sandbox.run("echo", ["hello"])

```

### Snapshots

```python
snapshot = client.snapshot_and_wait(sandbox_id, timeout=300, poll_interval=1.0)
print(snapshot.snapshot_id)
# snapshot.status.value, snapshot.size_bytes

info = client.get_snapshot(snapshot_id)           # -> SnapshotInfo
snapshots = client.list_snapshots()               # -> list[SnapshotInfo]
client.delete_snapshot(snapshot_id)

# Restore from snapshot
new_sandbox = client.create_and_connect(snapshot_id=snapshot.snapshot_id)
```

Snapshots restore filesystem and memory state. Inherited settings (image, resources, entrypoint, secrets) can be overridden on restore.

### Clone (CLI only)

```bash
tl sbx clone <sandbox-id>   # Snapshot + restore in one operation
```

Note: Cloning is a CLI-only operation, not available in the Python SDK.

### Suspend & Resume

Suspend/resume is available for **named sandboxes only**. Ephemeral sandboxes return 400.

**CLI:**

```bash
tl sbx suspend my-env
tl sbx resume my-env
```

**REST API:**

```bash
# Suspend — snapshots the sandbox and terminates its live container
curl -X POST https://api.tensorlake.ai/sandboxes/{sandbox_id_or_name}/suspend \
  -H "Authorization: Bearer $TL_API_KEY"
# 202 = suspend initiated, 200 = already suspended

# Resume — restores from snapshot
curl -X POST https://api.tensorlake.ai/sandboxes/{sandbox_id_or_name}/resume \
  -H "Authorization: Bearer $TL_API_KEY"
# 202 = resume initiated, 200 = already running
```

**Status codes (both endpoints):** 400 = cannot suspend/resume in current state (or ephemeral), 401 = invalid credentials, 403 = insufficient permissions, 404 = not found.

Note: Suspend/resume is not available in the Python SDK — use CLI or REST API. However, many sandbox-proxy requests (e.g., hitting the sandbox URL) automatically resume suspended sandboxes.

## Sandbox — Interact with Running Sandbox

### Execute Commands

```python
result = sandbox.run(
    command: str,                        # e.g., "python", "bash"
    args: list[str] | None = None,       # e.g., ["-c", "print('hello')"]
    env: dict[str, str] | None = None,
    working_dir: str | None = None,
    timeout: float | None = None,
)
result.exit_code   # int
result.stdout      # str
result.stderr      # str
```

Shell commands (pipes, redirects, chaining) require wrapping in bash:

```python
sandbox.run("bash", ["-c", "ls -la /workspace | grep '.py'"])
sandbox.run("bash", ["-c", "cd /workspace && pip install -r requirements.txt && python main.py"])
```

### File Operations

```python
sandbox.write_file(path: str, content: bytes)
data = sandbox.read_file(path: str)          # -> bytes (use bytes(data).decode() for text)
sandbox.delete_file(path: str)
entries = sandbox.list_directory(path: str)   # -> ListDirectoryResponse
# entries.entries[].name, entries.entries[].size
```

Best practice: Use `/workspace` as the default working directory.

### Process Management

```python
# Start a long-running process
proc = sandbox.start_process(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    working_dir: str | None = None,
    stdin_mode: str | None = None,           # "pipe" to enable stdin writing
    stdout_mode: str | None = None,          # "capture" to capture stdout
    stderr_mode: str | None = None,          # "capture" to capture stderr
)
# proc.pid, proc.status

sandbox.list_processes()                     # -> list[ProcessInfo]

# Stream output as it arrives (SSE)
for event in sandbox.follow_output(proc.pid):
    print(event.line, end="")

# Signal handling
import signal
sandbox.send_signal(proc.pid, signal.SIGTERM)  # Graceful stop
sandbox.send_signal(proc.pid, signal.SIGKILL)  # Force kill
```

### Process Stdin/Stdout/Stderr (Granular APIs)

For fine-grained I/O control, use `stdin_mode="pipe"` when starting a process:

```python
# Start process with stdin pipe
proc = sandbox.start_process("python", ["-i"], stdin_mode="pipe")

# Write to stdin (SDK wraps the REST endpoint)
# REST: POST /api/v1/processes/<pid>/stdin
# Close stdin when done:
# REST: POST /api/v1/processes/<pid>/stdin/close
```

**Stdout/Stderr streaming (SSE):**

```python
# Stream output line-by-line as Server-Sent Events
for event in sandbox.follow_output(proc.pid):
    # event.line — output content
    # event.timestamp — when the line was emitted
    # event type: "output" (data) or "eof" (stream complete)
    print(event.line, end="")
```

**REST equivalents:**
- Stream output: `GET /api/v1/processes/<pid>/output/follow` (SSE — emits `output` and `eof` events)
- Write stdin: `POST /api/v1/processes/<pid>/stdin` (body: raw bytes)
- Close stdin: `POST /api/v1/processes/<pid>/stdin/close`
- Send signal: `POST /api/v1/processes/<pid>/signal` (body: `{"signal": 15}`)
- Kill process: `DELETE /api/v1/processes/<pid>`

### Interactive PTY Session

```python
session = sandbox.create_pty_session(
    command="/bin/bash",
    rows=24,
    cols=80,
)
ws_url = sandbox.pty_ws_url(session["session_id"], session["token"])
```

## Sandbox Images

Build custom images using the Image builder (imported from applications):

```python
from tensorlake.applications import Image

SANDBOX_IMAGE = (
    Image(name="data-tools", base_image="ubuntu-minimal")
    .run("pip install pandas pyarrow jupyter")
    .run("mkdir -p /workspace/cache")
    .env("APP_ENV", "prod")
)
```

### Base Images

| Base Image | Description |
|---|---|
| `ubuntu-minimal` | Default. No systemd, boots in hundreds of ms. |
| `ubuntu-systemd` | Includes systemd, supports Docker/K8s inside sandbox. |

### Image Builder Methods (chainable)

- `.run(command)` — Execute shell command during build
- `.env(key, value)` — Set environment variable
- `.copy(src, dest)` — Copy file from local filesystem
- `.add(src, dest)` — Add file to image

### CLI

```bash
tl sbx image create image.py --name data-tools-image
tl sbx new --image data-tools-image
```

## Networking

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allow_internet_access` | `bool` | `True` | Global internet toggle |
| `deny_out` | `list[str]` | `[]` | Blocked outbound destinations (domains/IPs/CIDRs) |

### Public URLs

- Management API: `https://<sandbox-id>.sandbox.tensorlake.ai`
- User services: `https://<port>-<sandbox-id>.sandbox.tensorlake.ai`
- Supports HTTP/1.1, HTTP/2, WebSocket upgrades

### Port Exposure (CLI/HTTP only)

```bash
tl sbx port expose <sandbox-id> 8080
tl sbx port ls <sandbox-id>
tl sbx port rm <sandbox-id> 8080
```

### Auto-Resume

Requests to a **suspended** named sandbox automatically resume it and wait for the port to become routable.

## Sandbox Statuses

| Status | Meaning |
|---|---|
| `Pending` | Being created/scheduled |
| `Running` | Ready for commands |
| `Snapshotting` | Snapshot in progress |
| `Suspending` | Being suspended |
| `Suspended` | Paused (named sandboxes only) |
| `Terminated` | Stopped |

## CLI Quick Reference

```bash
tl sbx new                              # Create ephemeral sandbox
tl sbx new my-env                       # Create named sandbox
tl sbx exec <id> <command>              # Execute command
tl sbx run <command>                    # Create, run, teardown
tl sbx ssh <id>                         # Interactive shell
tl sbx cp file.txt <id>:/path           # Upload file (file-only, no dirs)
tl sbx cp <id>:/path ./local            # Download file
tl sbx clone <id>                       # Snapshot + restore
tl sbx snapshot <id>                    # Create snapshot
tl sbx suspend <id>                     # Suspend named sandbox
tl sbx terminate <id>                   # Terminate sandbox (by name or ID)
tl sbx image create img.py --name NAME  # Build image
tl sbx port expose <id> 8080            # Expose port
```
