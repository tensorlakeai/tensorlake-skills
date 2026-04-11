# Tensorlake Skill

Build production agent workflows with [Tensorlake's](https://tensorlake.ai).

This skill helps coding agents use Tensorlake to build real agent systems with sandboxed execution and orchestration. It covers both the **Python** (`pip install tensorlake`) and **TypeScript** (`npm install tensorlake`) SDKs. It is designed for modern agent use cases like multi-agent applications, isolated code execution, long-running workflows, and tool-using agents that need a real workspace.

Instead of treating Tensorlake as just another API, this skill teaches agents how to use Tensorlake as infrastructure: run tasks in isolated environments with the Sandbox SDK, coordinate durable workflows with the sandbox-native Orchestrate SDK, and compose reliable agent systems for production use.

Use it when you want your coding agent to build:

- multi-agent applications
- sandboxed coding or execution workflows
- agent teams with separate workspaces
- long-running or stateful agent systems
- production-ready orchestration patterns

## What This Skill Does

It guides agents to:

- use the **Sandbox SDK** for agent execution environments and isolated tool calls
- use the **Orchestrate SDK** for sandbox-native durable workflow orchestration and multi-agent coordination
- combine both SDKs to build production-style agent systems
- choose Tensorlake patterns that are better than a single-agent or stateless approach

The skill is especially useful for tasks like:

- running code, scripts, or services inside isolated sandboxes
- giving each agent its own workspace, files, and execution environment
- building agentic applications with an orchestrator and specialist sub-agents
- coordinating parallel agents and collecting their outputs
- building demos and prototypes that show why agent infrastructure matters
Works with any LLM provider (OpenAI, Anthropic) and any agent framework (LangChain, etc.). Tensorlake is the infrastructure layer — bring your own models and frameworks.

The skill triggers automatically when you ask the agent to:

- Run LLM-generated code in a secure sandbox
- Build agentic workflows or multi-agent pipelines
- Orchestrate complex multi-step AI applications
- Integrate Tensorlake with any LLM, framework, database, or API
- Ask questions about Tensorlake APIs or documentation

## Supported Agents


| Agent                                                         | File        | How to Install                               |
| ------------------------------------------------------------- | ----------- | -------------------------------------------- |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `SKILL.md`  | See [Claude Code installation](#claude-code) |
| [Google ADK](https://google.github.io/adk-docs/skills/)       | `SKILL.md`  | See [Google ADK installation](#google-adk)   |
| [OpenAI Codex](https://openai.com/index/codex/)               | `AGENTS.md` | See [Codex installation](#openai-codex)      |


## Installation

### Quick Install

#### Any Agent

```bash
npx skills add tensorlakeai/tensorlake-skills
```

Works with Claude Code, Cursor, Cline, GitHub Copilot, Windsurf, and more via [skills.sh](https://skills.sh).

## Setup

Tensorlake requires a `TENSORLAKE_API_KEY` configured in the local environment. Get one at [cloud.tensorlake.ai](https://cloud.tensorlake.ai), then either run `tensorlake login` (Python) / `npx tl login` (TypeScript) or configure the variable through your shell profile, `.env` file, or secret manager. Do not paste API keys into chat, commit them to source control, or print them in terminal output.

## Repository Structure

```
tensorlake-skills/
├── SKILL.md                  # Skill definition (Claude Code, Google ADK)
├── AGENTS.md                 # Skill definition (OpenAI Codex)
├── CHANGELOG.md              # Changes tracked per SDK version
├── .claude-plugin/
│   ├── plugin.json               # Claude Code plugin metadata
│   └── marketplace.json          # Marketplace listing
├── scripts/
│   └── bump-version.sh          # Version bump automation
├── .github/
│   ├── workflows/
│   │   └── sync-check.yml        # Weekly drift detection (CI)
│   └── scripts/
│       ├── fetch_docs.py         # Fetch live doc pages
│       ├── check_drift.py        # Compare fetched vs bundled
│       └── sources.yaml          # Map: reference file → source URLs
└── references/
    ├── applications_sdk.md       # Orchestrate API reference
    ├── sandbox_sdk.md            # Sandbox API reference
    ├── sandbox_persistence.md    # Sandbox state: snapshots, suspend/resume, state machine
    ├── documentai_sdk.md         # DocumentAI API reference
    ├── integrations.md           # Integration patterns (LangChain, OpenAI, ChromaDB, Qdrant, etc.)
    ├── platform.md               # Webhooks, auth, access control, EU data residency
    ├── sandbox_advanced.md       # Skills-in-sandboxes, AI code execution, data analysis, CI/CD
    └── troubleshooting.md        # Common issues, production integration, benchmarks
```

## Versioning

This skill uses [SemVer](https://semver.org/) for its own version, independent of the TensorLake SDK version it documents.

- **Major** — breaking changes (renamed/removed reference files, restructured skill)
- **Minor** — new reference files, significant content additions, new SDK version coverage
- **Patch** — fixes, small content updates, drift corrections

The TensorLake SDK version being documented is tracked separately in `sources.yaml` and in the source headers at the top of each reference file.

### Bumping the Version

Use `scripts/bump-version.sh` to update the version across all files:

```bash
./scripts/bump-version.sh patch                # 2.0.0 -> 2.0.1
./scripts/bump-version.sh minor                # 2.0.0 -> 2.1.0
./scripts/bump-version.sh major                # 2.0.0 -> 3.0.0
./scripts/bump-version.sh minor --sdk 0.5.0    # bump + update SDK version in changelog
```

The script:
1. Reads the current version from `SKILL.md` frontmatter
2. Bumps major, minor, or patch
3. Updates `SKILL.md` and `AGENTS.md`
4. Stamps the `[Unreleased]` section in `CHANGELOG.md` with the new version and today's date
5. Prints the git commands to commit and tag

### Release Workflow

```bash
# 1. Make your changes to reference files, SKILL.md, etc.

# 2. Add an [Unreleased] section to CHANGELOG.md with your changes

# 3. Run the bump script
./scripts/bump-version.sh minor

# 4. Commit, tag, and push
git add -A
git commit -m "release: v2.1.0"
git tag v2.1.0
git push origin HEAD && git push origin v2.1.0
```

## Maintaining References

### Source Tracking

Each reference file has a source header that tracks which doc pages it was built from:

```html
<!--
Source:
  - https://docs.tensorlake.ai/sandboxes/lifecycle.md
  - https://docs.tensorlake.ai/sandboxes/commands.md
SDK version: tensorlake 0.4.42
Last verified: 2026-04-08
-->
```

The full mapping is in `.github/scripts/sources.yaml`.

### Drift Detection

A weekly GitHub Action (`sync-check.yml`) fetches the live TensorLake docs and compares them against the bundled reference files. If new APIs, removed endpoints, or changed signatures are detected, it opens a GitHub Issue with a summary of what drifted.

### Maintenance Cadence

| Frequency | Action |
|-----------|--------|
| Weekly (automated) | CI drift-check runs, opens issue if divergence detected |
| Per SDK release | Manual update of reference files + bump version |
| Monthly | Review gap coverage — are new doc pages appearing that need a new reference file? |

## Documentation

- [Tensorlake Docs](https://docs.tensorlake.ai)
- [LLM-friendly docs](https://docs.tensorlake.ai/llms.txt)
- [API Reference](https://docs.tensorlake.ai/api-reference/v2/introduction)

## License

MIT