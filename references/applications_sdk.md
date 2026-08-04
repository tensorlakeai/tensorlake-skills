<!--
Source:
  - https://docs.tensorlake.ai/applications/introduction.md
  - https://docs.tensorlake.ai/applications/overview.md
  - https://docs.tensorlake.ai/applications/quickstart.md
  - https://docs.tensorlake.ai/applications/architecture.md
  - https://docs.tensorlake.ai/applications/concepts.md
  - https://docs.tensorlake.ai/applications/building-workflows.md
  - https://docs.tensorlake.ai/applications/error-handling.md
  - https://docs.tensorlake.ai/applications/futures.md
  - https://docs.tensorlake.ai/applications/map-reduce.md
  - https://docs.tensorlake.ai/applications/async-functions.md
  - https://docs.tensorlake.ai/applications/images.md
  - https://docs.tensorlake.ai/applications/durability.md
  - https://docs.tensorlake.ai/applications/crash-recovery.md
  - https://docs.tensorlake.ai/applications/retries.md
  - https://docs.tensorlake.ai/applications/secrets.md
  - https://docs.tensorlake.ai/applications/timeouts.md
  - https://docs.tensorlake.ai/applications/public-endpoints.md
  - https://docs.tensorlake.ai/applications/scale-out-queuing.md
  - https://docs.tensorlake.ai/applications/scaling-agents.md
  - https://docs.tensorlake.ai/applications/observability.md
  - https://docs.tensorlake.ai/applications/cron-scheduler.md
  - https://docs.tensorlake.ai/applications/parallel-sub-agents.md
  - https://docs.tensorlake.ai/applications/sandboxes.md
  - https://docs.tensorlake.ai/applications/guides/streaming-progress.md
  - https://docs.tensorlake.ai/applications/guides/logging.md
SDK version: tensorlake 0.5.97
Last verified: 2026-08-04
-->

# TensorLake Applications SDK Reference

Tensorlake Orchestration ("Applications") is a **compute platform for agents**: it runs your agents, it doesn't replace your agent framework. You bring the agent logic (OpenAI Agents SDK, LangGraph, Claude Agent SDK, or plain Python), and Tensorlake provides serverless containers, durable execution, sandboxes, and observability.

## Table of Contents

