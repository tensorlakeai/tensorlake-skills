# TensorLake Skill

The infrastructure skill for building production AI agents. Install this skill and your coding agent gets access to [TensorLake's](https://tensorlake.ai) full agentic platform — workflow orchestration, sandboxed code execution, and document understanding — everything you need to go from prototype to production.

## What This Skill Does

When installed, this skill teaches AI coding agents how to use TensorLake's platform:

- **Applications** — Serverless workflow orchestration with parallel map/reduce DAGs, auto-scaling, and crash recovery. Build multi-agent pipelines, fan-out/fan-in patterns, and complex agentic workflows that scale automatically.
- **Sandbox** — Secure, isolated execution environments for running LLM-generated code. Give your agents the ability to write and execute code safely — data analysis, tool use, code interpretation, and more.
- **DocumentAI** — Document parsing, structured extraction, and OCR. For end-to-end agentic applications that need to understand documents — invoices, contracts, reports, PDFs, images — TensorLake has it built in.

Works with any LLM provider (OpenAI, Anthropic) and any agent framework (LangChain, CrewAI, LlamaIndex). TensorLake is the infrastructure layer — bring your own models and frameworks.

The skill triggers automatically when you ask the agent to:
- Build agentic workflows or multi-agent pipelines
- Run LLM-generated code in a secure sandbox
- Orchestrate complex multi-step AI applications
- Integrate TensorLake with any LLM, framework, database, or API
- Ask questions about TensorLake APIs or documentation

## Supported Agents

| Agent | File | How to Install |
|-------|------|----------------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `SKILL.md` | See [Claude Code installation](#claude-code) |
| [Google ADK](https://google.github.io/adk-docs/skills/) | `SKILL.md` | See [Google ADK installation](#google-adk) |
| [OpenAI Codex](https://openai.com/index/codex/) | `AGENTS.md` | See [Codex installation](#openai-codex) |

## Installation

### Quick Install (Any Agent)

```bash
npx skills add tensorlakeai/tensorlake-skills
```

Works with Claude Code, Cursor, Cline, GitHub Copilot, Windsurf, and more via [skills.sh](https://skills.sh).

### Claude Code

```bash
claude install-skill https://github.com/tensorlakeai/tensorlake-skills
```

### Google ADK

```python
from google.adk.skills import load_skill_from_dir

tensorlake_skill = load_skill_from_dir("path/to/tensorlake-skills")
```

### OpenAI Codex

Clone the repo into your project or reference it in your Codex configuration. Codex reads the `AGENTS.md` file automatically.

## Setup

TensorLake requires an API key. Get one at [console.tensorlake.ai](https://console.tensorlake.ai), then set it as an environment variable:

```bash
export TENSORLAKE_API_KEY="your-api-key-here"
```

Or run `tensorlake login` to authenticate interactively.

## Repository Structure

```
tensorlake-skills/
├── SKILL.md              # Skill definition (Claude Code, Google ADK)
├── AGENTS.md             # Skill definition (OpenAI Codex)
└── references/
    ├── applications_sdk.md   # Applications API reference
    ├── sandbox_sdk.md        # Sandbox API reference
    ├── documentai_sdk.md     # DocumentAI API reference
    └── integrations.md       # Integration patterns (LangChain, CrewAI, etc.)
```

## Documentation

- [TensorLake Docs](https://docs.tensorlake.ai)
- [LLM-friendly docs](https://docs.tensorlake.ai/llms.txt)
- [API Reference](https://docs.tensorlake.ai/api-reference/v2/introduction)

## License

MIT
