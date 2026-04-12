<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/introduction.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
  - https://docs.tensorlake.ai/sandboxes/file-operations.md
  - https://docs.tensorlake.ai/sandboxes/processes.md
  - https://docs.tensorlake.ai/sandboxes/networking.md
  - https://docs.tensorlake.ai/sandboxes/images.md
  - https://docs.tensorlake.ai/sandboxes/pty-sessions.md
  - https://docs.tensorlake.ai/sandboxes/computer-use.md
SDK version: tensorlake 0.4.44
Last verified: 2026-04-12
-->

# TensorLake Sandbox SDK Reference

For state management (snapshots, suspend/resume, clone, ephemeral vs named, state machine), see [sandbox_persistence.md](sandbox_persistence.md).

## Imports

**Python:**

```python
from tensorlake.sandbox import SandboxClient
```

**TypeScript:**

```typescript
import { SandboxClient } from "tensorlake";
```

Install: `npm install tensorlake` (also installs `tl` and `tensorlake` CLI tools)

## SandboxClient — Lifecycle Management

**Python:**

```python
client = SandboxClient()
```

**TypeScript:**

```typescript
const client = SandboxClient.forCloud({
  apiKey: process.env.TENSORLAKE_API_KEY,
});
```

### Create Sandboxes

**Python:**

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

**TypeScript:**

```typescript
// Ephemeral sandbox
const sandbox = await client.create({
  cpus: 1.0,
  memoryMb: 1024,
  timeoutSecs: 300,
});

// Named sandbox
const named = await client.create({
  name: "my-agent-env",
  cpus: 2.0,
  memoryMb: 2048,
});

console.log(named.sandboxId);  // server-assigned UUID
console.log(named.name);       // "my-agent-env"
```

### Connect to Existing Sandbox

**Python:**

```python
# `identifier` accepts sandbox_id (UUID) or name
sandbox = client.connect(identifier="my-env")
print(sandbox.sandbox_id)  # server UUID, e.g. "s7jus08qec4axzgbpq76h"
print(sandbox.name)        # "my-env"
```

**TypeScript:**

```typescript
// Accepts sandbox ID or name
const sandbox = client.connect("my-env");
console.log(sandbox.sandboxId);  // server UUID
console.log(sandbox.name);       // "my-env"
```

### Query, Update & Delete

**Python:**

```python
info = client.get("my-env")            # -> SandboxInfo (accepts name or sandbox_id)
sandboxes = client.list()              # -> list[SandboxInfo]
client.update_sandbox("my-env", "new-name")  # Rename sandbox
client.delete("new-name")             # Terminates the sandbox (accepts name or sandbox_id)
```

**TypeScript:**

```typescript
const info = await client.get("my-env");     // accepts name or sandboxId
const sandboxes = await client.list();
await client.update("my-env", { name: "new-name" });
await client.delete("new-name");
```

### Sandbox Properties

**Python:** `sandbox.sandbox_id` (str), `sandbox.name` (str | None), `sandbox.status` (str)

**TypeScript:** `sandbox.sandboxId` (string), `sandbox.name` (string | null)

### SandboxInfo Attributes

`sandbox_id`/`sandboxId`, `name`, `namespace`, `status`, `image`, `resources` (`ContainerResourcesInfo`: `.cpus`, `.memory_mb`/`.memoryMb`), `secret_names`, `timeout_secs`, `entrypoint`, `created_at`, `terminated_at`

### Create & Connect to a Sandbox

**Python:**

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

# Manual lifecycle (call close() or terminate() when done)
sandbox = client.create_and_connect(cpus=1.0)
# ... use sandbox ...
sandbox.close()       # Terminates sandbox and closes connection
# or: sandbox.terminate()  # Equivalent — stops the sandbox
```

**TypeScript:**

```typescript
const sandbox = await client.createAndConnect({
  name: "my-env",          // optional
  cpus: 1.0,
  memoryMb: 1024,
  timeoutSecs: 600,
  allowInternetAccess: false,
  snapshotId: "snap-xxx",  // optional — restore from snapshot
});

try {
  const result = await sandbox.run("echo", { args: ["hello"] });
  console.log(result.stdout);
} finally {
  await sandbox.terminate();
  client.close();
}
```

### Persistence

Snapshots, suspend/resume, clone, ephemeral vs named, and the full state machine live in [sandbox_persistence.md](sandbox_persistence.md).

## Sandbox — Interact with Running Sandbox

### Execute Commands

**Python:**

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

Shell commands (pipes, redirects, chaining) require wrapping in bash:

**Python:**

```python
sandbox.run("bash", ["-c", "ls -la /workspace | grep '.py'"])
sandbox.run("bash", ["-c", "cd /workspace && pip install -r requirements.txt && python main.py"])
```

**TypeScript:**

```typescript
await sandbox.run("bash", {
  args: ["-lc", "ls -la /workspace | grep '.py' | wc -l"],
});
await sandbox.run("bash", {
  args: ["-lc", "cd /workspace && pip install -r requirements.txt && python main.py"],
});
```

### File Operations

**Python:**

```python
sandbox.write_file(path: str, content: bytes)
data = sandbox.read_file(path: str)          # -> bytes (use bytes(data).decode() for text)
sandbox.delete_file(path: str)
entries = sandbox.list_directory(path: str)   # -> ListDirectoryResponse
# entries.entries[].name, entries.entries[].size
```

**TypeScript:**

```typescript
await sandbox.writeFile(
  "/workspace/data.csv",
  new TextEncoder().encode("name,score\nAlice,95\nBob,87"),
);

