---
name: tensorlake
license: MIT
description: >
  TensorLake SDK for building agentic workflows, sandboxed code execution, and document parsing/extraction.
  Use when the user mentions tensorlake, or asks about TensorLake APIs/docs/capabilities.
  Also use when the user is building AI agents or agentic applications that need
  serverless workflow orchestration (parallel map/reduce DAGs),
  sandboxed execution of LLM-generated code,
  or document parsing, structured extraction, and OCR from PDFs/images.
  Works with any LLM provider (OpenAI, Anthropic), agent framework (LangChain, CrewAI, LlamaIndex),
  database, or API as the infrastructure layer.
metadata:
  author: tensorlake
  version: 1.0.0
---

# TensorLake SDK

Three APIs: **Applications** (serverless workflow DAGs), **Sandbox** (isolated code execution), **DocumentAI** (document parsing/extraction). Use standalone or as infrastructure alongside any LLM, agent framework, database, or API.

**For documentation questions**: Read the relevant reference file below to answer. If the bundled references don't cover it, fetch `https://docs.tensorlake.ai/llms.txt` for the latest docs.
**For building**: Use the Quick Start and Core Patterns below, plus reference files for API details.

## Setup

TensorLake requires a `TENSORLAKE_API_KEY` environment variable. Before writing any TensorLake code, verify the key is set by running `echo $TENSORLAKE_API_KEY`. If not set, ask the user to provide their API key and guide them to set it:

```bash
export TENSORLAKE_API_KEY="your-api-key-here"
```

Get an API key at https://console.tensorlake.ai. Run `tensorlake login` as an alternative to set it interactively. For deployed applications, use the `secrets` parameter in `@function()` to pass the key securely.

## Quick Start — Agentic Workflow Application

```python
from tensorlake.applications import (
    application, function, run_local_application, Image, File
)

@application()
@function()
def orchestrator(urls: list[str]) -> list[dict]:
    """Entry point: must have both @application and @function."""
    fetched = fetch_page.map(urls)           # parallel map
    summary = summarize.reduce(fetched, initial="")  # reduce
    return format_output(summary)

@function(timeout=60)
def fetch_page(url: str) -> str:
    import requests
    return requests.get(url).text

@function(image=Image(base_image="python:3.11-slim").run("pip install openai"))
def summarize(accumulated: str, page: str) -> str:
    # reduce signature: (accumulated, next_item) -> accumulated
    return accumulated + "\n" + page[:500]

@function()
def format_output(text: str) -> dict:
    return {"summary": text}

if __name__ == "__main__":
    request = run_local_application(orchestrator, ["https://example.com"])
    print(request.output())
```

## Core Patterns

- **DAG composition**: Chain functions via `.future()`, `.map()`, `.reduce()` to form parallel pipelines
- **Agentic + Sandbox**: Use Applications to orchestrate, Sandbox to execute LLM-generated code safely
- **Document extraction**: Use DocumentAI with Pydantic schemas to extract structured data from PDFs/images
- **LLM integration**: Use any LLM provider inside `@function()` — install deps via `Image`, pass keys via `secrets`
- **Framework integration**: Use Sandbox as a code execution tool for LangChain/CrewAI/LlamaIndex agents, or DocumentAI as a document loader for any RAG pipeline

For integration examples (LangChain, CrewAI, OpenAI function calling, multi-agent orchestration): See [references/integrations.md](references/integrations.md)

## Key Rules

1. **Entry point needs both decorators**: `@application()` then `@function()` on the same function.
2. **Reduce signature**: `def my_reduce(accumulated, next_item) -> accumulated_type` — two positional args.
3. **Map input**: Pass a list or a Future that resolves to a list.
4. **Futures chain**: `result = step2.future(step1.future(x))` — step2 waits for step1 automatically.
5. **Local dev**: `run_local_application(fn, *args)` — no containers needed.
6. **Remote deploy**: `tensorlake deploy path/to/app.py` then `run_remote_application(fn, *args)`.
7. **Custom images**: Use `Image(base_image=...).run("pip install ...")` for dependencies.
8. **Secrets**: Declare with `secrets=["MY_SECRET"]` in `@function()`, manage via `tensorlake secrets`.

## API Reference

Bundled references (use when building with TensorLake):

- **Applications SDK** (decorators, futures, map/reduce, images, context): See [references/applications_sdk.md](references/applications_sdk.md)
- **Sandbox SDK** (create, run commands, file ops, snapshots, pools): See [references/sandbox_sdk.md](references/sandbox_sdk.md)
- **DocumentAI SDK** (parse, extract, classify, options): See [references/documentai_sdk.md](references/documentai_sdk.md)
- **Integrations** (LangChain, CrewAI, OpenAI tools, RAG pipelines): See [references/integrations.md](references/integrations.md)

**Latest docs**: If bundled references lack detail, fetch https://docs.tensorlake.ai/llms.txt for the most up-to-date API documentation.

## CLI Commands

```bash
tensorlake deploy path/to/app.py        # Deploy to cloud
tensorlake parse --file-path doc.pdf     # Parse document
tensorlake login                         # Authenticate
tensorlake secrets                       # Manage secrets
tensorlake create-template               # Create sandbox template
```
