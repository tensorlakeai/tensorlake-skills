# TensorLake SDK

TensorLake provides three APIs for building agentic applications:

- **Applications** — Serverless workflow DAGs with parallel map/reduce, auto-scaling, and crash recovery
- **Sandbox** — Isolated code execution environments for running LLM-generated code safely
- **DocumentAI** — Document parsing, structured data extraction, and OCR from PDFs/images

Use standalone or as infrastructure alongside any LLM provider, agent framework, database, or API.

## Setup

TensorLake requires the `TENSORLAKE_API_KEY` environment variable to be configured. Verify it is set before writing TensorLake code. If not set, direct the user to run `tensorlake login` or to configure the key via their environment (e.g., shell profile or `.env` file). Do **not** ask the user to paste their API key directly into the conversation or echo it in a command. Get an API key at https://console.tensorlake.ai.

## Quick Start

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
    """Fetch a user-provided URL. Validate/sanitize URLs before use."""
    import requests
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text

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

## Key Rules

1. Entry point needs both `@application()` and `@function()` on the same function.
2. Reduce signature: `def my_reduce(accumulated, next_item) -> accumulated_type` — two positional args.
3. Map input: pass a list or a Future that resolves to a list.
4. Futures chain: `result = step2.future(step1.future(x))` — step2 waits for step1 automatically.
5. Local dev: `run_local_application(fn, *args)` — no containers needed.
6. Remote deploy: `tensorlake deploy path/to/app.py` then `run_remote_application(fn, *args)`.
7. Custom images: `Image(base_image=...).run("pip install ...")` for dependencies.
8. Secrets: declare with `secrets=["MY_SECRET"]` in `@function()`, manage via `tensorlake secrets`.

## Core Patterns

- **DAG composition**: Chain functions via `.future()`, `.map()`, `.reduce()` to form parallel pipelines
- **Agentic + Sandbox**: Use Applications to orchestrate, Sandbox to execute LLM-generated code safely
- **Document extraction**: Use DocumentAI with Pydantic schemas to extract structured data from PDFs/images
- **LLM integration**: Use any LLM provider inside `@function()` — install deps via `Image`, pass keys via `secrets`
- **Framework integration**: Use Sandbox as a code execution tool for LangChain/CrewAI/LlamaIndex agents, or DocumentAI as a document loader for any RAG pipeline

## Reference Documentation

Detailed API docs are in the `references/` directory:

- `references/applications_sdk.md` — Decorators, futures, map/reduce, images, context
- `references/sandbox_sdk.md` — Create sandboxes, run commands, file ops, snapshots, pools
- `references/documentai_sdk.md` — Parse, extract, classify, options
- `references/integrations.md` — LangChain, CrewAI, OpenAI tools, RAG pipeline patterns

For the latest documentation: https://docs.tensorlake.ai/llms.txt

## CLI Commands

```bash
tensorlake deploy path/to/app.py        # Deploy to cloud
tensorlake parse --file-path doc.pdf     # Parse document
tensorlake login                         # Authenticate
tensorlake secrets                       # Manage secrets
tensorlake create-template               # Create sandbox template
```
