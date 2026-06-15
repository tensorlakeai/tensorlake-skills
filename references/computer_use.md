<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/computer-use.md
SDK version: tensorlake 0.5.44
Last verified: 2026-06-16
-->

# Computer Use (Desktop Automation)

Use the `tensorlake/ubuntu-vnc` image to get a desktop-enabled sandbox with XFCE, TigerVNC, and Firefox pre-installed. Desktop connections are proxied through an authenticated endpoint — no port exposure required.

For sandbox creation, lifecycle, and the rest of the SDK surface, see [sandbox_sdk.md](sandbox_sdk.md). For browser automation against the in-sandbox Chrome via the Chrome DevTools Protocol, see [sandbox_usecases.md](sandbox_usecases.md#drive-chrome-over-cdp). For warm-desktop forking, see [sandbox_persistence.md](sandbox_persistence.md).

## Table of Contents

- [Quickstart](#quickstart)
- [Reconnect to an Existing Desktop Sandbox](#reconnect-to-an-existing-desktop-sandbox)
- [Connect with a VNC Client](#connect-with-a-vnc-client)
- [Desktop Methods and Properties](#desktop-methods-and-properties)
- [Browser Access with noVNC](#browser-access-with-novnc)
- [Notes](#notes)

## Quickstart

**Python:**

```python
from tensorlake.sandbox import Sandbox
from pathlib import Path
import time

sandbox = Sandbox.create(image="tensorlake/ubuntu-vnc")
try:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        # XFCE + keybind daemon need a few seconds to settle. On a freshly
        # restored snapshot, vncserver is up before XFCE finishes booting, so
        # the first Ctrl+Alt+T can be dropped if sent too early.
        time.sleep(5.0)

        Path("sandbox-desktop.png").write_bytes(desktop.screenshot())
        print(f"desktop is {desktop.width}x{desktop.height}")

        desktop.press(["ctrl", "alt", "t"])
        time.sleep(4.0)
        desktop.type_text("echo docs-test > /tmp/desktop-test.txt")
        desktop.press("enter")
        time.sleep(3.0)

        # Mouse helpers when you know the coordinates.
        desktop.move_mouse(640, 400)
        desktop.scroll_down()

    result = sandbox.run("bash", ["-lc", "cat /tmp/desktop-test.txt"])
    print(result.stdout.strip())  # docs-test
finally:
    sandbox.terminate()
```

**JavaScript:**

```javascript
import { Sandbox } from "tensorlake";
import { writeFile } from "node:fs/promises";

const sandbox = await Sandbox.create({ image: "tensorlake/ubuntu-vnc" });
try {
  const desktop = await sandbox.connectDesktop({ password: "tensorlake" });
  try {
    await new Promise((r) => setTimeout(r, 5000));
    await writeFile("sandbox-desktop.png", await desktop.screenshot());

    await desktop.press(["ctrl", "alt", "t"]);
    await new Promise((r) => setTimeout(r, 4000));
    await desktop.typeText("echo docs-test > /tmp/desktop-test.txt");
    await desktop.press("enter");
    await new Promise((r) => setTimeout(r, 3000));

    await desktop.moveMouse(640, 400);
    await desktop.scrollDown();
  } finally {
    await desktop.close();
  }

  const result = await sandbox.run("bash", { args: ["-lc", "cat /tmp/desktop-test.txt"] });
  console.log(result.stdout.trim()); // docs-test
} finally {
  await sandbox.terminate();
}
```

## Reconnect to an Existing Desktop Sandbox

```python
from pathlib import Path
from tensorlake.sandbox import Sandbox

with Sandbox.connect("your-running-sandbox-id") as sandbox:
    with sandbox.connect_desktop(password="tensorlake") as desktop:
        Path("existing-sandbox.png").write_bytes(desktop.screenshot())
```

```javascript
import { Sandbox } from "tensorlake";
import { writeFile } from "node:fs/promises";

const sandbox = await Sandbox.connect({ sandboxId: "your-running-sandbox-id" });
try {
  const desktop = await sandbox.connectDesktop({ password: "tensorlake" });
  try {
    await writeFile("existing-sandbox.png", await desktop.screenshot());
  } finally {
    await desktop.close();
  }
} finally {
  sandbox.close(); // closes the client connection — does NOT terminate the VM
}
```

`sandbox.close()` (or exiting the Python `with` block on a connected handle) closes the client connection only. The sandbox VM keeps running. To stop it, call `sandbox.terminate()` explicitly.

## Connect with a VNC Client

To drive the desktop from a real VNC viewer (macOS Screen Sharing, TigerVNC, RealVNC, Remmina, etc.), open a local tunnel to port `5901` inside the sandbox. The tunnel keeps sandbox-proxy auth local — you do **not** need to expose `5901` publicly.

```bash
tl sbx tunnel <sandbox-id> 5901 --listen-port 15901
```

Leave it running. It forwards `127.0.0.1:15901` to port `5901` inside the sandbox over an authenticated WebSocket. Then point your viewer at `localhost:15901` (password: `tensorlake`):

- **macOS:** `open vnc://localhost:15901`
- **Linux (TigerVNC):** `vncviewer localhost:15901` (`apt install tigervnc-viewer` or `dnf install tigervnc`)
- **Other RFB viewers** (RealVNC, TightVNC, Remmina, KRDC): point at `localhost:15901`

Stop the tunnel with `Ctrl+C`. Closing the tunnel does not terminate the sandbox.

## Desktop Methods and Properties

**Properties** (no parentheses — read directly):

| Property  | Description                          |
|-----------|--------------------------------------|
| `width`   | Desktop width in pixels              |
| `height`  | Desktop height in pixels             |

**Methods** (Python `snake_case` shown; TypeScript mirrors in `camelCase` — e.g., `moveMouse`, `mousePress`, `doubleClick`, `typeText`, `scrollDown`, `keyDown`):

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

> **Startup delay.** Fresh `tensorlake/ubuntu-vnc` sandboxes need a few seconds (≈5s) for XFCE and the keybind daemon to settle. On a freshly restored snapshot, `vncserver` is up before XFCE finishes — the first `Ctrl+Alt+T` can be dropped if sent too early. Sleep before the first action and before screenshots.

Coordinate-based actions are screen-relative. Common workflow: take a screenshot → inspect → call `move_mouse()` / `click()` / `double_click()` / `scroll()` with the noted coordinates.

## Browser Access with noVNC

For a live human-facing desktop stream (instead of polling `screenshot()`), bridge the sandbox's VNC port to the browser with [`noVNC`](https://novnc.com/info.html):

1. Keep `TENSORLAKE_API_KEY` on the backend.
2. Backend opens a TCP tunnel to the sandbox's VNC port `5901`.
3. Bridge that tunnel to a browser WebSocket endpoint (e.g. `/vnc/<session-id>`).
4. Point `noVNC` at your backend WebSocket; authenticate with desktop password `tensorlake`.

You do **not** need to expose port `5901` publicly. For hybrid agent + human sessions, use `noVNC` for the live view and `sandbox.connect_desktop()` for programmatic actions on the backend — that separation avoids turning the browser into a screenshot polling loop.

```bash
npm install @novnc/novnc
```

```ts
import RFB from "@novnc/novnc/lib/rfb";

const host = document.getElementById("desktop");
if (!(host instanceof HTMLDivElement)) {
  throw new Error("Missing #desktop container");
}

const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const url = `${protocol}//${window.location.host}/vnc`;

const rfb = new RFB(host, url, {
  credentials: { password: "tensorlake" },
  shared: true,
});
rfb.scaleViewport = true;
rfb.clipViewport = false;
rfb.showDotCursor = true;
```

```html
<div id="desktop" style="width: 1200px; height: 800px; background: black;"></div>
```

## Notes

- Image name is `tensorlake/ubuntu-vnc` (fully qualified). The unqualified `ubuntu-vnc` alias may still resolve but the qualified form is canonical.
- Default VNC password for the managed image: `"tensorlake"`.
- Desktop connection is proxied through an authenticated endpoint — no port exposure required for SDK-driven automation.
- `sandbox.close()` on a `Sandbox.connect(...)` handle closes the client only; call `sandbox.terminate()` to stop the VM.
- For warm-desktop forking (parallelize agent runs without re-launching XFCE), see snapshots in [sandbox_persistence.md](sandbox_persistence.md).
