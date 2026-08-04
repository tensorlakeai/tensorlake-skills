<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/skills-in-sandboxes.md
  - https://docs.tensorlake.ai/sandboxes/tool-calls.md
  - https://docs.tensorlake.ai/sandboxes/claude-managed-agents.md
  - https://docs.tensorlake.ai/sandboxes/opencode.md
  - https://docs.tensorlake.ai/sandboxes/crabbox.md
  - https://docs.tensorlake.ai/sandboxes/devin-outposts.md
  - https://docs.tensorlake.ai/sandboxes/data-analysis.md
  - https://docs.tensorlake.ai/sandboxes/cicd-build.md
  - https://docs.tensorlake.ai/sandboxes/agentic-autoresearch.md
  - https://docs.tensorlake.ai/sandboxes/agentic-rl-reproducible-env.md
  - https://docs.tensorlake.ai/sandboxes/agentic-swarm-intelligence.md
  - https://docs.tensorlake.ai/sandboxes/agentic-d&g.md
  - https://docs.tensorlake.ai/sandboxes/gspo-agentic-rl.md
  - https://docs.tensorlake.ai/sandboxes/chrome-cdp.md
  - https://docs.tensorlake.ai/sandboxes/harbor.md
  - https://docs.tensorlake.ai/sandboxes/remote-dev.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Sandbox Use Cases

## Table of Contents