- [Imports](#imports)
- [Decorators](#decorators)
- [Calling Functions](#calling-functions)
- [Input/Output Serialization](#inputoutput-serialization)
- [Map & Reduce](#map--reduce)
- [Future API](#future-api)
- [Async Functions](#async-functions)
- [Running Applications](#running-applications)
- [Public Endpoints](#public-endpoints)
- [Durable Execution](#durable-execution)
- [RequestContext](#requestcontext)
- [Image Builder](#image-builder)
- [File Type](#file-type)
- [Retries](#retries)
- [Scaling](#scaling)
- [Cron Scheduler](#cron-scheduler)
- [Exceptions](#exceptions)
- [Secrets](#secrets)
- [Observability](#observability)
- [Sandboxes and Orchestration](#sandboxes-and-orchestration)

## Imports

```python
from tensorlake.applications import (
    application, function, cls,
    run_local_application, run_remote_application,
    get_remote_request,
    Future, RETURN_WHEN,
    RequestContext, Request, File, HttpBody, Image, Retries,
    ReplayMode, RequestError, Logger,
)
```

Note `Image` for Applications comes from `tensorlake.applications` — the sandbox image DSL is a different `Image` from `tensorlake`.

## Decorators

### @application()

Entry point decorator. Must wrap a function also decorated with `@function()`. Each application gets a unique HTTP entry point named after the Python function.

```python
@application(
    tags: dict[str, str] = {},
    retries: Retries | None = None,   # Default for every function in the app; no retries by default
    region: str | None = None,        # "us-east-1" or "eu-west-1"; default is any region
    allow: list[str] | None = None,   # Application capabilities. Only "unauthenticated_requests" is supported.
)
```

`allow=["unauthenticated_requests"]` creates a public endpoint callable without a Tensorlake API key — see [Public Endpoints](#public-endpoints).

### @function()

Decorates individual callable functions. Every call executes in its own function container, supports durable execution, can run in parallel, can be retried independently, has its own resource limits, and gets its own logs and execution timeline.

```python
@function(
    description: str = "",
    cpu: float = 1.0,              # 1.0–8.0
    memory: float = 1.0,           # GB, 1.0–32.0
    ephemeral_disk: float = 2.0,   # GB, 2.0–50.0 (SSD at /tmp)
    gpu: str | None = None,        # e.g. "T4", "H100" — contact support@tensorlake.ai to enable GPU support
    timeout: int = 300,            # seconds, 1–172800 (max 48 hours)
    image: Image = Image(),
    secrets: list[str] = [],
    retries: Retries | int | None = None,
    region: str | None = None,
    # Documented on other pages, not in the SDK Reference attribute list:
    warm_containers: int | None = None,   # Pre-warmed containers for zero cold starts
    max_containers: int | None = None,    # Upper limit; excess queued FIFO
    concurrency: int | None = None,       # Concurrent requests per container
    durable: bool = True,                 # Enable/disable checkpointing
)
```

Resource guidance from the docs: for functions with multi-gigabyte inputs or outputs, use **at least 3 CPUs** (fastest download/upload). Set `memory` to **at least 2× the size of the largest input or output**, since both serialized and deserialized representations are held in memory. `/tmp` (`ephemeral_disk`) is SSD-backed and erased when the container terminates; other paths like `/home/ubuntu` are slower. Python `tempfile` writes land in `/tmp`.

**Timeout auto-reset**: calling `ctx.progress.update()` resets the timeout counter, so a function can run indefinitely while it keeps reporting progress. Recommended pattern: set a **short** timeout and rely on progress updates, so a stuck function fails fast instead of running silently for hours.

### @cls()

Marks a class whose methods can be decorated with `@function()`. `__init__(self)` runs once per function-container startup for one-time initialization and **cannot take arguments other than `self`**.

```python
@cls()
class MyCompute:
    def __init__(self):
        self.model = load_large_model()

    @application()
    @function(cpu=4, memory=16)
    def run(self, data: str) -> int:
        return self.model.run(data)

# Call a class-method application by name:
run_remote_application("MyCompute.run", data="some input data")
```

### Application functions vs regular functions

Every `@application()` function is also a Tensorlake function, which is why it needs `@function()` too. As HTTP entry points, application functions:

- **Require JSON-serializable type hints** for all arguments and the return value.
- **Don't support `/` and `*`** in the argument list.
- **Don't support `*args` and `**kwargs`.**
- **Ignore call arguments not defined in the signature** — which makes code migrations easy: an old client can keep sending arguments the function no longer takes.

Regular `@function()` arguments and return values need no type hints but **must be picklable** (most Python objects are; Processes, Threads, and DB connections are not). A `File` argument or return value bypasses pickling and is passed as-is. Application functions can be called from regular functions; the call runs inside the current request without creating a new one.

## Calling Functions

```python
# Synchronous (blocks the calling function until the call completes)
result = my_function(arg1, arg2)

# Non-blocking (returns a Future)
future = my_function.future(arg1, arg2)
result = future.result()

# Async
result = await my_function.future(arg1, arg2)
```

## Input/Output Serialization

Application inputs are deserialized from JSON via type hints; the return value is JSON-serialized per the return hint and becomes the HTTP response body. Each hint must be [supported in Pydantic JSON mode](https://docs.pydantic.dev/latest/concepts/serialization/#json-mode). Supported: `str`, `int`, `float`, `bool`, `list`, `dict`, `set`, `tuple`, `None`, `Any`, `|` unions, Pydantic model classes, and more. A union hint (`str | int`) accepts any member type. `Any` accepts any valid JSON value and deserializes to the corresponding Python object; **missing type hints are treated as `Any`**.

Request-body rules when calling over HTTP:

| Application signature | Request body |
|---|---|
| No arguments | Empty POST body |
| One argument | JSON-serialized body |
| Multiple arguments, or one or more files | `multipart/form-data` |

```bash
# no arguments
curl https://api.tensorlake.ai/applications/hello_world \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" --json ''

# single argument
curl https://api.tensorlake.ai/applications/greet \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" --json '"Hello, John"'

# multiple arguments — one form field per parameter, each with its own content type
curl https://api.tensorlake.ai/applications/process_data \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  -H "Accept: application/json" \
  -F 'query=[{"name":"Alice","age":25}];type=application/json' \
  -F 'limit=10;type=application/json'

# file upload
curl https://api.tensorlake.ai/applications/process_file \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" \
  -F "input=@/foo/bar/file_name.txt"
```

Arguments with default values may be omitted from the request input.

## Map & Reduce

**Map** applies a function to each item of a list in parallel. **Reduce** aggregates the results. Tensorlake parallelizes map calls across containers; the reducer is applied to each pair of mapped values **sequentially in the original list order**, and each reduce call runs as soon as its inputs are available.

```python
# Blocking
squares: list[int] = square.map([i for i in range(n)])
total: TotalSum = sum_total.reduce(squares, TotalSum(value=0))   # (items, initial)

# Non-blocking (Futures)
squares_future = square.future.map([i for i in range(n)])
return sum_total.future.reduce(squares_future, TotalSum(value=0))   # tail call
```

The reducer signature is `(accumulated, next_item) -> accumulated`. The initial value is optional — `sum.reduce(squares)` is also valid.

**Inputs.** Both operations accept:

- **A list**, where each item can be a value, a `Future`, a Tensorlake coroutine, or an `asyncio.Task`. Tensorlake recognizes and runs those automatically and uses their results as inputs.
- **A single `Future` / coroutine / `asyncio.Task`** that resolves to a list. Tensorlake waits for it and uses the returned list as the operation input — useful when the input list is produced by another Tensorlake function.

**Tail call optimization**: map and reduce Futures can be returned from functions as tail calls. The returning function completes immediately and frees its container while Tensorlake orchestrates the operation.

## Future API

A Future defines, runs, and tracks a function call or a map/reduce operation. It is created with the `function.future` factory and **does not start running** until `.run()` or `.result()` is called, it is used as a function-call argument, or it is returned from a function.

```python
future = my_function.future(arg1, arg2)
future.run()                 # start immediately; returns self for chaining. Blocks to START, not to finish.
future.result(timeout=None)  # block for the result; raises FunctionError on failure, TimeoutError on timeout
future.done()                # True once completed (successfully or with an exception)
future.exception             # property: TensorlakeError | None (also None while incomplete)

await future                 # via __await__(); equivalent to .result() without blocking the event loop
coro = future.coroutine()    # convert to a coroutine — must be called BEFORE .run(); returns the same object each time

done, not_done = Future.wait(
    futures,                                # Iterable[Future]
    timeout=None,                           # float | None
    return_when=RETURN_WHEN.ALL_COMPLETED,  # ALL_COMPLETED | FIRST_COMPLETED | FIRST_EXCEPTION
)                                           # -> tuple[list[Future], list[Future]]
```

`Future.wait` mirrors `concurrent.futures.wait`. **A future that isn't running yet is started automatically when passed to `Future.wait`.**

Futures passed as arguments to other functions are auto-resolved — Tensorlake runs them if needed, waits, and substitutes the results:

```python
a = double.future(x)
b = double.future(x + 1)
result = add(a, b)   # add waits for a and b automatically; a and b run in parallel
```

**Tail calls.** A function makes a tail call by **returning a Future**. The Future's result becomes the function's return value; the Future starts running immediately and the calling container is freed to process other work. This avoids three costs of blocking calls: wasted resources while waiting, more containers needed for the same concurrency, and higher latency from sequential blocking.

```python
@application()
@function()
def greet(name: str) -> str:
    capitalized_name: Future = capitalize.future(name)
    joke: Future = make_joke.future(name)
    # Tail call: greet returns almost immediately and frees its container.
    return say_hello_and_say_joke.future(capitalized_name, joke=joke)
```

> **Wrapping Futures inside other Python objects is NOT allowed** — as arguments or as tail calls. `return concat([some_future, name])` will not work: Tensorlake does not recognize a Future nested in a list/dict/object and will neither run it nor wait for it. The one exception is **map and reduce inputs**, which do recognize Futures inside a list.

## Async Functions

An `async` Tensorlake function returns a coroutine when called:

```python
@function()
async def fetch_data(url: str) -> dict: ...

result = await fetch_data(url)                          # blocks
task = asyncio.create_task(fetch_data(url))             # background
results = await asyncio.gather(fetch_a(x), fetch_b(y))  # parallel

doubled = await double.map(numbers)                     # async map/reduce
total = await add.reduce(doubled)
```

Returning a coroutine or a Future as a tail call frees the container immediately. Calling sync from async: use `.future()` to avoid blocking the event loop. Calling async from sync: use `.future().result()`.

## Running Applications

```bash
tl app new hello_world              # scaffolds hello_world/hello_world.py
tl app deploy hello_world/hello_world.py
```

```python
# Local (dev/test, in-process, no containers) — runs as a normal Python script
request: Request = run_local_application(my_app, *args, **kwargs)
output = request.output()   # blocks; raises on failure

# Remote (Tensorlake Cloud, containers, autoscaling)
request: Request = run_remote_application(my_app, *args, **kwargs)
request: Request = run_remote_application("app_name", *args, **kwargs)   # by name
print(request.id)
output = request.output()   # you do NOT need to poll — retrieving the output waits for completion
```

**HTTP:**

```bash
# Invoke -> {"request_id": "beae8736ece31ef9"}
curl https://api.tensorlake.ai/applications/hello_world \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" --json '"John"'

# Check progress -> {"id":..., "outcome":"success", "failure_reason":null, "request_error":null, ...}
curl -X GET https://api.tensorlake.ai/applications/hello_world/requests/{request_id} \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"

# Get the output
curl -X GET https://api.tensorlake.ai/applications/hello_world/requests/{request_id}/output \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY"
```

`outcome` is `success` or `failure`, and is **`null` while the request is still in progress**.

## Public Endpoints

By default applications require an API key. Adding the `unauthenticated_requests` capability creates a public endpoint callable without Tensorlake credentials.

```python
from tensorlake.applications import application, function

@application(allow=["unauthenticated_requests"])
@function()
def public_api(payload: dict) -> dict:
    return {"status": "accepted", "payload": payload}
```

Deploy normally (`tl app deploy public_api.py`). On the **first** deployment Tensorlake assigns the application a stable, opaque `public_endpoint_id`; redeploying preserves it:

```text
https://api.tensorlake.ai/applications/public/<public_endpoint_id>
```

```bash
curl https://api.tensorlake.ai/applications/public/<public_endpoint_id> --json '{"event": "created"}'
```

To disable public access, remove `unauthenticated_requests` from `allow` and redeploy.

### HttpBody — raw request bodies

Use the `HttpBody` type when you need the raw request body (e.g. to verify a webhook signature over exact bytes):

```python
from tensorlake.applications import HttpBody, application, function

@application(allow=["unauthenticated_requests"])
@function()
def receive_raw_body(body: HttpBody) -> dict:
    return {
        "content_type": body.content_type,
        "size": len(body.content),
        "payload": body.json(),
    }
```

`HttpBody` exposes `body.content` (raw bytes), `body.content_type`, `body.text()`, and `body.json()`.

### Webhook receiver example

```python
import hmac, os
from hashlib import sha256
from tensorlake.applications import HttpBody, RequestContext, application, function

def verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@application(allow=["unauthenticated_requests"])
@function(secrets=["GITHUB_WEBHOOK_SECRET"])
def github_webhook(body: HttpBody) -> dict[str, str]:
    headers = RequestContext.get().headers
    if headers.get("X-GitHub-Event") != "workflow_job":
        return {"status": "ignored"}
    if not verify_signature(body.content, headers.get("X-Hub-Signature-256"),
                            os.environ["GITHUB_WEBHOOK_SECRET"]):
        return {"status": "rejected"}
    event = body.json()
    return {"status": "accepted", "action": event.get("action", "")}
```

## Durable Execution

> Durable execution is in **technical preview** per the docs.

Every `@function()` call in a request is automatically checkpointed: outputs of successful calls are reused without re-execution when the request is replayed or a function is retried.

```python
from tensorlake.applications import Request, get_remote_request, ReplayMode

request: Request = get_remote_request(application_name, request_id)
request.replay()                                  # adaptive mode (default)
request.replay(upgrade_to_latest_version=True)    # re-run with the latest deployed code
request.replay(mode=ReplayMode.STRICT)            # fails with ReplayError if new calls appear
request.replay(mode=ReplayMode.ADAPTIVE)          # allows new calls
print(request.output())
```

```bash
curl "https://api.tensorlake.ai/applications/$APPLICATION_NAME/requests/$REQUEST_ID/replay" \
  -H "Authorization: Bearer $TENSORLAKE_API_KEY" --json '{}'
# --json '{"mode": "strict"}' | '{"mode": "adaptive"}' | '{"upgrade_to_latest_version": true}'
```

Replay **does not create a new request** — it re-runs the same request with the same request ID and updates the output.

**Replay modes.** *Adaptive* (default) allows a replayed request to take a different execution path; new calls execute normally and removed calls are ignored. *Strict* fails with `ReplayError` if a new call is detected while one or more calls from the original run are not re-executed — use it when all resources claimed in the original run must be reused (no repeated cross-service transactions).

**How calls are matched.** Tensorlake fingerprints every function call. A fingerprint includes the call type (`function_call`, `map`, `reduce`), function name, parent call fingerprint, call sequence number in the parent, plus structural information. **Function parameters are NOT part of the fingerprint**, so:

- Changing parameters in application code doesn't affect replay matching (seamless code upgrades).
- Passing different values (random numbers, current time) doesn't affect matching.
- Changing the **sequence** of calls does break matching — behavior then depends on the replay mode.
- Arbitrary call ordering (e.g. random delays) makes matching non-deterministic even without code changes. Avoid it.

**Disabling durability** for functions that must always run fresh:

```python
@function(durable=False)
def get_current_weather() -> str: ...
```

Non-durable calls are always re-executed on replay/retry and their outputs are never reused. **Avoid calling other Tensorlake functions from a non-durable function** — all such calls also become non-durable. With strict replay, no validation is done on non-durable calls.

**Automatic retries** use the same mechanism, and always use adaptive mode.

**Best practices:** wrap every external call (LLM, API, database) in a Tensorlake function; design for determinism; make side effects idempotent; disable durability for functions that must run fresh; ensure backward compatibility if you combine strict mode with a code upgrade.

**Human-in-the-loop.** The replay API doubles as a resume mechanism for requests that timed out waiting on an external input: a `wait_approval` function with a 5-minute timeout fails, and replaying after approval skips the completed steps and re-executes only the waiting one.

## RequestContext

Available only during function execution.

```python
ctx: RequestContext = RequestContext.get()
ctx.request_id                          # str — unique per request

# Request headers (immutable, case-insensitive)
ctx.headers["X-Request-Type"]           # required header — raises if absent
ctx.headers.get("x-request-signature")  # optional; returns the LAST value of a repeated header
ctx.headers.getlist("X-Provider-Tag")   # all values, in received order

# Key-value state, scoped to the request; each request starts empty. Values must be picklable.
ctx.state.set(key, value)               # -> None
ctx.state.get(key, default=None)        # -> Any | None

# Metrics
ctx.metrics.timer(name, value)          # duration in seconds
ctx.metrics.counter(name, value=1)      # counters start at 0

# Progress reporting (also resets the function timeout)
ctx.progress.update(
    current,        # int | float — current step or percentage
    total,          # int | float — total steps, or 100 for percentage
    message=None,   # str | None
    attributes=None,  # dict[str, str] | None
)
```

Tensorlake **strips sensitive and connection-specific headers** before building the request context: `Authorization`, `Authentication`, `Cookie`, proxy authentication headers, `Host`, standard hop-by-hop headers, and headers named by `Connection`.

Poll progress with `GET /applications/{app}/requests/{request_id}/progress`:

```json
{
  "current": 45,
  "total": 100,
  "message": "Processing batch 3 of 10",
  "attributes": {"batch_id": "batch_003", "records_processed": "4500"},
  "timestamp": 1704067200000
}
```

## Image Builder

Container images are built when you deploy an application.

```python
from tensorlake.applications import Image, function

image = (
    Image(name="my-pdf-parser-image", base_image="ubuntu:24.04")
    .run("apt update")
    .run("pip install langchain")
)

@function(image=image, gpu="T4")
def parse_pdf(pdf_path: str) -> str:
    import langchain   # MUST be imported inside the function body
    ...
```

**Packages installed in the image must be imported inside the function body**, not at module level — they may not exist in the Python environment you deploy from.

Default base image: `python:{LOCAL_PYTHON_VERSION}-slim-bookworm` (Debian), where `LOCAL_PYTHON_VERSION` is the Python version of your current environment.

Chainable builder method documented for application images: `.run(command)`.

**Private base images.** If `base_image` lives in a private registry, Tensorlake authenticates the pull using your local Docker config (`$DOCKER_CONFIG/config.json`, default `~/.docker/config.json`) — e.g. after `docker login`. Function images build through the same path as sandbox images, so the setup is identical.

## File Type

```python
class File:
    content: bytes       # raw bytes of the file
    content_type: str    # MIME content type
```

A `File` argument or return value bypasses JSON/pickle serialization. As an application input the HTTP body is the raw bytes and content type; as an application output the response body is `File.content` with `Content-Type: File.content_type`. **Files up to 5 TB are supported**, but the SDK does not support lazy loading — the entire file is loaded into memory when the function is called.

```python
from tensorlake.applications import run_remote_application, File

with open("/foo/bar/file_name.txt", "rb") as f:
    run_remote_application("process_file", File(content=f.read(), content_type="text/plain"))
```

> The Tensorlake SDK `File` is not Python's built-in file object.

## Retries

```python
from tensorlake.applications import function, Retries

@function(retries=Retries(max_retries=3))
def risky_step(): ...

@function(retries=3)      # shorthand
def risky_step(): ...
```

The default policy is **no retries**. Rate-limit errors, timeouts, exceptions, and **validation failures (e.g. Pydantic `ValidationError`)** all trigger retries, with exponential backoff. Nested calls that already succeeded are served from checkpoints. If retries are exhausted the request fails and can be re-run later with the Replay API. Set a default policy for every function via `@application(retries=...)`.

If you allow retries, make the function **idempotent** unless that's genuinely unnecessary for your case.

> **Disable client-level retries (e.g. OpenAI's `max_retries=0`) when using Tensorlake retries.** Layering both creates unpredictable behavior and inflated retry counts.

Structured-output validation is the canonical use: if an LLM returns malformed data, `model_validate_json` raises and Tensorlake retries the entire call.

## Scaling

```python
@function(warm_containers=2, max_containers=20, concurrency=5)
def agent(prompt: str) -> str: ...
```

- `warm_containers` — pre-warmed containers with code and dependencies loaded, eliminating cold-start latency. Use for low-latency paths and predictable baseline traffic.
- `max_containers` — upper limit. Once reached, additional requests are **automatically queued and processed FIFO**; no Redis/SQS/RabbitMQ needed.
- `concurrency` — concurrent requests per container.
- **Default (no parameters):** scales dynamically from zero based on demand, no upper bound, cold starts after idle, no queuing.
- Each function in a workflow scales **independently**.

**Rate-limiting external APIs:** total concurrent calls = `max_containers` × `concurrency`. For an API allowing 100 requests/second, `max_containers=50` with `concurrency=2` caps you at 100 in flight.

## Cron Scheduler

Schedule recurring invocations of a deployed application via the REST API or the Applications UI. **The schedule starts immediately after creation.**

```python
import requests, base64, json

payload = {"cron_expression": "0 * * * *"}      # 5-field cron; every hour
input_data = json.dumps({"report_type": "daily"}).encode()
payload["input_base64"] = base64.b64encode(input_data).decode()   # optional, max 1 MiB decoded

# Create
resp = requests.post(
    f"https://api.tensorlake.ai/applications/{application}/cron-schedules",
    json=payload,
    headers={"Authorization": "Bearer TENSORLAKE_API_KEY"},
)
schedule_id = resp.json()["schedule_id"]        # save it; required to delete

# List
requests.get(f"https://api.tensorlake.ai/applications/{application}/cron-schedules", headers=...)

# Delete (permanent; to modify, delete + recreate)
requests.delete(
    f"https://api.tensorlake.ai/applications/{application}/cron-schedules/{schedule_id}",
    headers=...,
)
```

**Request fields:** `cron_expression` (required, valid 5-field cron), `input_base64` (optional, base64 bytes passed as input on every invocation, max 1 MiB decoded).

**List response fields:** `id`, `application_name`, `cron_expression`, `next_fire_time_ms`, `last_fired_at_ms` (`null` if never fired), `created_at`, `enabled` (always `true`, reserved for future use).

> `next_fire_time_ms` and `last_fired_at_ms` are standard Unix **millisecond** timestamps (`new Date(next_fire_time_ms)` in JS). **`created_at` is a monotonic counter for ordering, not a wall-clock timestamp — do not display it as a date.**

**Limits:** minimum interval 60 seconds (`* * * * *` is the fastest; sub-minute expressions are rejected with `400`), max 100 schedules per application, max 1 MiB decoded input payload.

## Exceptions

| Exception | When |
|---|---|
| `RequestError` | Raise it to explicitly fail a request immediately |
| `TensorlakeError` | Base class (returned by `Future.exception`) |
| `FunctionError` | Raised by `Future.result()` when the operation failed |
| `TimeoutError` | Raised by `Future.result(timeout=...)` when the timeout is reached first |
| `ReplayError` | Strict replay encounters new function calls |

**Failure propagation.** A function fails by raising or timing out. An unhandled exception bubbles to the caller and can fail the request; failed requests can be re-run with the Replay API, with previously successful nested calls served from checkpoints. With Futures, errors surface when you call `.result()`.

```python
@application()
@function()
def workflow(user_input: str) -> dict:
    try:
        return {"status": "ok", "tool_output": call_tool(user_input)}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}   # degrade instead of failing the request
```

**Debugging:** reproduce locally (applications run as normal Python functions via `run_local_application`), add structured logs of inputs/outputs excluding secrets, and make side effects idempotent since functions can retry.

## Secrets

```bash
tl secrets set OPENAI_API_KEY=<value> [MORE=<value>]
tl secrets list          # names and creation dates only; values are never shown
tl secrets unset OPENAI_API_KEY [MORE]
```

```python
@function(secrets=["AWS_ACCESS_KEY", "OPENAI_API_KEY"])
def my_func() -> str:
    key = os.environ["OPENAI_API_KEY"]
```

**Redeploy the application after adding or updating a secret** for the new values to take effect.

Security: envelope encryption with AES-256-GCM. Each project has a dedicated Data Encryption Key (DEK) wrapped by a root Key Encryption Key (KEK) managed by AWS KMS. Secrets stay encrypted at rest and are decrypted **in memory only** on the dataplane machines running functions that need them, with all communication over mTLS.

## Observability

Every function call is automatically traced. The dashboard's execution timeline shows the function call sequence, timing (including cold-start time), which calls ran in parallel vs sequentially, and per-call status (success / failure / retry).

**Logging.** Standard `print()` and `logging` are captured automatically and associated with the specific function call and request; `print` output defaults to level `INFO`. Levels are `TRACE`(1), `DEBUG`(2), `INFO`(3), `WARNING`(4), `ERROR`(5).

Built-in structured logger:

```python
from tensorlake.applications import Logger

logger = Logger.get_logger(module="my_app")
logger.info("User logged in", user_id=123)        # structlog-style kwargs
logger.error("An error occurred", exc_info=True)  # log exceptions as structured data
logger = logger.bind(user_id=123)                 # bind context to all subsequent logs
```

`structlog` is also supported — the recommended config uses `add_log_level`, `TimeStamper(fmt="iso", key="timestamp", utc=True)`, `StackInfoRenderer()`, `dict_tracebacks`, and `JSONRenderer()`. To set a level manually without a logger, print a JSON object containing a `level` attribute:

```python
print('{"level": "DEBUG", "message": "Debugging the payload"}')
```

**Retention:** 7 days by default, extendable to 30 days or 1 year — contact `support@tensorlake.ai`.

**Logs API:** `GET https://api.tensorlake.ai/applications/{application}/logs`

Response entries carry `timestamp`, `uuid`, `namespace`, `application`, `body`, `level`, and `logAttributes` (a JSON **string**), plus a top-level `nextToken`.

| Parameter | Type | Description |
|---|---|---|
| `requestId` | string | Filter by request IDs |
| `function` | string | Filter by function names |
| `functionExecutor` | string | Filter by function executor containers |
| `functionRunId` | string | Filter by function runs |
| `allocationId` | string | Filter by allocations |
| `level` | integer | Filter by log level (1–5) |
| `events` | integer | Filter system and application events (e.g. `events=3` to filter system events out) |
| `gate` | `and` \| `or` | Logic for combining filters (default `and`) |
| `head` | integer | Number of logs in ascending order (default 100) |
| `tail` | integer | Number of logs in descending order (default 100) |
| `nextToken` | string | Pagination token from the previous response |

Filter parameters can be **repeated** (`?level=2&level=3`); repeats are combined using `gate`. Logs are returned newest-first by default. System and application lifecycle events are included by default.

## Sandboxes and Orchestration

Two architectural patterns, chosen by **where the agent runs**:

**Pattern 1 — Agent in sandbox.** This is what `@function()` already is: your agent code runs inside an isolated container with its own filesystem, dependencies, and resource limits, reading/writing files and executing code within the container boundary. Use it when the agent and execution environment are tightly coupled, the agent needs persistent filesystem access across tool calls, or you want production to mirror local development. Trade-offs: API keys must live inside the container, and updating agent logic requires redeploying the function.

**Pattern 2 — Sandbox as tool.** The agent runs in a `@function()` and creates Tensorlake sandboxes on demand for code execution. Use it when executing untrusted or LLM-generated code, when API keys should stay outside the execution environment, when you want many parallel sandboxes, or when the agent must create, inspect, and tear down environments dynamically. Trade-offs: network latency per execution, and two layers of containers.

```python
@application()
@function(image=agent_image, timeout=1800)
def coding_agent(task: str) -> str:
    from tensorlake.sandbox import Sandbox

    sandbox = Sandbox.create(
        image="tensorlake/ubuntu-minimal",
        cpus=1.0,
        memory_mb=1024,
        timeout_secs=60,
    )
    try:
        result = sandbox.run("python", ["-c", generated_code])
        return result.stdout
    finally:
        sandbox.terminate()
```

> The docs' Pattern 2 snippet uses `sandbox.execute(...)`, `result.output`, and `sandbox_client.delete(...)`. Those symbols do not exist in the Sandbox SDK reference — use `sandbox.run(...)`, `result.stdout`, and `sandbox.terminate()` as above. See [sandbox_sdk.md](sandbox_sdk.md).

For durable state that outlives both the function container and the sandbox, mount a Cloud Volume or Git repository — see [volumes_and_git.md](volumes_and_git.md).
