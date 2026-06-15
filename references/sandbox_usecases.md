<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/skills-in-sandboxes.md
  - https://docs.tensorlake.ai/sandboxes/tool-calls.md
  - https://docs.tensorlake.ai/sandboxes/claude-managed-agents.md
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
SDK version: tensorlake 0.5.44
Last verified: 2026-06-16
-->

# TensorLake Sandbox Use Cases

## Table of Contents

- [Skills in Sandboxes](#skills-in-sandboxes)
- [AI Code Execution](#ai-code-execution)
- [Claude Managed Agents](#claude-managed-agents)
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
    Image(name="with-skills", base_image="ubuntu-systemd")
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
  baseImage: "ubuntu-systemd",
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
    Image(name="claude-code-skills", base_image="ubuntu-systemd")
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
  baseImage: "ubuntu-systemd",
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
- **Snapshots & fork-from-snapshot.** `sandbox.checkpoint()` then `Sandbox.create(snapshot_id=...)` × N forks N children from one known-good state — the basis for best-of-N tool execution and [parallel sub-agents](sandbox_sdk.md#snapshots).
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

[Harbor](https://github.com/harbor-framework/harbor) is a framework from the creators of [Terminal-Bench](https://www.tbench.ai/) for evaluating and optimizing agents and language models against curated datasets (Terminal-Bench, SWE-Bench, Aider Polyglot) or your own benchmarks, plus generating rollouts for RL optimization. Harbor abstracts the execution backend behind an `--env` flag; **Tensorlake plugs in as one of those providers** — same Harbor commands, same tasks/agents/evaluators, running on Tensorlake sandboxes.

### Quick start

```bash
# install Harbor with the Tensorlake provider
uv pip install "harbor[tensorlake]"
# or: pip install "harbor[tensorlake]"

export TENSORLAKE_API_KEY="tl_..."
export ANTHROPIC_API_KEY="sk-ant-..."   # or another agent provider

# Run a single Terminal-Bench 2.0 task on Tensorlake with Claude Code as the agent
harbor run --env tensorlake \
  --include-task-name pytorch-model-cli \
  --dataset terminal-bench@2.0 \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --ae ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
```

Drop `--include-task-name` to run the full Terminal-Bench 2.0 suite. `--ae KEY=VALUE` forwards an env var from your shell into the sandbox where the agent runs — repeat the flag for any other secrets the agent needs.

### Why Tensorlake for Harbor

- **Per-trial sandboxes** — each task starts on a clean machine and is destroyed at the end. No shared kernel state between trials, which matters for both eval reproducibility and RL reward integrity.
- **Pre-warmed snapshots** — environments with heavy `apt`/`pip` installs (PyTorch, CUDA, full Linux desktops) can be built once, snapshotted, and restored under a second per trial.
- **Independent verification** — Harbor's test script runs inside the sandbox and writes `1.0`/`0.0` to `reward.txt`. The agent never sees or touches the verifier, so "the agent said it worked" is never confused with "the tests pass."
- **Parallel scale** — Tensorlake schedules thousands of sandboxes concurrently, exactly what RL rollout generation and full benchmark sweeps need.

### Anatomy of a Harbor task

```
gcode-to-text/
├── environment/
│   ├── Dockerfile              # base image and setup steps
│   └── text.gcode.gz
├── instruction.md              # prompt the agent receives
├── solution/
│   └── solve.sh                # oracle reference for environment validation
├── task.toml                   # provisioning config (see below)
└── tests/
    ├── test_outputs.py
    └── test.sh                 # runs after the agent finishes; writes reward.txt
```

### Tune sandbox resources

`task.toml` controls the sandbox Harbor provisions on Tensorlake. Set resources in the `[environment]` block:

```toml
[environment]
cpus = 2
memory_mb = 4096
storage_mb = 20480
allow_internet = true
```

| Field            | Default | Forwarded to Tensorlake   |
|------------------|---------|---------------------------|
| `cpus`           | `1`     | `cpus`                    |
| `memory_mb`      | `2048`  | `memory_mb`               |
| `storage_mb`     | `10240` | `ephemeral_disk_mb`       |
| `allow_internet` | `true`  | `allow_internet_access`   |

> **Memory ratio constraint.** Tensorlake requires `memory_mb` to be between 1024 and 8192 MB **per CPU core**.

Rules of thumb: bump `cpus` and `memory_mb` for heavy Dockerfiles (PyTorch, CUDA, full desktops, large datasets) and raise `storage_mb` past image size + working set — underprovisioning shows up as build timeouts or mid-trial OOMs. Set `allow_internet = false` to stop the agent from web-searching for answers; if the verifier needs network access, bake it into the Dockerfile (per-host allowlists are coming).

### Debugging

Attach to a live trial environment to inspect state and rerun tests by hand:

```bash
harbor env attach <session_id>
```

Each trial produces structured artifacts (`agent/`, `verifier/`, `result.json`, `trial.log`) so you can trace agent actions, verifier checks, and pass/fail reasoning.
