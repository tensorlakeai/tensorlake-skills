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

`sandbox_id`, `name`, `namespace`, `status`, `image`, `resources` (`.cpus`, `.memory_mb`), `secret_names`, `timeout_secs`, `entrypoint`, `created_at`, `terminated_at`

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

# Or connect to existing sandbox
sandbox = client.connect(sandbox_id)
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

Note: Cloning and suspending named sandboxes are CLI-only operations, not available in the Python SDK.

### Sandbox Pools

```python
pool = client.create_pool(
    image: str | None = None,
    cpus: float = 1.0,
    memory_mb: int = 2048,
    secret_names: list[str] | None = None,
    timeout_secs: int = 0,
    entrypoint: list[str] | None = None,
    max_containers: int | None = None,
    warm_containers: int | None = None,
)
pool_id = pool.pool_id

info = client.get_pool(pool_id)        # -> SandboxPoolInfo
pools = client.list_pools()            # -> list[SandboxPoolInfo]
info = client.update_pool(pool_id, ...)
client.delete_pool(pool_id)

# Claim a sandbox from the pool
response = client.claim(pool_id)
```

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

### Interactive PTY Session

```python
session = sandbox.create_pty_session(
    command="/bin/bash",
    rows=24,
    cols=80,
)
ws_url = sandbox.pty_ws_url(session["session_id"], session["token"])
```

### Cleanup

```python
sandbox.close()       # Close connection, sandbox keeps running
# client.delete(sandbox_id) to terminate
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
tl sbx image create img.py --name NAME  # Build image
tl sbx port expose <id> 8080            # Expose port
```
