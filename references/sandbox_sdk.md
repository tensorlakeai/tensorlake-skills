<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/introduction.md
  - https://docs.tensorlake.ai/sandboxes/quickstart.md
  - https://docs.tensorlake.ai/sandboxes/sdk-reference.md
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
  - https://docs.tensorlake.ai/sandboxes/file-operations.md
  - https://docs.tensorlake.ai/sandboxes/processes.md
  - https://docs.tensorlake.ai/sandboxes/environment-variables.md
  - https://docs.tensorlake.ai/sandboxes/networking.md
  - https://docs.tensorlake.ai/sandboxes/images.md
  - https://docs.tensorlake.ai/sandboxes/pty-sessions.md
  - https://docs.tensorlake.ai/sandboxes/computer-use.md
  - https://docs.tensorlake.ai/sandboxes/docker.md
SDK version: tensorlake 0.5.3
Last verified: 2026-04-28
-->

# TensorLake Sandbox SDK Reference

TensorLake Sandboxes are MicroVMs backed by Firecracker and CloudHypervisor. The `ubuntu-minimal` base image starts up in a few hundred milliseconds; `ubuntu-systemd` takes around 1 second to boot. The platform is HIPAA and SOC 2 Type II compliant, supports EU data residency, and offers zero data retention.

For state management (snapshots, suspend/resume, ephemeral vs named, state machine), see [sandbox_persistence.md](sandbox_persistence.md).

> **0.5.1 note:** `Sandbox` is the preferred handle for create/connect/run/suspend/resume/checkpoint and now also for **rename and port exposure** via the `sandbox.update(name=..., exposed_ports=..., allow_unauthenticated_access=...)` instance method. `SandboxClient` still ships and emits a `DeprecationWarning` on construction; only `client.list()` lacks a direct `Sandbox`-level replacement. `Sandbox.name`, `Sandbox.status`, and `Sandbox.sandbox_id` are properties (no parens). `sandbox.status` returns a `SandboxStatus` enum (`SandboxStatus.RUNNING`, `.SUSPENDED`, etc.) — use `sandbox.status.value` for the lowercase string form. Snapshot creation is `sandbox.checkpoint()`; restore is `Sandbox.create(snapshot_id=...)`.

## Table of Contents

