# TensorLake Sandbox SDK Reference

## Imports

```python
from tensorlake.sandbox import (
    SandboxClient, Sandbox,
    SandboxStatus, SnapshotStatus, ProcessStatus,
    OutputMode, StdinMode,
    CommandResult, SandboxInfo, SandboxPoolInfo, SnapshotInfo, ProcessInfo,
)
```

## SandboxClient — Lifecycle Management

```python
client = SandboxClient(
    api_url: str = "https://api.tensorlake.ai",
    api_key: str | None = None,       # Defaults to TENSORLAKE_API_KEY env var
    organization_id: str | None = None,
    project_id: str | None = None,
    namespace: str | None = None,
)

# Factory methods
client = SandboxClient.for_cloud(api_key=None, organization_id=None, project_id=None)
client = SandboxClient.for_localhost(api_url="http://localhost:8900", namespace="default")
```

### Create & Delete Sandboxes

```python
response = client.create(
    image: str | None = None,
    cpus: float = 1.0,
    memory_mb: int = 2048,
    ephemeral_disk_mb: int = 1024,
    secret_names: list[str] | None = None,
    timeout_secs: int | None = None,
    entrypoint: list[str] | None = None,
    allow_internet_access: bool = True,
    allow_out: list[str] | None = None,
    deny_out: list[str] | None = None,
    snapshot_id: str | None = None,
)
sandbox_id = response.sandbox_id

info = client.get(sandbox_id)          # -> SandboxInfo
sandboxes = client.list()              # -> list[SandboxInfo]
client.delete(sandbox_id)              # Terminates the sandbox
```

### Claim from Pool

```python
response = client.claim(pool_id)       # -> CreateSandboxResponse
```

### Snapshots

```python
snap = client.snapshot(sandbox_id)                    # -> CreateSnapshotResponse (async op)
info = client.get_snapshot(snap.snapshot_id)           # -> SnapshotInfo
info = client.snapshot_and_wait(sandbox_id, timeout=300)  # -> SnapshotInfo (blocks)
snapshots = client.list_snapshots()                    # -> list[SnapshotInfo]
client.delete_snapshot(snapshot_id)
```

### Sandbox Pools

```python
pool = client.create_pool(
    image: str | None = None,
    cpus: float = 1.0,
    memory_mb: int = 2048,
    ephemeral_disk_mb: int = 1024,
    secret_names: list[str] | None = None,
    timeout_secs: int = 0,
    entrypoint: list[str] | None = None,
    max_containers: int | None = None,
    warm_containers: int | None = None,
)
pool_id = pool.pool_id

info = client.get_pool(pool_id)        # -> SandboxPoolInfo
pools = client.list_pools()            # -> list[SandboxPoolInfo]
info = client.update_pool(pool_id, image=..., max_containers=..., ...)
client.delete_pool(pool_id)
```

### Connect to a Sandbox

```python
# Context manager (auto-terminates on exit)
with client.create_and_connect(
    image: str | None = None,
    cpus: float = 1.0,
    memory_mb: int = 2048,
    ephemeral_disk_mb: int = 1024,
    secret_names: list[str] | None = None,
    timeout_secs: int | None = None,
    entrypoint: list[str] | None = None,
    allow_internet_access: bool = True,
    allow_out: list[str] | None = None,
    deny_out: list[str] | None = None,
    pool_id: str | None = None,
    snapshot_id: str | None = None,
    startup_timeout: float = 60,
) as sandbox:
    result = sandbox.run("echo hello")

# Or connect to existing sandbox
sandbox = client.connect(sandbox_id)
```

## Sandbox — Interact with Running Sandbox

### Execute Commands

```python
result = sandbox.run(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    working_dir: str | None = None,
    timeout: float | None = None,
)
result.exit_code   # int
result.stdout      # str
result.stderr      # str
```

### File Operations

```python
sandbox.write_file(path: str, content: bytes)
data = sandbox.read_file(path: str)          # -> bytes
sandbox.delete_file(path: str)
entries = sandbox.list_directory(path: str)   # -> ListDirectoryResponse
```

### Process Management

```python
# Start a long-running process
proc = sandbox.start_process(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    working_dir: str | None = None,
    stdin_mode: StdinMode = StdinMode.CLOSED,
    stdout_mode: OutputMode = OutputMode.CAPTURE,
    stderr_mode: OutputMode = OutputMode.CAPTURE,
)

sandbox.list_processes()                     # -> list[ProcessInfo]
sandbox.get_process(pid)                     # -> ProcessInfo
sandbox.kill_process(pid)
sandbox.send_signal(pid, signal)             # -> SendSignalResponse

# Process I/O
sandbox.write_stdin(pid, data: bytes)
sandbox.close_stdin(pid)
sandbox.get_stdout(pid)                      # -> OutputResponse
sandbox.get_stderr(pid)                      # -> OutputResponse
sandbox.get_output(pid)                      # -> OutputResponse (combined)

# Stream output (SSE)
for event in sandbox.follow_stdout(pid):     # -> Iterator[OutputEvent]
    print(event.line)
```

### Cleanup

```python
sandbox.close()       # Close connection, sandbox keeps running
sandbox.terminate()   # Terminate sandbox and close connection
```

## Sandbox Statuses

| Status | Meaning |
|---|---|
| `PENDING` | Being created |
| `RUNNING` | Ready for commands |
| `SNAPSHOTTING` | Snapshot in progress |
| `SUSPENDED` | Paused (snapshot complete) |
| `TERMINATED` | Stopped |
