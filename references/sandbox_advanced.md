<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/skills-in-sandboxes.md
  - https://docs.tensorlake.ai/sandboxes/ai-code-execution.md
  - https://docs.tensorlake.ai/sandboxes/data-analysis.md
  - https://docs.tensorlake.ai/sandboxes/cicd-build.md
  - https://docs.tensorlake.ai/sandboxes/agentic-autoresearch.md
  - https://docs.tensorlake.ai/sandboxes/agentic-rl-reproducible-env.md
  - https://docs.tensorlake.ai/sandboxes/agentic-swarm-intelligence.md
  - https://docs.tensorlake.ai/sandboxes/gspo-agentic-rl.md
SDK version: tensorlake 0.4.49
Last verified: 2026-04-22
-->

# TensorLake Sandbox Advanced Patterns

## Table of Contents

- [Skills in Sandboxes](#skills-in-sandboxes)
- [AI Code Execution](#ai-code-execution)
- [Data Analysis](#data-analysis)
- [CI/CD Build Pipelines](#cicd-build-pipelines)

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
tl sbx new --image claude-code-skills
```

### Runtime Installation (SDK)

```python
from tensorlake.sandbox import SandboxClient

client = SandboxClient()

with client.create_and_connect() as sandbox:
    sandbox.run("bash", ["-c", "apt-get update && apt-get install -y nodejs npm"])
    sandbox.run("bash", ["-c", "npm install -g skills"])
    sandbox.run("bash", ["-c", "skills add tensorlakeai/tensorlake-skills --all -y --copy"])

    result = sandbox.run("find", ["/", "-name", "SKILL.md", "-type", "f", "-not", "-path", "*/node_modules/*"])
    print(result.stdout)
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
sandbox = client.create_and_connect(
    cpus=1.0,
    memory_mb=1024,
    timeout_secs=600,
    allow_internet_access=False  # important for untrusted code
)

result = sandbox.run("python", ["-c", code])
# result.stdout, result.stderr, result.exit_code
```

**TypeScript:**

```typescript
import { SandboxClient } from "tensorlake";

const client = SandboxClient.forCloud({
  apiKey: process.env.TENSORLAKE_API_KEY,
});

const sandbox = await client.createAndConnect({
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
  client.close();
}
```

### Snapshots for Pre-installed Dependencies

```python
snapshot = client.snapshot_and_wait(sandbox.sandbox_id)
sandbox = client.create_and_connect(snapshot_id=snapshot.snapshot_id)
```

### Integration Patterns

**Claude (Anthropic):** Define a `run_code` tool in the tools schema. Detect `tool_use` blocks in responses, execute via `sandbox.run()`, return results as `tool_result`.

**OpenAI Function Calling:** Structure sandbox as a function definition. Parse `tool_calls`, execute, append results to message history.

**OpenAI Agents SDK:** Wrap sandbox execution with `@function_tool` decorator.

### Best Practices

- **Reuse sandboxes** — creating new ones per tool call adds cold-start latency and loses filesystem state
- **Set `allow_internet_access=False`** for untrusted code. If you need `pip install` on demand, pre-bake deps into a custom image or snapshot instead of flipping internet access on for untrusted code
- **Pre-install deps via snapshots** or let agents `pip install` on demand (only in trusted setups)
- **Tear down** with `sandbox.close()` or `sandbox.terminate()` when the session ends

### Anti-patterns

Do not work around the fresh-process model by building a persistent interpreter:

- **Don't use `start_process` + `write_stdin`** to keep a long-running `python` kernel alive and pipe code into it. `sandbox.run("python", ["-c", code])` is the supported shape. A long-running stdin-fed kernel is not a documented pattern and gives up the clean per-call stdout/stderr/exit_code contract.
- **Don't tell the downstream LLM that variables persist across turns** in its system prompt. They don't. Tell it instead: "You have a persistent workspace directory and installed packages; module imports and variables reset between calls — write intermediate state to `/workspace/` if you need it across turns."
- **Don't flip `allow_internet_access=True` to enable pip for untrusted code.** Pre-install dependencies into a custom `Image` or a snapshot, then boot the sandbox from that snapshot with `snapshot_id=`.
- **Don't fabricate methods or fields.** There is no `sandbox.exec()`, `sandbox.python()`, `sandbox.eval()`, `sandbox.repl()`, or `persistent=True` / `repl_mode=True` / `session=True` kwarg. The return object has `stdout`, `stderr`, `exit_code` — not `.output`, `.result`, or `.logs`.

---

## Data Analysis

Run parallel data analysis and model benchmarking in isolated sandboxes.

### Pattern: Parallel Benchmarking

```python
import asyncio, json
from tensorlake.sandbox import SandboxClient

def run_model_benchmark(model_name, sklearn_path):
    """Synchronous benchmark — one sandbox per model."""
    client = SandboxClient()
    sandbox = client.create_and_connect()
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
        sandbox.close()

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
from tensorlake.sandbox import SandboxClient

def copy_to_sandbox(sandbox, local_dir, sandbox_dir):
    """Recursively copy a local directory into the sandbox."""
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        dest = f"{sandbox_dir}/{rel}" if rel != "." else sandbox_dir
        sandbox.run("mkdir", ["-p", dest])
        for f in files:
            with open(os.path.join(root, f), "rb") as fh:
                sandbox.write_file(f"{dest}/{f}", fh.read())

client = SandboxClient()
sandbox = client.create_and_connect()
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
    sandbox.close()
```

**Key `sandbox.run()` parameters:**
- `env` — inject environment variables
- `working_dir` — set working directory for the command
