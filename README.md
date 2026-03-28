# Tensorlake Skill

Build production agent workflows with [Tensorlake's](https://tensorlake.ai).

This skill helps coding agents use Tensorlake to build real agent systems with sandboxed execution and orchestration. It is designed for modern agent use cases like multi-agent applications, isolated code execution, long-running workflows, and tool-using agents that need a real workspace.

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
Works with any LLM provider (OpenAI, Anthropic) and any agent framework (LangChain, CrewAI, LlamaIndex). Tensorlake is the infrastructure layer — bring your own models and frameworks.

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

Tensorlake requires a `TENSORLAKE_API_KEY` configured in the local environment. Get one at [cloud.tensorlake.ai](https://cloud.tensorlake.ai), then either run `tensorlake login` or configure the variable through your shell profile, `.env` file, or secret manager. Do not paste API keys into chat, commit them to source control, or print them in terminal output.

## Repository Structure

```
tensorlake-skills/
├── SKILL.md              # Skill definition (Claude Code, Google ADK)
├── AGENTS.md             # Skill definition (OpenAI Codex)
└── references/
    ├── applications_sdk.md   # Orchestrate API reference
    ├── sandbox_sdk.md        # Sandbox API reference
    ├── documentai_sdk.md     # DocumentAI API reference
    └── integrations.md       # Integration patterns (LangChain, CrewAI, etc.)
```

## Documentation

- [Tensorlake Docs](https://docs.tensorlake.ai)
- [LLM-friendly docs](https://docs.tensorlake.ai/llms.txt)
- [API Reference](https://docs.tensorlake.ai/api-reference/v2/introduction)

## License

MIT