const content = await sandbox.readFile("/workspace/data.csv");
console.log(new TextDecoder().decode(content));

await sandbox.deleteFile("/workspace/data.csv");
```

Best practice: Use `/workspace` as the default working directory.

### Process Management

**Python:**

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
# proc.pid, proc.status (SandboxProcessStatus), proc.stdin_writable
# proc.command, proc.args, proc.started_at, proc.ended_at
# proc.exit_code, proc.signal

sandbox.list_processes()                     # -> list[ProcessInfo]

# Stream output as it arrives (SSE)
for event in sandbox.follow_output(proc.pid):
    print(event.line, end="")

# Signal handling
import signal
sandbox.send_signal(proc.pid, signal.SIGTERM)  # Graceful stop
sandbox.send_signal(proc.pid, signal.SIGKILL)  # Force kill
```

**TypeScript:**

```typescript
import { ProcessStatus } from "tensorlake";

const proc = await sandbox.startProcess("python", {
  args: ["-c", "import time\nfor i in range(5):\n print(f'Step {i+1}/5')\n time.sleep(1)"],
});

// Poll for completion
let info = await sandbox.getProcess(proc.pid);
while (info.status === ProcessStatus.RUNNING) {
  await new Promise((resolve) => setTimeout(resolve, 100));
  info = await sandbox.getProcess(proc.pid);
}

// Get captured output
console.log((await sandbox.getStdout(proc.pid)).lines);
console.log((await sandbox.getStderr(proc.pid)).lines);
console.log((await sandbox.getOutput(proc.pid)).lines);  // combined

// Stream output as it arrives (SSE)
for await (const event of sandbox.followOutput(proc.pid)) {
  process.stdout.write(event.line);
}

// Signal / kill
await sandbox.sendSignal(proc.pid, 15);   // SIGTERM — graceful stop
await sandbox.killProcess(proc.pid);       // Dedicated kill convenience (no Python equivalent)
```

### Process Stdin/Stdout/Stderr (Granular APIs)

For fine-grained I/O control, use `stdin_mode="pipe"` (Python) or `stdinMode: "pipe"` (TypeScript) when starting a process:

**Python:**

```python
proc = sandbox.start_process("python", ["-i"], stdin_mode="pipe")
sandbox.write_stdin(proc.pid, b"print('hello')\n")
sandbox.close_stdin(proc.pid)  # delivers EOF without terminating the process
```

**TypeScript:**

```typescript
const proc = await sandbox.startProcess("python", {
  args: ["-i"],
  stdinMode: "pipe",
});
await sandbox.writeStdin(proc.pid, new TextEncoder().encode("print('hello')\n"));
await sandbox.closeStdin(proc.pid);
```

**REST equivalents:**
- Stream output: `GET /api/v1/processes/<pid>/output/follow` (SSE — emits `output` and `eof` events)
- Write stdin: `POST /api/v1/processes/<pid>/stdin` (body: raw bytes)
- Close stdin: `POST /api/v1/processes/<pid>/stdin/close`
- Send signal: `POST /api/v1/processes/<pid>/signal` (body: `{"signal": 15}`)
- Kill process: `DELETE /api/v1/processes/<pid>`

### Interactive PTY Session

**Python:**

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
print(pty.wait())

# Reconnect to an existing PTY session
pty = sandbox.connect_pty(session_id, token)
```

**TypeScript:**

```typescript
const pty = await sandbox.createPty({
  command: "/bin/bash",
  rows: 24,
  cols: 80,
});

await pty.sendInput("pwd\nexit\n");
console.log(await pty.wait());
```

## Computer Use (Desktop Automation)

Use the `ubuntu-vnc` image to get a desktop-enabled sandbox with XFCE, TigerVNC, and Firefox. Desktop connections are proxied through an authenticated endpoint — no port exposure needed.

**Python:**

```python
from tensorlake.sandbox import SandboxClient
from pathlib import Path
import time

client = SandboxClient()

# Screenshot
with client.create_and_connect(image="ubuntu-vnc") as sandbox:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        Path("sandbox-desktop.png").write_bytes(desktop.screenshot())