- [Imports](#imports)
- [Sandbox — Static Methods](#sandbox--static-methods)
- [Sandbox — Instance Methods](#sandbox--instance-methods)
- [Computer Use (Desktop Automation)](#computer-use-desktop-automation)
- [Sandbox Images](#sandbox-images)
- [Networking](#networking)
- [Data Models](#data-models)
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

Install: `pip install tensorlake` (Python) or `npm install tensorlake` (TypeScript). Both ship with the `tl` and `tensorlake` CLI tools. Authenticate once with `tl login`, or export `TENSORLAKE_API_KEY` in the environment.

## Sandbox — Static Methods

All sandbox lifecycle operations live as static methods on the `Sandbox` class.

### Create a Sandbox

**Python:**

```python
# Ephemeral sandbox — no name, cannot be suspended
sandbox = Sandbox.create(
    name=None,             # str | None — promote to named by passing a value
    cpus=1.0,              # float, 1.0–8.0
    memory_mb=1024,        # int, 1024–8192 per CPU
    disk_mb=10240,         # int, 10240–102400 (10–100 GiB) — root filesystem size in MiB
    timeout_secs=None,     # int | None — None means no timeout
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

# Port exposure is a post-create operation in 0.5.1 — see "Port Exposure" below.
# Use sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
# or SandboxClient().expose_ports(...).
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

// Port exposure is a post-create operation in 0.5.1 — see "Port Exposure" below.
```

`Sandbox.create()` returns an operable `Sandbox` handle that is already connected — you can call instance methods on it directly without a separate `connect()` step.

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
const sandbox = await Sandbox.connect("my-agent-env");
console.log(sandbox.sandboxId);
console.log(sandbox.name);

const result = await sandbox.run("python", { args: ["main.py"] });
console.log(result.stdout);
```

### List, Update

In 0.5.1, rename and port-exposure live on the `Sandbox` instance via `sandbox.update(...)`. `SandboxClient` is still required for listing sandboxes (no instance equivalent) and emits a `DeprecationWarning` on construction.

**Python:**

```python
from tensorlake.sandbox import Sandbox, SandboxClient

# Rename / promote ephemeral → named, or change exposed ports — instance method (preferred)
info = sandbox.update(name="my-env")                            # -> Traced[SandboxInfo]
info = sandbox.update(exposed_ports=[8080], allow_unauthenticated_access=False)
print(info.value.name, info.value.exposed_ports)

# Listing still requires SandboxClient
client = SandboxClient()
for sb in client.list():                                        # -> iterator[SandboxInfo]
    print(sb.sandbox_id, sb.status)
```

> Legacy client form `client.update_sandbox("sbx-123", "my-env")` still works in 0.5.x but is **deprecated** — prefer `sandbox.update(...)` on the instance handle. If you only have a `sandbox_id`, do `Sandbox.connect("sbx-123").update(name="my-env")`.

**TypeScript:**

```typescript
import { Sandbox, SandboxClient } from "tensorlake";

const client = new SandboxClient();
const sandboxes = await client.list();
for (const sb of sandboxes) {
  // status values are capitalized strings: "Pending" | "Running" | "Suspending" | "Suspended" | "Snapshotting" | "Terminated"
  console.log(sb.sandboxId, sb.name, sb.status, sb.createdAt);
}

// Filter then terminate — terminate is an INSTANCE method, so connect first
const stale = sandboxes.filter((sb) => sb.status === "Suspended");
for (const sb of stale) {
  const handle = await Sandbox.connect(sb.sandboxId);
  await handle.terminate();
}

// Rename via the client (legacy but still supported)
const renamed = await client.update("sbx-123", { name: "my-env" });
console.log(renamed.name);
```

> Termination is an **instance** method (`sandbox.terminate()` / `await sandbox.terminate()`), not a static or client method. There is no `client.delete(id)` — get a handle via `Sandbox.connect(...)` first if you only have an identifier. The `status` field on `SandboxInfo` is the capitalized string form (`"Suspended"`, not `"suspended"`); the lowercase form only appears as `sandbox.status.value` on the Python `SandboxStatus` enum.

### Snapshot Management (Static)

```python
info = Sandbox.get_snapshot("snap-xyz")          # -> SnapshotInfo
Sandbox.delete_snapshot("snap-xyz")              # -> None
```

```typescript
const info = await Sandbox.getSnapshot("snap-xyz");
await Sandbox.deleteSnapshot("snap-xyz");
```

### Port Exposure

In 0.5.1, prefer `sandbox.update(exposed_ports=[...], allow_unauthenticated_access=...)` on the instance. `SandboxClient.expose_ports(...)` / `unexpose_ports(...)` and the CLI still work. Full examples and the auth-vs-public trade-off live in [Networking → Port Exposure](#port-exposure) below.

## Sandbox — Instance Methods

Once you have a `Sandbox` handle (from `create` or `connect`), use these methods directly on it.

### Lifecycle

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

Suspend/resume only works on **named** sandboxes. Ephemeral sandboxes return an error. To convert an ephemeral sandbox into a named one after creation, call `sandbox.update(name="my-env")` on the instance handle — same `sandbox_id` is preserved, no recreation needed. (The legacy `SandboxClient().update_sandbox(id, name)` form still works but is deprecated.) Note: this is fundamentally different from `sandbox.checkpoint()` + `Sandbox.create(snapshot_id=...)`, which produces a *new* sandbox with a *new* `sandbox_id`.

### Snapshots (Instance)

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

### Execute Commands

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

> **Canonical forms — don't invent variants.** For LLM tool-use, the idiom is `sandbox.run("python", ["-c", code])`. There is no `sandbox.exec()`, `sandbox.python()`, `sandbox.eval()`, or `sandbox.repl()`. The return object exposes exactly `stdout`, `stderr`, `exit_code` (Python) / `stdout`, `stderr`, `exitCode` (TypeScript) — don't reference `.output`, `.result`, `.logs`, or streaming fields like `.stream` / `.lines` on the result. For live stdout from a long-running process, use `start_process` + `follow_output` (see [Process Management](#process-management)), not a fabricated field on `run()`.

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
data = sandbox.read_file("/workspace/data.csv").value    # -> bytes (unwrap Traced)
print(data.decode())
entries = sandbox.list_directory("/workspace").value.entries  # entries[].name, entries[].size
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

### Process Management

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

### Process stdin/stdout/stderr (Granular)

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

### Interactive PTY Session

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
console.log(await pty.wait());
```

> **Python differs.** `create_pty()` in Python does not accept `on_data` / `on_exit` in its keyword arguments. Attach them after creation via `pty.on_data(callback)` and `pty.on_exit(callback)` instead. TypeScript supports both forms — at-creation in the options object, or post-creation via `pty.onData(...)` / `pty.onExit(...)`.

## Computer Use (Desktop Automation)

Use the `ubuntu-vnc` image to get a desktop-enabled sandbox with XFCE, TigerVNC, and Firefox. Desktop connections are proxied through an authenticated endpoint — no port exposure needed.

**Python:**

```python
from tensorlake.sandbox import Sandbox
from pathlib import Path
import time

sandbox = Sandbox.create(image="ubuntu-vnc")
try:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        time.sleep(4.0)  # XFCE + desktop services need a few seconds before screenshots are reliable
        Path("sandbox-desktop.png").write_bytes(desktop.screenshot())
        print(f"desktop is {desktop.width}x{desktop.height}")

        desktop.press(["ctrl", "alt", "t"])
        time.sleep(1.0)
        desktop.type_text("echo docs-test > /tmp/desktop-test.txt")
        desktop.press("enter")

    result = sandbox.run("bash", ["-lc", "cat /tmp/desktop-test.txt"])
    print(result.stdout.strip())
finally:
    sandbox.terminate()
```

### Reconnecting to an Existing Desktop Sandbox

```python
sandbox = Sandbox.connect("your-running-sandbox-id")
with sandbox.connect_desktop(password="tensorlake") as desktop:
    Path("existing-sandbox.png").write_bytes(desktop.screenshot())
```

### Desktop Methods and Properties

**Properties** (no parentheses — read directly):

| Property  | Description                          |
|-----------|--------------------------------------|
| `width`   | Desktop width in pixels              |
| `height`  | Desktop height in pixels             |

**Methods** (Python `snake_case` shown; TypeScript mirrors in `camelCase` — e.g., `moveMouse`, `mousePress`):

| Method             | Description                                              |
|--------------------|----------------------------------------------------------|
| `screenshot()`     | Returns PNG bytes of the current desktop                 |
| `press(key)`       | Press key or key combo (e.g., `["ctrl", "alt", "t"]`)    |
| `type_text(text)`  | Type text input                                          |
| `move_mouse(x, y)` | Move cursor to coordinates                               |
| `click()`          | Single mouse click at current cursor position            |
| `double_click()`   | Double mouse click at current cursor position            |
| `mouse_press()`    | Press a mouse button (held — pair with `mouse_release`)  |
| `mouse_release()`  | Release a held mouse button                              |
| `scroll()`         | Scroll (generic — direction/amount via parameters)       |
| `scroll_up()`      | Scroll up                                                |
| `scroll_down()`    | Scroll down                                              |
| `key_down()`       | Press and hold a key (pair with `key_up`)                |
| `key_up()`         | Release a held key                                       |
| `close()`          | Close desktop connection (auto on context-manager exit)  |

> **Startup delay.** Fresh `ubuntu-vnc` sandboxes need a few seconds (≈4s) for XFCE and the rest of the desktop services to finish booting before screenshots are reliable. Sleep before the first `screenshot()` or you may capture a blank/loading frame.

### Browser Access with noVNC

For a live human-facing desktop stream (instead of polling `screenshot()`), bridge the sandbox's VNC port to the browser with [`noVNC`](https://novnc.com/info.html):

1. Keep `TENSORLAKE_API_KEY` on the backend.
2. Backend opens a TCP tunnel to the sandbox's VNC port `5901`.
3. Bridge that tunnel to a browser WebSocket endpoint (e.g. `/vnc/<session-id>`).
4. Point `noVNC` at your backend WebSocket; authenticate with desktop password `tensorlake`.

You do **not** need to expose port `5901` publicly. For hybrid agent + human sessions, use `noVNC` for the live view and `sandbox.connect_desktop()` for programmatic actions on the backend.

```bash
npm install @novnc/novnc
```

```ts
import RFB from "@novnc/novnc/lib/rfb";

const host = document.getElementById("desktop") as HTMLDivElement;
const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const url = `${protocol}//${window.location.host}/vnc`;

const rfb = new RFB(host, url, {
  credentials: { password: "tensorlake" },
  shared: true,
});
rfb.scaleViewport = true;
```

```html
<div id="desktop" style="width: 1200px; height: 800px; background: black;"></div>
```

### Notes

- Default VNC password for managed `ubuntu-vnc` image: `"tensorlake"`
- Desktop connection is proxied through an authenticated endpoint (no port exposure needed)
- `Sandbox.connect()` returns a handle that does **not** auto-terminate the sandbox; call `.terminate()` explicitly when done

## Sandbox Images

A sandbox image is a project-scoped, named snapshot built from a base image plus build steps. Three definition formats — Python DSL, TypeScript DSL, Dockerfile — and three build paths.

### Define an Image

**Python:**

```python
from tensorlake import Image

image = (
    Image(name="data-tools-image", base_image="ubuntu-systemd")
    .copy("requirements.txt", "/tmp/requirements.txt")
    .run("apt-get update && apt-get install -y python3 python3-pip")
    .run("python3 -m pip install --break-system-packages -r /tmp/requirements.txt")
    .run("mkdir -p /workspace/cache")
    .env("APP_ENV", "prod")
)

image.build()
```

**TypeScript:**

```typescript
import { Image } from "tensorlake";

const image = new Image({
  name: "data-tools-image",
  baseImage: "ubuntu-systemd",
})
  .copy("requirements.txt", "/tmp/requirements.txt")
  .run("apt-get update && apt-get install -y python3 python3-pip")
  .run("python3 -m pip install --break-system-packages -r /tmp/requirements.txt")
  .run("mkdir -p /workspace/cache")
  .env("APP_ENV", "prod")
  .workdir("/workspace");

await image.build();
```

**Dockerfile:**

```dockerfile
FROM ubuntu-systemd

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
    Image(name="etl-tools", base_image="ubuntu-minimal")
    .run("apt-get update && apt-get install -y python3 python3-pip")
    .run("python3 -m pip install --break-system-packages pandas pyarrow duckdb")
)
image.build()

sandbox = Sandbox.create(image="etl-tools", cpus=4.0, memory_mb=8192)
result = sandbox.run("python3", ["-c", "import pandas, pyarrow, duckdb; print('ok')"])
print(result.stdout, result.exit_code)
```

### Build / Register the Image

Build-time resources default to `cpus=2.0`, `memory_mb=4096`, `disk_mb=10240` (10 GiB) and are passed to the build call (not the `Image(...)` constructor):

**Python:**

```python
image.build()                                   # use defaults

image.build(
    cpus=4.0,
    memory_mb=4096,
    disk_mb=25600,                              # 25 GiB build/root disk
)
```

**TypeScript:**

```typescript
await image.build();
```

**CLI (Dockerfile only):**

```bash
tl sbx image create ./Dockerfile --registered-name data-tools-image
tl sbx image create ./Dockerfile \
  --registered-name data-tools-image \
  --cpus 4 --memory 4096 --disk_mb 25600
```

The positional argument is a Dockerfile path. The `-n/--registered-name` flag sets the registered name; if omitted, it defaults to the parent directory when the file is named `Dockerfile`, otherwise the file stem. Names must be unique within a project.

> **Disk size carries over to launched sandboxes.** Use a larger build-time `disk_mb` when you want to bake big dependencies into the image without forcing every consumer to override `disk_mb` at `Sandbox.create()` time. CPU and memory are *not* inherited — they fall back to `Sandbox.create()`'s own `cpus` / `memory_mb` (defaults `1.0` / `1024`) unless explicitly set at launch.

Before building, run `tl login` and `tl init` (or `npx tl init`) to select the target project.

### Base Images

| Base Image          | Description                                                                                              |
|---------------------|----------------------------------------------------------------------------------------------------------|
| `ubuntu-minimal`    | Default. Minimal Ubuntu, no systemd, boots in hundreds of ms.                                            |
| `ubuntu-systemd`    | Ubuntu with systemd, supports Docker/K8s inside the sandbox.                                             |
| `ubuntu-vnc`        | Desktop-enabled (XFCE + TigerVNC + Firefox) — use with `sandbox.connect_desktop()` for computer-use.     |
| `debian11-minimal`  | Minimal Debian 11.                                                                                       |
| `debian12-minimal`  | Minimal Debian 12.                                                                                       |
| `debian-minimal`    | Minimal Debian 13.                                                                                       |

Use these short names directly in `base_image=` / `baseImage:`, in `FROM`, and in `image=` when launching a sandbox from a base image (no `tensorlake/` prefix).

### Image Builder Methods (chainable)

- `.run(command)` — execute shell command during build
- `.env(key, value)` — set environment variable
- `.copy(src, dest)` — copy file from local build context
- `.add(src, dest)` — add file from local build context
- `.workdir(path)` — set working directory (TypeScript). For Python, set `WORKDIR` via a Dockerfile if needed.

### Supported Build Operations

Materialized into the snapshot: `RUN`, `WORKDIR`, `ENV`, `COPY`, `ADD`. Preserved as metadata only (not executed): `CMD`, `ENTRYPOINT`, `EXPOSE`, `HEALTHCHECK`, `LABEL`, `STOPSIGNAL`, `VOLUME`. Not supported: `ARG`, `ONBUILD`, `SHELL`, `USER`, multi-stage Dockerfiles, remote `COPY`/`ADD` sources.

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

These are parameters on `Sandbox.create()`. Port exposure (`exposed_ports`, `allow_unauthenticated_access`) is a separate post-create operation in 0.5.1 — see [Port Exposure](#port-exposure).

### Public URLs

- Management API: `https://<sandbox-id-or-name>.sandbox.tensorlake.ai` (port `9501`, always authenticated)
- User services: `https://<port>-<sandbox-id-or-name>.sandbox.tensorlake.ai`
- Supports HTTP/1.1, HTTP/2, WebSocket upgrades, gRPC

The hostname accepts either the sandbox ID or a sandbox name.

### Port Exposure

In 0.5.1, prefer the `Sandbox` instance method:

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
await Sandbox.exposePorts("my-env", [8080], { allowUnauthenticatedAccess: false });
await Sandbox.unexposePorts("my-env", [8080]);
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

## Data Models

### SandboxInfo

| Field                          | Type                     | Description                                          |
|--------------------------------|--------------------------|------------------------------------------------------|
| `sandbox_id` / `sandboxId`     | `str`                    | Server-assigned UUID                                 |
| `name`                         | `str \| None`            | Name, or `None` for ephemeral                        |
| `namespace`                    | `str`                    | Namespace                                            |
| `status`                       | `str`                    | `"Pending" \| "Running" \| "Suspending" \| "Suspended" \| "Snapshotting" \| "Terminated"` |
| `image`                        | `str`                    | Container image used                                 |
| `resources`                    | `ContainerResourcesInfo` | `.cpus`, `.memory_mb`, `.disk_mb` (camelCase in TS)  |
| `secret_names`                 | `list[str]`              | Injected secret names                                |
| `timeout_secs`                 | `int`                    | Timeout in seconds                                   |
| `exposed_ports`                | `list[int]`              | User ports routed by the proxy                       |
| `allow_unauthenticated_access` | `bool`                   | Whether exposed user ports skip TensorLake auth      |
| `entrypoint`                   | `list[str]`              | Custom entrypoint command                            |
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

`snapshot_id` / `snapshotId`, `sandbox_id`, `status` (`"Pending" | "Ready" | "Failed"`), `size_bytes`, `created_at`.

### Process Status / Mode Enums

- **`SandboxProcessStatus`** — `running`, `exited`, `signaled`
- **`SandboxProcessStdinMode`** — `closed` (default), `pipe`
- **`SandboxProcessOutputMode`** — `capture`, `discard`

## CLI Quick Reference

```bash
tl sbx create                            # Create ephemeral sandbox
tl sbx create my-env                     # Create named sandbox
tl sbx create --image data-tools-image --cpus 2 --memory 2048 --timeout 600
tl sbx ls                                # List active sandboxes
tl sbx ls --all                          # Include suspended/terminated
tl sbx exec <id> <command>               # Execute command
tl sbx run <command>                     # Create, run, teardown
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
tl sbx image describe NAME               # Show registered Dockerfile + metadata
tl sbx port expose <id> 8080             # Expose port (sets allow_unauthenticated_access=true)
tl sbx port ls <id>
tl sbx port rm <id> 8080
```
