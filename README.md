# Tensorlake Skill

A lightweight skill that points coding agents at the live [Tensorlake](https://tensorlake.ai) docs whenever they need to write Tensorlake code.

Tensorlake's docs change frequently. Rather than freezing a large chunk of API surface into the skill, this skill stays small: it tells the agent what Tensorlake is, makes sure the SDK and `TENSORLAKE_API_KEY` are set up, and then routes it to `https://docs.tensorlake.ai/llms.txt` to fetch the live docs that match the task. It covers the **Python** (`pip install tensorlake`) and **TypeScript** (`npm install tensorlake`) SDKs, plus the **CLI** (`curl -fsSL https://tensorlake.ai/install | sh`).

Bundled snapshots under `references/` are an offline fallback only — used when the live fetch fails (network unreachable, non-2xx, timeout). They are not the source of truth and are expected to lag.

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

## Documentation

- [Tensorlake Docs](https://docs.tensorlake.ai)
- [LLM-friendly docs](https://docs.tensorlake.ai/llms.txt)
- [API Reference](https://docs.tensorlake.ai/api-reference/v2/introduction)

## License

MIT