# Send keyboard input and verify
with client.create_and_connect(image="ubuntu-vnc") as sandbox:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        desktop.press(["ctrl", "alt", "t"])
        time.sleep(1.0)
        desktop.type_text("echo docs-test > /tmp/desktop-test.txt")
        desktop.press("enter")
    result = sandbox.run("bash", ["-lc", "cat /tmp/desktop-test.txt"])
    print(result.stdout.strip())
```

### Reconnecting to an Existing Desktop Sandbox

```python
sandbox_id = "your-running-sandbox-id"
with client.connect(sandbox_id) as sandbox:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        Path("existing-sandbox.png").write_bytes(desktop.screenshot())
```

### Desktop Methods

| Method | Description |
|---|---|
| `screenshot()` | Returns PNG bytes of current desktop |
| `press(key)` | Press key or key combo (e.g., `["ctrl", "alt", "t"]`) |
| `type_text(text)` | Type text input |
| `move_mouse()` | Move cursor |
| `click()` | Single mouse click |
| `double_click()` | Double mouse click |
| `scroll()` | Scroll |
| `key_down()` | Key press (held) |
| `key_up()` | Key release |

### Notes

- Default VNC password for managed `ubuntu-vnc` image: `"tensorlake"`
- Desktop connection is proxied through an authenticated endpoint (no port exposure needed)
- `client.connect()` does not terminate sandbox on exit (unlike `create_and_connect` context manager)
- Context manager pattern (`with`) auto-closes desktop connections

## Sandbox Images

Build custom images using the Image builder:

**Python:**

```python
from tensorlake.applications import Image

SANDBOX_IMAGE = (
    Image(name="data-tools", base_image="ubuntu-minimal")
    .run("pip install pandas pyarrow jupyter")
    .run("mkdir -p /workspace/cache")
    .env("APP_ENV", "prod")
)
```

**TypeScript:**

```typescript
import { Image, createSandboxImage } from "tensorlake";

const image = new Image({
  name: "data-tools",
  baseImage: "ubuntu-minimal",
})
  .run("pip install pandas pyarrow jupyter")
  .run("mkdir -p /workspace/cache")
  .env("APP_ENV", "prod")
  .workdir("/workspace");

// Register image
await createSandboxImage(image, {
  contextDir: ".",
  cpus: 4,
  memoryMb: 4096,
});
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
- `.workdir(path)` — Set working directory (TypeScript only)

### Launching Sandboxes from Custom Images

**Python:**

```python
with client.create_and_connect(
    image="data-tools",
    cpus=4.0,
    memory_mb=4096,
    timeout_secs=1800,
) as sandbox:
    result = sandbox.run("python3", ["-c", "import pandas; print('ready')"])
```

**TypeScript:**

```typescript
const sandbox = await client.createAndConnect({
  image: "data-tools",
  cpus: 4.0,
  memoryMb: 4096,
  timeoutSecs: 1800,
});
```

### CLI

```bash
tl sbx image create image.py --name data-tools-image
tl sbx new --image data-tools-image
```

## Networking

| Python Parameter | TypeScript Parameter | Type | Default | Description |
|---|---|---|---|---|
| `allow_internet_access` | `allowInternetAccess` | `bool` | `True` | Global internet toggle |
| `deny_out` | `denyOut` | `list[str]` | `[]` | Blocked outbound destinations (domains/IPs/CIDRs) |
| `allow_out` | `allowOut` | `list[str]` | `[]` | Allowed outbound destinations (when internet disabled) |

### Public URLs

- Management API: `https://<sandbox-id>.sandbox.tensorlake.ai`
- User services: `https://<port>-<sandbox-id>.sandbox.tensorlake.ai`
- Supports HTTP/1.1, HTTP/2, WebSocket upgrades

### Port Exposure

**Python:**

```python
client.expose_ports(sandbox_id, ports=[8080], allow_unauthenticated_access=False)
client.unexpose_ports(sandbox_id, ports=[8080])
```

**TypeScript:**

```typescript
await client.exposePorts("my-env", [8080], { allowUnauthenticatedAccess: false });
await client.unexposePorts("my-env", [8080]);
```

**CLI:**

```bash
tl sbx port expose <sandbox-id> 8080
tl sbx port ls <sandbox-id>
tl sbx port rm <sandbox-id> 8080
```

Idle auto-suspend and auto-resume for named sandboxes are covered in [sandbox_persistence.md](sandbox_persistence.md#idle-auto-suspend-and-auto-resume).

## Enums

### SandboxProcessStatus

| Value | Meaning |
|---|---|
| `running` | Process is executing |
| `exited` | Process exited normally |
| `signaled` | Process terminated by signal |

### SandboxProcessStdinMode

| Value | Meaning |
|---|---|
| `closed` | Stdin is not writable (default) |
| `pipe` | Stdin accepts writes via `write_stdin()` |

### SandboxProcessOutputMode

| Value | Meaning |
|---|---|
| `capture` | Capture output for later retrieval |
| `discard` | Discard output |

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
