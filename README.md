# Tensorlake Skill

**Up-to-date Tensorlake knowledge for AI coding agents.** A lightweight skill that teaches Claude Code, OpenAI Codex, Google ADK, and other coding agents how to write correct Tensorlake code — by routing them to live documentation at [docs.tensorlake.ai](https://docs.tensorlake.ai)

## Why This Exists

AI coding agents hallucinate Tensorlake APIs. Their training data don't have the knowledge, so they invent function signatures, miss new features, and reference removed endpoints. This skill fixes that: when an agent detects a Tensorlake-related task, it fetches the live docs and uses them as the source of truth.

It covers the **Python SDK** (`pip install tensorlake`), **TypeScript SDK** (`npm install tensorlake`), and **CLI** (`curl -fsSL https://tensorlake.ai/install | sh`).

## What is a "skill"?

A skill is a small markdown instruction file that teaches an AI coding agent how to use a specific tool or library — similar in spirit to an MCP server, but lighter weight and model-agnostic. The agent reads the skill on activation, follows its instructions (e.g., "fetch live docs before writing code"), and applies the result to your task. No server to run, no extra runtime — just a file the agent reads.

## Example

Without the skill:

> **User:** Build me a Tensorlake sandbox that runs untrusted Python and exposes port 8000.
> **Agent:** *(writes code referencing `Sandbox.new()` — an API that doesn't exist in current SDK)*

With the skill:

> **User:** Build me a Tensorlake sandbox that runs untrusted Python and exposes port 8000.
> **Agent:** *(skill triggers → fetches `https://docs.tensorlake.ai/llms.txt` → loads `sandboxes/lifecycle.md` → writes correct code using current `tensorlake.Sandbox.create()` API)*



## What This Skill Does

When it triggers, the skill instructs the agent to:

1. Verify the SDK is installed and `TENSORLAKE_API_KEY` is configured.
2. `WebFetch https://docs.tensorlake.ai/llms.txt` to get the current doc index.
3. From that index, fetch the `.md` page(s) relevant to the task and use them as the source of truth.
4. Only on fetch failure, fall back to [`references/feature_lookup.md`](references/feature_lookup.md), which routes features and keywords to a bundled snapshot.

It also enforces a few guardrails: verify every symbol against the live docs or installed package before suggesting code, prefer live docs over snapshots when they disagree, and never request, embed, or print API keys.

## When It Triggers

The skill activates when the user mentions Tensorlake or sandboxes, or asks the agent to do anything that maps to the Tensorlake product surface — for example:

- Run LLM-generated or untrusted code in an isolated sandbox
- Persist a sandbox across sessions via suspend/resume, or fork from a snapshot
- Build a custom sandbox image, expose a port, or configure egress allowlists
- Drive PTY/interactive shells or computer-use / desktop automation
- Build durable workflows or multi-agent orchestration with the Applications SDK
- Ask questions about Tensorlake APIs or documentation

It works alongside any LLM provider (OpenAI, Anthropic) and any agent framework (Claude Agents SDK, OpenAI Agents SDK, LangChain, etc.) — Tensorlake is the infrastructure layer.

## Supported Agents


| Agent                                                         | File        | How to Install                |
| ------------------------------------------------------------- | ----------- | ----------------------------- |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `SKILL.md`  | See [Quick Install](#quick-install) |
| [Google ADK](https://google.github.io/adk-docs/skills/)       | `SKILL.md`  | See [Quick Install](#quick-install) |
| [OpenAI Codex](https://openai.com/index/codex/)               | `AGENTS.md` | See [Quick Install](#quick-install) |


## Installation

### Quick Install

#### Any Agent

```bash
npx skills add tensorlakeai/tensorlake-skills
```

Works with Claude Code, Cursor, Cline, GitHub Copilot, Windsurf, and more via [skills.sh](https://skills.sh).

## Setup

Tensorlake requires a `TENSORLAKE_API_KEY` configured in the local environment. Get one at [cloud.tensorlake.ai](https://cloud.tensorlake.ai), then either run `tl login` (or `tensorlake login`) / `npx tl login` (TypeScript) or configure the variable through your shell profile, `.env` file, or secret manager. Do not paste API keys into chat, commit them to source control, or print them in terminal output.

## Repository Structure

```
tensorlake-skills/
├── SKILL.md                  # Skill definition (Claude Code, Google ADK)
├── AGENTS.md                 # Skill definition (OpenAI Codex)
├── CLAUDE.md                 # Repo governance (sync rules, version bump policy)
├── CHANGELOG.md              # Changes tracked per SDK version
├── .claude-plugin/
│   ├── plugin.json               # Claude Code plugin metadata
│   └── marketplace.json          # Marketplace listing
├── scripts/
│   └── bump-version.sh          # Version bump automation
├── .github/
│   ├── workflows/
│   │   ├── sync-check.yml        # Weekly drift detection (CI)
│   │   └── evals.yml             # PR eval CI (skill-trigger + judge-graded)
│   └── scripts/
│       ├── fetch_docs.py         # Fetch live doc pages
│       ├── check_drift.py        # Compare fetched vs bundled
│       └── sources.yaml          # Map: reference file → source URLs
├── evals/
│   ├── evals.json               # Eval suite: prompts, expected references, judge criteria
│   ├── run.py                   # Run evals (claude -p with stream-json + trigger detection)
│   ├── grade.py                 # Judge-LLM grading (skipped when skill didn't trigger)
│   ├── grade_static.py          # Static / non-judge grading checks
│   ├── filter.py                # Map changed references/** files → impacted eval IDs
│   └── ci_summary.py            # Render PR summary table (trigger rate + pass/fail)
└── references/
    ├── feature_lookup.md         # Curated index — routes features/keywords to the snapshot below
    ├── applications_sdk.md       # Orchestration API reference
    ├── sandbox_sdk.md            # Sandbox API reference
    ├── sandbox_persistence.md    # Sandbox state: snapshots, suspend/resume, state machine
    ├── computer_use.md           # Desktop automation: XFCE + Firefox, screenshots, mouse/keyboard, noVNC
    ├── integrations.md           # Integration patterns (LangChain, OpenAI, ChromaDB, Qdrant, etc.)
    ├── platform.md               # Webhooks, auth, access control, EU data residency
    ├── sandbox_usecases.md       # Skills-in-sandboxes, AI code execution, data analysis, CI/CD
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
SDK version: tensorlake 0.5.5
Last verified: 2026-04-30
-->
```

The full mapping is in `.github/scripts/sources.yaml`.

### Drift Detection

A weekly GitHub Action (`sync-check.yml`) fetches the live TensorLake docs and compares them against the bundled reference files. If new APIs, removed endpoints, or changed signatures are detected, it opens a GitHub Issue with a summary of what drifted.

### Eval Suite

The `evals/` directory contains a test harness that runs the skill end-to-end on representative prompts and grades the responses. CI (`.github/workflows/evals.yml`) runs it automatically on PRs that touch `references/**.md`; version bumps, `SKILL.md` / `AGENTS.md` edits, and `evals/**` script changes don't auto-trigger (use `workflow_dispatch` to run on-demand, optionally with a comma-separated list of eval IDs).

Each run captures two signals:

- **Skill-trigger rate** — did the skill actually fire? Surfaced separately so a "skill didn't fire" failure doesn't masquerade as a "skill fired but answered wrong" failure. Detected from `claude -p`'s `--output-format stream-json` output.
- **Judge-graded pass/fail** — an LLM judge evaluates each response against per-eval expected references and criteria. If the skill didn't trigger, judging is skipped and all expectations record `skill not triggered; grading skipped`.

`evals/filter.py` maps changed reference files to impacted eval IDs (so PRs only run the evals their changes can affect). PR runs render a summary table to the GitHub Step Summary via `evals/ci_summary.py` and upload the full eval workspace as an artifact. Evals are report-only — failures show in the table but never block the PR.

### Maintenance Cadence

| Frequency | Action |
|-----------|--------|
| Weekly (automated) | CI drift-check runs, opens issue if divergence detected |
| Per SDK release | Manual update of reference files + bump version |
| Monthly | Review gap coverage — are new doc pages appearing that need a new reference file? |

## FAQ

### How is this different from just pointing agents at `llms.txt` directly?

`llms.txt` is the doc index. This skill adds the trigger logic ("when should the agent reach for Tensorlake docs at all?"), the fetch-and-fallback flow, guardrails (don't print API keys, verify symbols against installed packages), and an offline snapshot for when the network is unreachable. It's the difference between "here are the docs" and "here's how an agent should behave when a task involves Tensorlake."

### How does this compare to an MCP server?

MCP servers are runtime processes that expose tools to an agent over a protocol. Skills are static markdown files the agent reads. Tradeoffs:

- **MCP** is better when you need live state, authenticated API calls, or tool-use semantics (e.g., "list my running sandboxes").
- **Skills** are better for teaching an agent *how to write code* against an SDK — no server to run, works in any agent that supports skills, zero runtime overhead.

The two are complementary. You can use both.

### Does this work with models other than Claude?

Yes. The skill is model-agnostic — it's a markdown instruction file. It works with Claude Code, OpenAI Codex (via `AGENTS.md`), Google ADK, Cursor, Cline, GitHub Copilot, and Windsurf. The underlying Tensorlake SDK works with any LLM provider (OpenAI, Anthropic, open models) and any agent framework.

### Do I need a Tensorlake API key to install the skill?

No — installing the skill is just adding a file. You'll need a `TENSORLAKE_API_KEY` when the agent actually runs Tensorlake code on your behalf. Get one at [cloud.tensorlake.ai](https://cloud.tensorlake.ai).

### What happens if `docs.tensorlake.ai` is unreachable?

The skill falls back to bundled snapshots in `references/`. They lag the live docs (intentionally — they're not the source of truth) but cover the major API surface: sandboxes, applications/workflows, persistence, computer use, integrations, and platform features.

### How often is this updated?

A weekly CI job diffs the bundled snapshots against live docs and opens an issue if they've drifted. Reference files are refreshed per SDK release. The live docs are always current — the skill just routes to them.



## Documentation

- [Tensorlake Docs](https://docs.tensorlake.ai)
- [LLM-friendly docs](https://docs.tensorlake.ai/llms.txt)
- [API Reference](https://docs.tensorlake.ai/api-reference/v2/introduction)

## License

MIT