- [Skills in Sandboxes](#skills-in-sandboxes)
- [AI Code Execution](#ai-code-execution)
- [Claude Managed Agents](#claude-managed-agents)
- [OpenCode](#opencode)
- [Crabbox (test suites)](#crabbox-test-suites)
- [Devin Outposts](#devin-outposts)
- [Agentic Swarm Intelligence](#agentic-swarm-intelligence)
- [Agentic Dungeons & Dragons](#agentic-dungeons--dragons)
- [Agentic Autoresearch Loop](#agentic-autoresearch-loop)
- [RL Reproducible Environments](#rl-reproducible-environments)
- [RL Training with GSPO](#rl-training-with-gspo)
- [Data Analysis](#data-analysis)
- [CI/CD Build Pipelines](#cicd-build-pipelines)
- [Sandbox as a Dev Environment](#sandbox-as-a-dev-environment)
- [Drive Chrome over CDP](#drive-chrome-over-cdp)
- [Harbor (evals + RL rollouts)](#harbor-evals--rl-rollouts)

## Skills in Sandboxes

Install agent skill files into sandbox images so coding agents (Claude Code, Codex, Cursor, etc.) can discover TensorLake SDK references at startup.

**Scope note:** These patterns apply only to sandbox images the user is explicitly building for their own agents. Do **not** write to discovery paths like `~/.claude/skills/` or `~/.agents/skills/` on the user's host machine, on shared systems, or on any environment the user has not asked you to modify — that would change the behavior of other agents/tools outside the current task. The commands below are templates for the user to include in their own `Image(...)` definitions when they want the skill bundled inside a sandbox they control.

### Agent Discovery Paths

| Agent | Skill Location |
|-------|---------------|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` |
| OpenAI Codex | `~/.agents/skills/<name>/SKILL.md` or `AGENTS.md` in working dir |
| Google ADK | Loaded via `load_skill_from_dir()` |
| Cursor | `.cursor/rules/*.mdc` |
| Cline | `.clinerules/` |
| Windsurf | `.windsurf/rules/*.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |

### Installation via Skills CLI (Multi-Agent)

**Python:**

```python
from tensorlake import Image

image = (
    Image(name="with-skills", base_image="tensorlake/ubuntu-systemd")
    .run("apt-get update && apt-get install -y nodejs npm python3 python3-pip")
    .run("npm install -g skills")
    .run("skills add tensorlakeai/tensorlake-skills --all -y --copy")
    .run("python3 -m pip install --break-system-packages tensorlake")
)
```

**TypeScript:**

```typescript
import { Image } from "tensorlake";

const image = new Image({
  name: "with-skills",
  baseImage: "tensorlake/ubuntu-systemd",
})
  .run("apt-get update && apt-get install -y nodejs npm python3 python3-pip")
  .run("npm install -g skills")
  .run("skills add tensorlakeai/tensorlake-skills --all -y --copy")
  .run("python3 -m pip install --break-system-packages tensorlake");
```

Flags: `--all` deploys to all detected agents, `-y` non-interactive, `--copy` avoids symlink issues in containers.

### Claude Code Specific Setup

**Python:**

```python
from tensorlake import Image

image = (
    Image(name="claude-code-skills", base_image="tensorlake/ubuntu-systemd")
    .run("apt-get update && apt-get install -y git python3 python3-pip")
    .run("git clone https://github.com/tensorlakeai/tensorlake-skills /tmp/tensorlake-skills")
    .run("mkdir -p /root/.claude/skills/tensorlake && cp -r /tmp/tensorlake-skills/SKILL.md /tmp/tensorlake-skills/references /root/.claude/skills/tensorlake/")
    .run("rm -rf /tmp/tensorlake-skills")
    .run("python3 -m pip install --break-system-packages tensorlake")
)
```

**TypeScript:**

```typescript
import { Image } from "tensorlake";

const image = new Image({
  name: "claude-code-skills",
  baseImage: "tensorlake/ubuntu-systemd",
})
  .run("apt-get update && apt-get install -y git python3 python3-pip")
  .run("git clone https://github.com/tensorlakeai/tensorlake-skills /tmp/tensorlake-skills")
  .run("mkdir -p /root/.claude/skills/tensorlake && " +
    "cp -r /tmp/tensorlake-skills/SKILL.md /tmp/tensorlake-skills/references /root/.claude/skills/tensorlake/")
  .run("rm -rf /tmp/tensorlake-skills")
  .run("python3 -m pip install --break-system-packages tensorlake");
```

### Image Creation

```bash
tl sbx image create Dockerfile --registered-name claude-code-skills
tl sbx create --image claude-code-skills
```

### Runtime Installation (SDK)

```python
from tensorlake.sandbox import Sandbox

sandbox = Sandbox.create()
try:
    sandbox.run("bash", ["-c", "apt-get update && apt-get install -y nodejs npm"])
    sandbox.run("bash", ["-c", "npm install -g skills"])
    sandbox.run("bash", ["-c", "skills add tensorlakeai/tensorlake-skills --all -y --copy"])

    result = sandbox.run("find", ["/", "-name", "SKILL.md", "-type", "f", "-not", "-path", "*/node_modules/*"])
    print(result.stdout)
finally:
    sandbox.terminate()
```

---

## AI Code Execution

Use sandboxes as LLM tool-call targets for safe code execution.

> **⚠ Each tool call is a fresh Python process.** `sandbox.run("python", ["-c", code])` spawns a new interpreter every time. Files written to disk and packages installed via `pip` **do** persist across calls in the same sandbox. Python variables, imports, and module-level state **do not**. If a user (or an earlier message) describes this as a "REPL session" or asks for "persistent variables between turns," correct the framing — the sandbox is a persistent *filesystem*, not a persistent *interpreter*.

### Architecture Pattern

1. Create a single sandbox at session start
2. Reuse it across tool calls — files and installed packages persist; Python variables/imports do NOT (each run is a fresh process)
3. Close when done

**Python:**

```python
from tensorlake.sandbox import Sandbox

sandbox = Sandbox.create(
    cpus=1.0,
    memory_mb=1024,
    timeout_secs=600,
    allow_internet_access=False,  # important for untrusted code
)

result = sandbox.run("python", ["-c", code])
# result.stdout, result.stderr, result.exit_code
```

**TypeScript:**

```typescript
import { Sandbox } from "tensorlake";

const sandbox = await Sandbox.create({
  cpus: 1.0,
  memoryMb: 1024,
  timeoutSecs: 600,
  allowInternetAccess: false,
});

async function runCode(code: string): Promise<string> {
  const result = await sandbox.run("python", {
    args: ["-c", code],
  });

  const chunks = [result.stdout.trim()];
  if (result.stderr.trim()) chunks.push(`[stderr]\n${result.stderr.trim()}`);
  if (result.exitCode !== 0) chunks.push(`[exit code: ${result.exitCode}]`);
  return chunks.filter(Boolean).join("\n\n") || "(no output)";
}

try {
  const output = await runCode("import statistics\nnums = [4, 8, 15, 16, 23, 42]\nprint(statistics.mean(nums))");
  console.log(output);
} finally {
  await sandbox.terminate();
}
```

### Snapshots for Pre-installed Dependencies

```python
snapshot = sandbox.checkpoint()
sandbox = Sandbox.create(snapshot_id=snapshot.snapshot_id)
```

### Integration Patterns

**Claude (Anthropic):** Define a `run_code` tool in the tools schema. Detect `tool_use` blocks in responses, execute via `sandbox.run()`, return results as `tool_result`.

**OpenAI Function Calling:** Structure sandbox as a function definition. Parse `tool_calls`, execute, append results to message history.

**OpenAI Agents SDK:** Wrap sandbox execution with `@function_tool` decorator.

### Best Practices

- **Reuse sandboxes** — creating new ones per tool call adds cold-start latency and loses filesystem state
- **Set `allow_internet_access=False`** for untrusted code. If you need `pip install` on demand, pre-bake deps into a custom image or snapshot instead of flipping internet access on for untrusted code
- **Pre-install deps via snapshots** or let agents `pip install` on demand (only in trusted setups)
- **Tear down** with `sandbox.terminate()` when the session ends

### Anti-patterns

Do not work around the fresh-process model by building a persistent interpreter:

- **Don't use `start_process` + `write_stdin`** to keep a long-running `python` kernel alive and pipe code into it. `sandbox.run("python", ["-c", code])` is the supported shape. A long-running stdin-fed kernel is not a documented pattern and gives up the clean per-call stdout/stderr/exit_code contract.
- **Don't tell the downstream LLM that variables persist across turns** in its system prompt. They don't. Tell it instead: "You have a persistent workspace directory and installed packages; module imports and variables reset between calls — write intermediate state to `/workspace/` if you need it across turns."
- **Don't flip `allow_internet_access=True` to enable pip for untrusted code.** Pre-install dependencies into a custom `Image` or a snapshot, then boot the sandbox from that snapshot with `snapshot_id=`.
- **Don't fabricate methods or fields.** There is no `sandbox.exec()`, `sandbox.python()`, `sandbox.eval()`, `sandbox.repl()`, or `persistent=True` / `repl_mode=True` / `session=True` kwarg. The return object has `stdout`, `stderr`, `exit_code` — not `.output`, `.result`, or `.logs`.

---

## Claude Managed Agents

Run Anthropic's [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview) agent loop on Anthropic's infrastructure while every tool call executes inside a Tensorlake sandbox you own. Reference integration: [`claude-managed-agents-tensorlake-sandbox`](https://github.com/tensorlakeai/claude-managed-agents-tensorlake-sandbox) (`examples/managed-agent`).

### Brain vs. hands

A Managed Agent splits into two halves. **Claude is the brain** — the LLM, the agent loop, session state, and the work queue live on Anthropic's infrastructure; it decides *which* tool to call but never executes one. **The sandbox is the hands** — every `bash`, `read`, `write`, `edit`, `glob`, `grep` call runs inside an execution environment you control. A Claude *Environment* with hosting type **Self-hosted** enqueues a work item per session run instead of running tools itself; your **orchestrator** drains that queue and turns each session into a Tensorlake sandbox running a thin worker that attaches back to Anthropic and executes tool calls for the life of the session.

### Why Tensorlake fits the "hands" role

- **Sub-second wake.** An agent loop is a tight decide→execute→decide cycle — many short tool calls separated by model think-time. A suspended sandbox resumes from its memory snapshot in **~0.6s** (a restore, not a cold boot), so the hands are ready the instant the brain calls a tool, without keeping a sandbox warm between turns.
- **Snapshots & fork-from-snapshot.** `sandbox.checkpoint()` then `Sandbox.create(snapshot_id=...)` × N forks N children from one known-good state — the basis for best-of-N tool execution and [parallel sub-agents](sandbox_persistence.md#forking-from-a-snapshot).
- **Suspend / resume.** Named sandboxes suspend when idle and resume with state intact (see [Sandbox as a Dev Environment](#sandbox-as-a-dev-environment) for the same primitive applied to a workstation).
- **Public port exposure.** `expose_ports(...)` serves a process at `https://{port}-{id}.sandbox.tensorlake.ai` with TLS terminated by Tensorlake's proxy — no reverse proxy of your own (see [Local Tunnels and exposed ports](sandbox_sdk.md#local-tunnels)).

### Three orchestrator modes

The orchestrator logic is identical in all three (`orchestrator_lib.py`: get-or-create a sandbox per session, drain the queue). Only *where it runs* differs. **Run exactly one orchestrator per `ANTHROPIC_ENVIRONMENT_ID`.**

| Mode | Where it runs | Spawn latency | Needs |
|---|---|---|---|
| **Webhook-in-sandbox** (recommended) | Inside a Tensorlake sandbox, port exposed publicly | Sub-second, scale-to-zero | Nothing running on your side — wakes on request |
| **Polling** | Your machine / server | Seconds | A long-running host process |
| **Webhook** | Your machine / server | ~Instant | A public HTTPS endpoint + TLS |

In webhook-in-sandbox mode the FastAPI receiver runs *inside* a sandbox with port 5051 exposed publicly; Anthropic pushes webhooks straight to Tensorlake (no host process, no TLS of yours). The sandbox has a short idle timeout, so with no inbound traffic it suspends (memory + the running uvicorn process preserved) and the next webhook resumes it automatically. Outbound polling from inside the sandbox does *not* keep it awake. The result is push latency with nothing running or billed while idle.

### Long-running sessions: recreate vs. resume

The same suspend/resume primitive applies one layer down, to the **per-session** sandbox. At `SANDBOX_TIMEOUT_SECONDS` an idle session sandbox auto-suspends. On the next burst, `_find_live_sandbox` in `orchestrator_lib.py` treats a suspended sandbox as not-live and **recreates from base** (clean slate, but loses session working state — re-clone, re-install, redo setup). Set `RESUME_SUSPENDED_SESSIONS=true` to instead **resume the suspended sandbox** (sub-second memory-snapshot restore with `/workspace`, deps, and warm caches intact). Recreate suits independent, cheap-to-setup bursts; resume suits a session whose accumulated state *is* the work. Idle cost is zero either way.

### Injecting credentials and naming

Two SDK facts shape the orchestrator:

- **Inject env vars per command, not on create.** Pass every credential and per-session var (`ANTHROPIC_ENVIRONMENT_KEY`, plus the session, work, and environment IDs) via `start_process(env={...})`, which merges on top of the sandbox base environment.
- **Sandbox names must be slugs** — lowercase letters, digits, and hyphens only. Slugify a session id to derive a name (e.g. `agent-<slug>`).

### Setup shape

The repo README is the source of truth; the four stages are: (1) **Configure** — `uv sync`, copy the `.env` / `.env.local` examples; (2) **Tensorlake** — set `TENSORLAKE_API_KEY`, `uv run tl login`, `make build` the per-session image (keep the SDK key and `tl login` on the *same* project); (3) **Claude Platform** (Console-only, non-default workspace) — `make agent`, create a **Self-hosted** Environment, generate its environment key; (4) **Orchestrator** — pick a mode (for webhook-in-sandbox: `make build-webhook`, register the printed URL as a `Session lifecycle → Run started` webhook with its signing secret in `ANTHROPIC_WEBHOOK_SIGNING_KEY`, *then* `make webhook-sandbox` since the secret is baked in at launch). Drive a session with `make session PROMPT="..."`; success streams `running` / `thinking` / `→ write` / `→ read` ending in `· done`. Common failure modes: import-order 401 (load credentials before importing the SDK), mismatched Tensorlake projects, `workers_polling: 0` in webhook modes.

---

## OpenCode

[OpenCode](https://opencode.ai) is a terminal coding agent. The [`tensorlake-opencode`](https://www.npmjs.com/package/tensorlake-opencode) plugin redirects the agent's **hands** (its file and shell tools) into a Tensorlake sandbox while the TUI, model loop, and session stay local.

**What gets intercepted:**

| OpenCode tool | Runs in the sandbox as |
|---|---|
| `bash` | `sandbox.run('sh', { args: ['-c', cmd] })` |
| `read` | `sandbox.readFile(path)` |
| `write` | `sandbox.writeFile(path, content)` |
| `edit` | read + string replace + write |
| `ls` | `sandbox.listDirectory(path)` |
| `glob` | `find … -name "pattern"` via bash |
| `grep` | `grep -rn …` via bash |

`webfetch` and `websearch` are **not** intercepted — they stay local since they don't touch your filesystem.

**Setup.** Add the bare package name to `~/.config/opencode/opencode.json`; OpenCode treats bare names as npm packages and installs them into its own cache (`~/.cache/opencode/packages/`) — you don't run `npm install`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["tensorlake-opencode"]
}
```

Then export `TENSORLAKE_API_KEY` in the shell you launch `opencode` from. With a Personal Access Token instead of a project-scoped key, also set `TENSORLAKE_ORGANIZATION_ID` and `TENSORLAKE_PROJECT_ID`.

> **The sandbox is created lazily, on the first intercepted tool call** — not at launch. If you start OpenCode and nothing appears to happen, that's expected; a session that only uses `webfetch`/`websearch` never spins one up. Trigger creation by asking the model to run something (`Run: uname -a` → reports **Linux**, confirming remote execution). Confirm the plugin loaded with `tail -f ~/.local/share/opencode/log/tensorlake.log` (expect `OpenCode started with TensorLake plugin`).

The agent's working directory inside the sandbox is **`/tmp/workspace`**.

**Configuration is entirely by environment variable, read once at sandbox-creation time.** There is no config file for it. Set the variables *before* running `opencode`; changing them in another terminal or after the sandbox exists has no effect on the running session.

| Variable | Default | Controls |
|---|---|---|
| `TENSORLAKE_API_KEY` | (required) | Account/project the sandbox is created in |
| `TENSORLAKE_ORGANIZATION_ID` | (required for PAT keys) | Organization ID |
| `TENSORLAKE_PROJECT_ID` | (required for PAT keys) | Project ID |
| `TENSORLAKE_IMAGE` | (platform default) | Registered image the sandbox boots from |
| `TENSORLAKE_CPUS` | `2` | vCPUs |
| `TENSORLAKE_MEMORY_MB` | `4096` | RAM in MB |
| `TENSORLAKE_DISK_MB` | `10240` | Ephemeral disk in MB |

`TENSORLAKE_IMAGE` is the highest-impact setting for real work: bake language runtimes, system packages, and project deps into an image so the agent isn't reinstalling them every session. Put the exports in `~/.zshrc` / `~/.bashrc` to make them persistent.

---

## Crabbox (test suites)

[Crabbox](https://crabbox.sh) is an open-source CLI from OpenClaw whose loop is *warm a box, sync the diff, run the suite*. Its Tensorlake provider delegates the sandbox to the `tensorlake` CLI:

```sh
crabbox run --provider tensorlake --tensorlake-image tl-crabbox -- pnpm test
```

`tl-crabbox` is a **public image Tensorlake publishes for Crabbox**: the standard Ubuntu base plus a writable `/workspace` (Crabbox's default workdir) with pnpm preinstalled. It ships `node`, `npm`, `pnpm`, `corepack`, `python3`, and `git`.

Crabbox owns the local workflow (config, repo claims, sync manifests, guardrails); Tensorlake owns the microVM and command transport — under the hood Crabbox shells out to `tensorlake sbx create`, `cp`, `exec`, and `terminate`.

**Setup:**

```sh
brew install openclaw/tap/crabbox
curl -fsSL https://tensorlake.ai/install | sh
export TENSORLAKE_API_KEY=tl_apiKey_...
```

The `tensorlake` CLI must be on `PATH`, or point Crabbox at it with `--tensorlake-cli`. Crabbox passes the key through the environment — it never appears on the command line. For multi-org/project accounts also set `TENSORLAKE_ORGANIZATION_ID` and `TENSORLAKE_PROJECT_ID`.

`.crabbox.yaml` at the repo root:

```yaml
provider: tensorlake
tensorlake:
  image: tl-crabbox
```

> **The `image` pin matters.** Crabbox's default workdir is `/workspace/crabbox`, and in Tensorlake's standard images commands run as `tl-user`, which **cannot create `/workspace`**. Without the pin every run fails with `tensorlake exec "mkdir -p '/workspace/crabbox'" exited 1`. To use a standard image instead, set `tensorlake.workdir: /home/tl-user/crabbox`.

**Workflow:**

```sh
crabbox warmup --provider tensorlake --tensorlake-cpus 2 --tensorlake-memory-mb 2048
crabbox run --provider tensorlake -- pnpm test
crabbox run --provider tensorlake --shell 'pnpm install && pnpm test'   # shell pipelines
crabbox stop --provider tensorlake harbor-barnacle                      # release a warmed sandbox
```

Warmup creates a named sandbox and prints a friendly slug (e.g. `harbor-barnacle`) reusable across runs with `--id <slug>`. Every `tensorlake.*` config field has a matching `--tensorlake-*` flag and a `CRABBOX_TENSORLAKE_*` environment override. Crabbox syncs **git-tracked files** and streams output live. Forward secrets with `--allow-env API_TOKEN` (injected for the command, removed after). One-off runs lease and auto-terminate a sandbox; `--keep-on-failure` keeps it alive after a failing command.

**Troubleshooting:**

| Error | Cause | Fix |
|---|---|---|
| `build sync file list: exit status 128` | Not inside a git repository — Crabbox builds its sync list from `git ls-files` | Run from a repo root (`git init` if needed) |
| `tensorlake exec "mkdir -p '/workspace/crabbox'" exited 1` | Default workdir isn't writable by `tl-user` in standard images | Pin `tensorlake.image: tl-crabbox`, or set `tensorlake.workdir: /home/tl-user/crabbox` |
| `Failed to spawn process in <workdir>: No such file or directory` | The executable (e.g. `pnpm`) isn't in the image. The message blames the directory, but it's the missing binary | Pin `tl-crabbox`, use a tool the image has, or register your own image |

---

## Devin Outposts

[Devin Outposts](https://docs.devin.ai/cloud/outposts) runs Devin sessions inside infrastructure you control: the **agent loop stays in Cognition's cloud**, while the **session machine** — where commands run, files change, and repos get checked out — moves into a Tensorlake sandbox you own.

Use an outpost when the agent needs a custom environment: private CA certificates, preinstalled toolchains, pre-cloned repositories, or services only reachable from your network. Because Tensorlake can run on self-hosted compute, the sandboxes can sit inside your network where Devin can read your source, query your databases, and test against the systems it writes code for.

**Architecture.** An **orchestrator** watches Devin's session queue, claims each session, and runs it in a Tensorlake sandbox. The orchestrator itself runs inside a long-lived Tensorlake sandbox, so nothing long-running stays on your laptop. **Each Devin session maps to one sandbox**: idle → suspend, wake → resume the same sandbox, end → terminate. Sandboxes are Linux microVMs, so the outpost is **Linux only**. **Run one orchestrator per outpost.**

Reference implementation: [`tensorlakeai/devin-outposts-tensorlake`](https://github.com/tensorlakeai/devin-outposts-tensorlake), a Python package that is mainly the orchestrator plus CLI commands.

**Setup shape:**

1. **Install** — clone, venv, `pip install -e .`, `cp .env.example .env`, add `TENSORLAKE_API_KEY`.
2. **Connect the outpost** — `outposts-connect --platform linux`, run on the **same machine as your browser** (the browser returns a one-time code to a temporary `localhost` listener). A Devin org admin confirms and clicks **Connect**; the command exchanges the code for a machine-serving token and writes `DEVIN_OUTPOSTS_TOKEN`, `DEVIN_API_URL`, and `OUTPOST_ID` to `.env`. **The token never passes through the browser.**
3. **Build the session image** — `build-devin-outposts-image` (installs `git`, `curl`, CA certificates; GitHub CLI and Chromium are **best-effort**, so verify if your sessions need them; `ffmpeg` for screen recording is skipped — add it yourself if you want recordings). Copy the printed name into `IMAGE_NAME`.
4. **Build the orchestrator image** — `build-devin-outposts-dispatcher-image` (distinct from the session image; build once, rebuild on package updates).
5. **Launch the orchestrator** — `devin-outposts-orchestrator-sandbox`. **Idempotent**: re-running resumes the sandbox and re-ensures the process.
6. **Create a session** in the Devin UI or Slack, selecting your outpost.

**Security model.** The launcher reads your local `.env` and injects credentials into the orchestrator **process environment at start** — never baked into the image. Treat the orchestrator sandbox as a trusted control-plane host. **Session sandboxes never receive the machine token or your Tensorlake API key**; each remote gets only its own session's connect token. Each claim pins `devin-remote` (Devin's session binary) **by SHA** and verifies the checksum before executing. The binary dials out over HTTPS, so **the sandbox needs no inbound ports**. Rotate a credential by updating `.env`, then `--terminate` and relaunch.

**Operating it:**

```bash
devin-outposts-orchestrator-sandbox --status
devin-outposts-orchestrator-sandbox --logs
devin-outposts-orchestrator-sandbox --terminate
```

Outposts is **watch-based**, so the orchestrator runs continuously (not scale-to-zero). Tensorlake suspends a named sandbox after your plan's maximum idle window, and **a suspended orchestrator cannot claim sessions.** Because the launcher is idempotent, schedule it on a cron with an interval **shorter than your plan's idle window**:

```bash
*/15 * * * * cd /path/to/devin-outposts-tensorlake && set -a && . ./.env && set +a && .venv/bin/devin-outposts-orchestrator-sandbox
```

The cron host needs the repo, venv, and `.env`, and must be awake when the tick fires — an always-on machine is the better home. On a sleeping laptop the orchestrator can stay suspended and queued sessions wait for the next tick after wake.

**Session logs.** `--logs` shows orchestrator lifecycle events only (claim, sandbox created, serving, released). Per-session tool-call output is written **inside** the serving sandbox to `/tmp/devin-outposts/<session>.log`. The repo's `session_logs.py` helper reads them:

```bash
python session_logs.py                 # list this outpost's serving sandboxes
python session_logs.py <dvo-name>      # dump the last 500 lines
python session_logs.py <dvo-name> -f   # stream live
```

The sandbox name is the `dvo-...` string logged on claim. Live mode runs `tail -F` over a **PTY WebSocket**, reconnects on idle timeout, waits through suspension and re-attaches on resume, and exits when the sandbox is terminated.

**Configuration (`.env`):**

| Variable | Required | Purpose |
|---|---|---|
| `DEVIN_OUTPOSTS_TOKEN` | Yes | Machine-serving token for queue watch/claim/release |
| `DEVIN_API_URL` | No | Devin API base without `/opbeta`; defaults to `https://api.devin.ai` |
| `TENSORLAKE_API_KEY` | Yes | Authenticates the Tensorlake SDK for images and sandbox lifecycle |
| `OUTPOST_ID` | Yes | Your outpost |
| `IMAGE_NAME` | Yes | Image the orchestrator boots session sandboxes from |
| `MAX_CONCURRENT_SESSIONS` | No | Concurrent sessions (default `5`) |
| `SANDBOX_CPUS` / `SANDBOX_MEMORY_MB` / `SANDBOX_DISK_MB` | No | Per-session sizing (2 vCPU, 8 GiB, 10 GiB) |
| `SANDBOX_TIMEOUT_SECS` | No | Idle seconds before auto-suspend (default `1800`) |
| `REPOS` / `GIT_USERNAME` / `GIT_TOKEN` | No | Comma-separated clone URLs to pre-clone into each sandbox, plus credentials for private ones — passed to the clone command only, never stored in the image |

---

## Agentic Swarm Intelligence

Map-reduce over LLM agents: each worker generates perspective-specific code, executes it in its own sandbox, and a lead agent aggregates the worker reports.

### Pattern

1. **Workers (map)** — N specialist agents, each prompts an LLM for code from its own perspective
2. **Sandbox per worker** — generated code runs in an isolated sandbox with `allow_internet_access=False`
3. **Lead (reduce)** — aggregator agent synthesizes worker reports into final insights

### Python

```python
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from tensorlake.sandbox import Sandbox

class ScoutReport(BaseModel):
    agent_id: str
    raw_data: str

def scout_agent(task_id: str) -> ScoutReport:
    code = generate_perspective_code(task_id)  # LLM call
    sandbox = Sandbox.create(allow_internet_access=False)
    try:
        sandbox.run("pip", ["install", "--user", "--break-system-packages", "numpy"])
        result = sandbox.run("python", ["-c", code])
        return ScoutReport(agent_id=task_id, raw_data=result.stdout)
    finally:
        sandbox.terminate()

def intelligence_swarm(task_ids: list[str]):
    with ThreadPoolExecutor(max_workers=len(task_ids)) as pool:
        reports = list(pool.map(scout_agent, task_ids))
    return lead_aggregator(reports)  # LLM synthesis
```

### TypeScript

```typescript
import { Sandbox } from "tensorlake";

async function scoutAgent(taskId: string) {
  const code = await generatePerspectiveCode(taskId);
  const sandbox = await Sandbox.create({ allowInternetAccess: false });
  try {
    const result = await sandbox.run("python", { args: ["-c", code] });
    return { agentId: taskId, rawData: result.stdout };
  } finally {
    await sandbox.terminate();
  }
}

const reports = await Promise.all(taskIds.map(scoutAgent));
```

### Latency optimization

Pre-create a snapshot with the common deps (numpy, pandas, etc.) and boot each scout from `snapshot_id=` instead of pip-installing per call.

---

## Agentic Dungeons & Dragons

A fun, self-contained demo of the same map-reduce pattern as [Agentic Swarm Intelligence](#agentic-swarm-intelligence): a terminal D&D game where parallel "Scene Agents" draft branch outcomes and a "Dungeon Master" agent reduces them into the next story beat.

### Loop

1. **Branch** — for a player choice, enumerate a few candidate actions (e.g. *Fight*, *Flee*, *Negotiate*).
2. **Map** — one `scene_agent` per branch runs in parallel, each in its own sandbox. The agent asks an LLM (GPT-4o in the example) to emit a Python script that rolls a D20, decides success/failure, and prints a single JSON object (`narrative`, `consequences`, `image_prompt`, `ascii_art`). The script executes in the sandbox; its stdout is parsed back into a `SceneDraft`.
3. **Reduce** — the `dungeon_master` agent receives all drafts, selects the one matching the player's *actual* choice, applies its consequences to player state (HP, inventory), and prompts the LLM for the next narrative beat plus three new choices.

`ThreadPoolExecutor.map(scene_agent, ...)` drives concurrency host-side; the sandboxes run in parallel on the server. Each branch is a clean `LLM → sandbox → JSON draft` stage, mirrored in both the Python and TypeScript starters.

### Why sandboxes here

LLM-generated dice/outcome scripts are untrusted code — each runs in an isolated sandbox (`allow_internet_access=False`, `timeout_secs=600`), so a malformed or runaway script can't touch the host or sibling branches. To cut per-turn latency when branches need libraries (e.g. `numpy` for richer mechanics), pre-bake deps into a snapshot and boot each `scene_agent` from `Sandbox.create(snapshot_id=...)` instead of `pip install`-ing every turn.

---

## Agentic Autoresearch Loop

Iterative ML script self-improvement: an LLM agent proposes candidate code modifications, parallel sandboxes race them, and a greedy hill-climbing loop accepts the winner if it lowers validation loss.

### Loop structure

1. **Calibration** — run the baseline script in a sandbox to establish starting validation loss
2. **Proposal** — agent generates N candidates with increasing temperatures (e.g. `0.9 + i * 0.1`)
3. **Parallel race** — each candidate runs in its own sandbox with a fixed step budget
4. **Evaluation** — parse `val_loss` from stdout, rank
5. **Hill-climb** — accept the winner only if it beats the current best
6. **Iterate** — repeat with the updated script and the last 8 experiments as memory

### TypeScript: sandbox per candidate

```typescript
async function evaluateCandidate(script: string) {
  const sandbox = await Sandbox.create({
    cpus: 2.0,
    memoryMb: 4096,
    timeoutSecs: 900,
  });
  try {
    await sandbox.writeFile("/workspace/train.py", script);
    const result = await sandbox.run("python", { args: ["/workspace/train.py"] });
    const match = result.stdout.match(/val_loss:\s*([0-9.]+)/);
    return { valLoss: match ? Number(match[1]) : Infinity };
  } finally {
    await sandbox.terminate();
  }
}
```

### Why sandboxes here

- LLM-generated training code is untrusted — running it in your host process risks arbitrary fs/network ops
- Per-candidate isolation means a runaway candidate can't affect siblings
- Fixed `STEPS` budget (treated as immutable in agent guidance) prevents reward hacking via longer training

### Operational modes

- **Smoke** — 3 iterations × 2 candidates × 150 steps (~5 minutes)
- **Full** — 8 iterations × 3 candidates × 300 steps (~20 minutes)

---

## RL Reproducible Environments

Use sandboxes as deterministic, isolated rollout environments for reinforcement learning. Same seed + same action sequence = byte-identical trajectory.

### Pattern

- One fresh sandbox per rollout — isolation is structural, not dependent on cleanup
- Embed the seed *into the harness script*, not on the host (keeps host-side RNG out of the loop)
- For gymnasium envs, seed both the env *and* the action space:

```python
env.reset(seed=seed)
env.action_space.seed(seed)
```

### Parallel rollouts (Python)

```python
import json
from concurrent.futures import ThreadPoolExecutor
from tensorlake.sandbox import Sandbox

def rollout(seed: int):
    sandbox = Sandbox.create()
    try:
        harness = f"""
import gymnasium, json
env = gymnasium.make("CartPole-v1")
obs, _ = env.reset(seed={seed})
env.action_space.seed({seed})
trajectory = []
for _ in range(200):
    action = env.action_space.sample()
    obs, reward, done, trunc, _ = env.step(action)
    trajectory.append((int(action), float(reward)))
    if done or trunc:
        break
print(json.dumps(trajectory))
"""
        result = sandbox.run("python", ["-c", harness])
        return json.loads(result.stdout)
    finally:
        sandbox.terminate()

with ThreadPoolExecutor(max_workers=4) as pool:
    trajectories = list(pool.map(rollout, [42, 43, 44, 45]))
```

### Why fresh-per-rollout

- Cached pip packages, `/tmp` files, and residual process state from a prior episode break reproducibility
- ThreadPoolExecutor manages concurrency; sandboxes manage isolation — separate concerns

---

## RL Training with GSPO

Use sandboxes as a reward oracle for fine-tuning code-generation models with Group Sequence Policy Optimization.

### Two-phase strategy

1. **SFT warmup** — supervised fine-tune on reference solutions so the model emits valid Python. Without this, all completions score 0 and there's no gradient signal.
2. **GSPO fine-tune** — trainer generates G completions per step, dispatches each to a sandbox, receives `tests_passed / total_tests` as reward.

### GSPO vs GRPO

| Aspect | GRPO | GSPO |
|---|---|---|
| Importance sampling | per-token: `clip(π_θ(t) / π_old(t))` | sequence-level: `clip(∏_t π_θ(t) / π_old(t))` |
| Best for | token-level control | long function bodies — trajectory-level treatment avoids noisy single tokens dominating the gradient |

### Sandbox reward function

```python
from tensorlake.sandbox import Sandbox

def reward(completion: str, hidden_tests: str) -> float:
    sandbox = Sandbox.create(allow_internet_access=False)
    try:
        sandbox.write_file("/workspace/solution.py", completion)
        sandbox.write_file("/workspace/tests.py", hidden_tests)
        result = sandbox.run("pytest", ["/workspace/tests.py", "--tb=no", "-q"],
                            working_dir="/workspace")
        return parse_pass_rate(result.stdout)  # tests_passed / total_tests
    finally:
        sandbox.terminate()
```

The model never sees the test files — preventing reward hacking.

### Key hyperparameters

- `importance_sampling_level="sequence"` — enables GSPO
- `temperature=1.4` — forces diversity across G completions; without it, GSPO collapses to zero reward variance
- Hidden pytest suite per task (4 tests typical), 75/25 train/eval split

### Expected scale

A 135M-parameter model with this loop reaches ~25% pass rate on held-out functions after limited training. Pre-training baseline is ~0%.

---

## Data Analysis

Run parallel data analysis and model benchmarking in isolated sandboxes.

### Pattern: Parallel Benchmarking

```python
import asyncio, json
from tensorlake.sandbox import Sandbox

def run_model_benchmark(model_name, sklearn_path):
    """Synchronous benchmark — one sandbox per model."""
    sandbox = Sandbox.create()
    try:
        sandbox.run("pip", ["install", "--user", "--break-system-packages", "numpy", "scikit-learn"])
        module, cls = sklearn_path.rsplit(".", 1)
        code = f"""
import json, time
from {module} import {cls}
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
start = time.time()
model = {cls}()
model.fit(X_train, y_train)
elapsed = time.time() - start
acc = accuracy_score(y_test, model.predict(X_test))
print(json.dumps({{"model": "{model_name}", "accuracy": round(acc, 4), "time": round(elapsed, 4)}}))
"""
        result = sandbox.run("python", ["-c", code])
        return json.loads(result.stdout)
    finally:
        sandbox.terminate()

async def main():
    models = {
        "RandomForest": "sklearn.ensemble.RandomForestClassifier",
        "SVM": "sklearn.svm.SVC",
        "LogisticRegression": "sklearn.linear_model.LogisticRegression",
    }
    results = await asyncio.gather(*[
        asyncio.to_thread(run_model_benchmark, name, path)
        for name, path in models.items()
    ])
    for r in results:
        print(r)

asyncio.run(main())
```

Use snapshots to avoid re-installing dependencies on each run.

### Parallel Batch Execution

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(run_model_benchmark, name, path): name for name, path in models.items()}
    for future in as_completed(futures):
        print(future.result())
```

---

## CI/CD Build Pipelines

Use sandboxes as ephemeral, isolated build containers.

### Pattern: Mini-CI Pipeline

```python
import os
from tensorlake.sandbox import Sandbox

def copy_to_sandbox(sandbox, local_dir, sandbox_dir):
    """Recursively copy a local directory into the sandbox."""
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        dest = f"{sandbox_dir}/{rel}" if rel != "." else sandbox_dir
        sandbox.run("mkdir", ["-p", dest])
        for f in files:
            with open(os.path.join(root, f), "rb") as fh:
                sandbox.write_file(f"{dest}/{f}", fh.read())

sandbox = Sandbox.create()
try:
    # Upload project files
    copy_to_sandbox(sandbox, "./my_project", "/workspace/project")

    # Install dependencies
    sandbox.run("pip", [
        "install", "-r", "requirements.txt",
        "--user", "--break-system-packages"
    ], working_dir="/workspace/project")

    # Run tests
    result = sandbox.run("python", ["-m", "pytest", "tests/"],
        working_dir="/workspace/project",
        env={"PYTHONPATH": "/workspace/project/src"})
    print(f"Exit: {result.exit_code}\nSTDOUT:\n{result.stdout}")

    # Build artifacts
    sandbox.run("python", ["setup.py", "sdist", "bdist_wheel"],
        working_dir="/workspace/project")

    # Download artifacts from the sandbox
    wheel_bytes = sandbox.read_file("/workspace/project/dist/my_project.whl")
finally:
    sandbox.terminate()
```

**Key `sandbox.run()` parameters:**
- `env` — inject environment variables
- `working_dir` — set working directory for the command

## Sandbox as a Dev Environment

Use a **named** sandbox as a portable cloud development workstation: SSH in from any machine, work normally, walk away when you're done. The sandbox idle-suspends and stops charging; resume tomorrow under the same name and your shell history, installed packages, in-progress branches, running `tmux` sessions, and `~/.vscode-server` are exactly where you left them. The sandbox id never changes across suspend/resume, so a single `~/.ssh/config` entry works forever.

### One-time setup — register your SSH key

```bash
tl sbx ssh keys add --name laptop ~/.ssh/id_ed25519.pub
tl sbx ssh keys ls
```

Keys are scoped per user across all projects — do this once per laptop.

### Create the dev sandbox

```bash
# Named sandbox so it can be suspended and resumed
tl sbx create my-dev --cpus 2 --memory 4096 --disk_mb 25600 --timeout 3600

# Print an SSH config block ready to paste into ~/.ssh/config
tl sbx describe my-dev
```

- `--disk_mb` is root FS size in MiB (range 10240–102400; 10–100 GiB). Toolchains, container images, and dataset checkouts fill the disk fastest.
- `--timeout 3600` gives an hour of idle slack before suspend; `--timeout 0` requests the plan maximum (24h on On-Demand). While you're SSH'd in, the idle timer is paused.
- Pass `--image my-image` if you've baked your toolchain into a [sandbox image](sandbox_sdk.md#sandbox-images).

### `~/.ssh/config` entry

`tl sbx describe my-dev` prints exactly this; the equivalent manual entry is:

```sshconfig
Host my-dev
  HostName sandbox.tensorlake.ai
  User <sandbox-id>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

`Host` is just a local alias. `User` **must** be the sandbox id — that's what the gateway routes on. `IdentitiesOnly yes` matters if you have multiple keys in your agent.

```bash
ssh my-dev
# tl-user@tl-sbx:~$
```

### Open it in VS Code (Remote-SSH)

1. Install the **Remote - SSH** extension (`ms-vscode-remote.remote-ssh`).
2. **Remote-SSH: Connect to Host…** → `my-dev`.
3. **File → Open Folder** → `/home/tl-user/workspace`. That path is writable by the default `tl-user` account and persisted across snapshots. `/workspace` is **not** `tl-user`-writable in the default image, and `/tmp/*` is writable but excluded from snapshots.
4. First connect takes ~30s while VS Code installs its server under `~/.vscode-server`. That directory lives under `/home/tl-user`, so it persists across suspend/resume — subsequent connects are fast.

JetBrains Gateway, Cursor, and other Remote-SSH clients work the same way.

### Day-to-day

- **Long jobs vs. SSH disconnect.** When your SSH session ends and no other proxy traffic is in flight, the idle clock starts and the sandbox eventually suspends. Suspend preserves running processes (a `tmux` job resumes when you do), but it does **not** make progress while suspended. For unattended work that needs to keep running: raise `--timeout`, keep a client connected, or use [Sandbox Processes](sandbox_sdk.md) which is designed for fire-and-forget.
- **Explicit suspend stops the meter immediately.** Don't wait for the idle timeout:

  ```bash
  tl sbx suspend my-dev
  ```

- **Resume tomorrow:**

  ```bash
  tl sbx resume my-dev
  ssh my-dev
  ```

The sandbox id never changes across suspend/resume — `~/.ssh/config` and VS Code Remote-SSH bookmarks keep working indefinitely.

## Drive Chrome over CDP

Run real Google Chrome inside a sandbox and drive it from your laptop with any DevTools-Protocol client (Playwright, Puppeteer, `chrome-remote-interface`, raw WebSocket) — no headless container, no screenshot polling, no public port. Built on the [`tensorlake/ubuntu-vnc`](computer_use.md) image plus a [Local Tunnel](sandbox_sdk.md#local-tunnels) carrying CDP traffic to `127.0.0.1`. The CDP path and the [Computer Use](computer_use.md) desktop path compose: keep the agent loop on CDP and attach a human reviewer over VNC.

### Workflow

1. **Launch the sandbox** with the `ubuntu-vnc` image (4 CPU / 4 GiB is a comfortable default for one Chrome session). The desktop password for the managed image is `tensorlake`.

   ```bash
   tl sbx create -i tensorlake/ubuntu-vnc -c 4 -m 4096 chrome-cdp
   ```

2. **Start Chrome with CDP enabled** on the existing VNC display (`:1`) as the desktop user (`tl-user`). Two flags are required:

   - `--remote-debugging-port=9222` — opens the DevTools Protocol endpoint on `127.0.0.1:9222` inside the sandbox.
   - `--remote-allow-origins=*` — required for Chrome ≥ 111, otherwise `ws://127.0.0.1:9222/devtools/...` returns `403 Forbidden`. The HTTP `/json/version` endpoint works without it; the WebSocket handshake does not.
   - `--user-data-dir=/tmp/<something>` — required for Chrome ≥ 136, which refuses to enable `--remote-debugging-port` against the default profile (`DevTools remote debugging requires a non-default data directory`).

   ```python
   from tensorlake.sandbox import Sandbox

   with Sandbox.connect("<sandbox-id>") as sandbox:
       sandbox.start_process(
           "sudo",
           args=[
               "-u", "tl-user",
               "env", "DISPLAY=:1", "XAUTHORITY=/home/tl-user/.Xauthority",
               "google-chrome",
               "--no-first-run",
               "--no-default-browser-check",
               "--remote-debugging-port=9222",
               "--remote-allow-origins=*",
               "--user-data-dir=/tmp/chrome-cdp",
           ],
       )
   ```

   `start_process` returns immediately and the sandbox daemon keeps Chrome alive — no `nohup`, no shell, no log redirection. Inspect captured output later via `sandbox.get_stdout(pid)` / `sandbox.get_stderr(pid)`. (TypeScript: `sandbox.startProcess(...)`, `sandbox.getStdout(pid)` / `sandbox.getStderr(pid)`.)

   Confirm CDP is up: `tl sbx exec <sandbox-id> -- bash -lc 'curl -s http://127.0.0.1:9222/json/version'` should return JSON with `Browser`, `Protocol-Version`, and `webSocketDebuggerUrl`.

3. **Open a tunnel** so `127.0.0.1:9222` on your laptop forwards to the sandbox (every byte rides an authenticated WebSocket — port `9222` never has to be in `exposed_ports`):

   ```bash
   tl sbx tunnel <sandbox-id> 9222
   ```

   TypeScript SDK form: `await sandbox.createTunnel(9222, { localPort: 9222 })`. Verify locally: `curl http://127.0.0.1:9222/json/version`.

4. **Drive the browser.** Open a fresh tab via CDP's HTTP control surface (`curl -X PUT "http://127.0.0.1:9222/json/new?https://news.ycombinator.com"`), or use a higher-level client:

   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
       page = browser.contexts[0].new_page()
       page.goto("https://news.ycombinator.com")
       print(page.locator(".titleline > a").all_text_contents()[:5])
   ```

   For raw protocol control (`Runtime.evaluate`, `Page.navigate`, `DOM.getDocument`), connect to the per-tab `webSocketDebuggerUrl` directly with `websocket-client` and exchange JSON messages. This is the path to take when wiring CDP into an LLM agent: expose `open_url`, `evaluate`, and `list_targets` as tools that wrap the per-tab WebSocket.

### `chrome-devtools` MCP for coding agents

Claude Code and OpenAI Codex can drive the same sandboxed Chrome through the official [`chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp). The MCP attaches via `--browser-url`; matching the URL to the tunnel's local port is the only required configuration.

```bash
# Claude Code (user scope by default; pass --scope project to write to .mcp.json)
claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest \
  --browser-url http://127.0.0.1:9222

# Codex (writes ~/.codex/config.toml; user-global only — no project scope)
codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest \
  --browser-url http://127.0.0.1:9222
```

If port `9222` is taken on your laptop, pick any free port and keep both sides aligned:

```bash
tl sbx tunnel <sandbox-id> 9222 --listen-port 12222
claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest \
  --browser-url http://127.0.0.1:12222
```

Restart the agent so it picks up the new MCP (Claude Code re-reads on launch; Codex reads `config.toml` at startup, no hot-reload), then ask it to do something in the browser. The agent routes through `chrome-devtools` → `127.0.0.1:9222` → tunnel → sandbox Chrome on display `:1`.

> **Verify the path before pointing an agent at it.** `curl http://127.0.0.1:9222/json/version` should return Chrome's JSON. The tunnel CLI keeps the local port bound even when the sandbox upstream goes away (terminated, suspended without auto-resume), so a hung `curl` usually means the sandbox is gone, not that the MCP is misconfigured.

### Pitfalls

- **`--remote-allow-origins=*` is required** for Chrome ≥ 111 — without it the HTTP CDP endpoints work but every WebSocket handshake fails with `403`.
- **`--user-data-dir` is required** for Chrome ≥ 136 to enable `--remote-debugging-port` at all.
- **Bind address.** `--remote-debugging-port` only listens on `127.0.0.1` by default — exactly what you want, since the tunnel forwards to `127.0.0.1` inside the sandbox and the debugger stays unreachable from anywhere else.
- **Headless mode.** If you do not need the VNC view, launch with `--headless=new` instead of attaching to display `:1`. Tunneling and CDP usage are identical.
- **`Failed to move to new namespace`.** Chrome's setuid sandbox sometimes fails inside container/VM combinations — add `--no-sandbox` to the launch flags.
- **Multiple agents.** Each tab has its own `webSocketDebuggerUrl` — two clients can drive different tabs of the same Chrome at once (agent loop + human reviewer).

Tear down: `tl sbx exec <sandbox-id> -- bash -lc 'sudo -u tl-user pkill -f google-chrome || true'`, then `tl sbx suspend <sandbox-id>` (named only) to keep the user-data-dir warm, or `tl sbx terminate <sandbox-id>` to release resources.

## Harbor (evals + RL rollouts)

[Harbor](https://github.com/harbor-framework/harbor) is a framework from the creators of [Terminal-Bench](https://www.tbench.ai/) for evaluating and optimizing agents and language models. Evaluate arbitrary agents (Claude Code, OpenHands, Codex CLI, others) against curated datasets like Terminal-Bench, SWE-Bench, and Aider Polyglot, build your own benchmarks, run thousands of trials in parallel, and generate rollouts for RL optimization. Harbor abstracts the execution backend behind an `--env` flag; **Tensorlake plugs in as one of those providers** — same Harbor commands, same tasks/agents/evaluators.

New accounts include free credits — per the docs, enough to run a full Terminal-Bench sweep before you pay for anything.

### Quick start

```bash
# install Harbor with the Tensorlake provider (installs the TensorLakeEnvironment provider)
uv pip install "harbor[tensorlake]"
# or: pip install "harbor[tensorlake]"

export TENSORLAKE_API_KEY="tl_..."
export ANTHROPIC_API_KEY="sk-ant-..."   # or another agent provider

harbor run --env tensorlake \
  --include-task-name terminal-bench/pytorch-model-cli \
  --dataset terminal-bench/terminal-bench-2-1 \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --ae ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
```

Drop `--include-task-name` to run the full **Terminal-Bench 2.1** suite. `--ae KEY=VALUE` forwards an env var from your shell into the sandbox where the agent runs — repeat for any other secrets.

> Dataset and task identifiers are now slash-namespaced (`terminal-bench/terminal-bench-2-1`, `terminal-bench/pytorch-model-cli`), not the older `terminal-bench@2.0` form.

### Why Tensorlake for Harbor

- **Per-trial sandboxes** — each task starts on a clean machine and is destroyed at the end. No shared kernel state between trials, which matters for eval reproducibility and RL reward integrity.
- **Full task-environment support** — Tensorlake **imports a task's real Docker image** and converts it into a sandbox image that boots directly, so every trial runs the exact environment the benchmark defines rather than one approximated by replaying a Dockerfile. That closes the environment gap that otherwise quietly skews results.
- **Pre-warmed snapshots** — environments with heavy `apt`/`pip` installs (PyTorch, CUDA, full Linux desktops) can be built once, snapshotted, and restored **under a second** per trial or rollout.
- **Independent verification** — Harbor's test script runs inside the sandbox and writes `1.0`/`0.0` to `reward.txt`. The agent never sees or touches the verifier, so "the agent said it worked" is never confused with "the tests pass."
- **Parallel scale** — Tensorlake schedules thousands of sandboxes concurrently.

### Anatomy of a Harbor task

```
gcode-to-text/
├── environment/
│   ├── Dockerfile              # base image and setup steps
│   └── text.gcode.gz
├── instruction.md              # prompt the agent receives
├── solution/
│   └── solve.sh                # oracle reference for validating the environment itself
├── task.toml                   # provisioning config (see below)
└── tests/
    ├── test_outputs.py
    └── test.sh                 # runs after the agent finishes; produces reward.txt
```

### Tune sandbox resources

`task.toml` controls the sandbox Harbor provisions on Tensorlake:

```toml task.toml
[environment]
cpus = 2
memory_mb = 4096
storage_mb = 20480
allow_internet = true
```

| Field | Default | Forwarded to Tensorlake |
|---|---|---|
| `cpus` | `1` | `cpus` |
| `memory_mb` | `2048` | `memory_mb` |
| `storage_mb` | `10240` | `ephemeral_disk_mb` |
| `allow_internet` | `true` | `allow_internet_access` |

> **Memory ratio constraint.** Tensorlake requires `memory_mb` to be between 1024 and 8192 MB **per CPU core**.

Rules of thumb: bump `cpus` and `memory_mb` for heavy Dockerfiles (PyTorch, CUDA, full desktops, large datasets) and raise `storage_mb` past image size + working set — underprovisioning shows up as build timeouts or mid-trial OOMs. Set `allow_internet = false` to stop the agent from web-searching for answers; if the verifier needs network access, bake it into the Dockerfile (per-host allowlists are coming).

### Image build & caching

Each trial boots from an image, built or imported **once** and then reused — you only pay on the first trial.

| Source | How to set it | When to use |
|---|---|---|
| **Prebuilt image** | `docker_image` in `task.toml` | Fastest start: boot directly from an image with the environment baked in. Terminal-Bench ships these. |
| **Dockerfile** | `environment/Dockerfile` | No prebuilt image declared. Built once, cached, reused across trials. |

If a task sets both, the prebuilt image wins.

**Prebuilt images.** Harbor looks the image up in Tensorlake by name and boots from it; if it isn't registered yet it imports it once. **The registered name is derived from the reference string**, so the *first* import of a given reference is what every later run boots.

```toml task.toml
[environment]
docker_image = "myorg/my-task-env:2025-06"
```

> **Always publish with an immutable tag, never `latest`.** Because the registered name comes from the reference string and not the image contents, `latest` is captured at first import and then frozen — push new content to `latest` and Harbor keeps booting the old image, never re-pulling. Use an immutable tag or digest so a new build means a new reference. To refresh an already-registered image, point `docker_image` at a new immutable tag/digest, or delete the registered Tensorlake image so the next run re-imports it. **`--force-build` does not re-import** — it builds from the Dockerfile instead.

**Terminal-Bench 2.1 images are already published** publicly, so anyone with Tensorlake access boots straight from them — no build, no import.

**Set org and project context.** Looking an image up by name requires it. Without it Harbor can't find the published image and falls back to importing it fresh (you'll see `Looking up a sandbox image by name requires organization and project context` in the logs):

```bash
export TENSORLAKE_ORGANIZATION_ID="..."
export TENSORLAKE_PROJECT_ID="..."
```

Harbor also reads these from `~/.tensorlake/config.toml` (`organization` and `project`) if present.

**Dockerfile builds** are cached on the Dockerfile **and every file in the build context**, so editing a `requirements.txt` pin or any `COPY`'d file triggers a rebuild automatically. If a build fails, Harbor falls back to replaying the Dockerfile's `RUN`/`COPY` steps on each trial so a trial is never blocked (just slower). That fallback is also an explicit escape hatch while iterating: `--ek use_oci_image_build=false`. Force a fresh rebuild for one run with `--force-build` (doesn't disturb the cache used by later normal runs).

**Dockerfile requirements** — the image builder is stricter than a local `docker build`:

- **`COPY` does not auto-create parent directories** — `COPY x /a/b/c` fails if `/a/b` doesn't exist. Add `RUN mkdir -p /a/b` first.
- **Don't pin exact apt versions** (`apt-get install curl=8.5.0-2ubuntu10.6`) — drop the pin or pick a version that exists in the target distro.
- **Use a `FROM` image that ships the Python you need** (e.g. `python:3.10-bookworm`) rather than relying on a non-native version being fetched at build time.

**Sharing images publicly.** Images Harbor builds or imports are **private to your organization** by default. `--ek is_public=true` registers a freshly built or imported image as public. It applies to both Dockerfile builds and prebuilt imports, but automatic boot-from-public by another org is wired through the **prebuilt `docker_image`** path — so prefer a `docker_image` reference if your goal is publishing an environment others boot directly. **Publishing public images is gated to an allow list**; if your account isn't on it the flag is silently ignored and the image stays private. `is_public` only takes effect when the image is **newly registered** — to turn an already-private image public, delete it first (or change the build context so it gets a new name), then rerun.

**Ad-hoc native dependencies.** For a couple of extra apt packages without editing the Dockerfile or maintaining a snapshot:

```bash
harbor run --env tensorlake \
  --ek 'preinstall_packages=["build-essential","rustc","cargo"]' \
  --dataset terminal-bench/terminal-bench-2-1 --agent claude-code --model anthropic/claude-sonnet-4-6
```

These install at the start of **each** trial — prefer snapshots when the package set is large or reused across many runs.

### Debugging

Attach to a live trial environment to inspect state and rerun tests by hand:

```bash
harbor env attach <session_id>
```

Each trial produces structured artifacts (`agent/`, `verifier/`, `result.json`, `trial.log`) so you can trace agent actions, verifier checks, and pass/fail reasoning.
