<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/computer-use.md
SDK version: tensorlake 0.5.5
Last verified: 2026-04-30
-->

# Computer Use (Desktop Automation)

Use the `ubuntu-vnc` image to get a desktop-enabled sandbox with XFCE, TigerVNC, and Firefox. Desktop connections are proxied through an authenticated endpoint — no port exposure needed.

For sandbox creation, lifecycle, and the rest of the SDK surface, see [sandbox_sdk.md](sandbox_sdk.md).

## Table of Contents

- [Quickstart](#quickstart)
- [Reconnecting to an Existing Desktop Sandbox](#reconnecting-to-an-existing-desktop-sandbox)
- [Desktop Methods and Properties](#desktop-methods-and-properties)
- [Browser Access with noVNC](#browser-access-with-novnc)
- [Notes](#notes)

## Quickstart

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

## Reconnecting to an Existing Desktop Sandbox

```python
sandbox = Sandbox.connect("your-running-sandbox-id")
with sandbox.connect_desktop(password="tensorlake") as desktop:
    Path("existing-sandbox.png").write_bytes(desktop.screenshot())
```

## Desktop Methods and Properties

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

## Browser Access with noVNC

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

## Notes

- Default VNC password for managed `ubuntu-vnc` image: `"tensorlake"`
- Desktop connection is proxied through an authenticated endpoint (no port exposure needed)
- `Sandbox.connect()` returns a handle that does **not** auto-terminate the sandbox; call `.terminate()` explicitly when done
