<!--
Source:
  - https://docs.tensorlake.ai/applications/introduction.md
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
  - https://docs.tensorlake.ai/applications/scale-out-queuing.md
  - https://docs.tensorlake.ai/applications/scaling-agents.md
  - https://docs.tensorlake.ai/applications/observability.md
  - https://docs.tensorlake.ai/applications/cron-scheduler.md
  - https://docs.tensorlake.ai/applications/parallel-sub-agents.md
  - https://docs.tensorlake.ai/applications/sandboxes.md
  - https://docs.tensorlake.ai/applications/guides/streaming-progress.md
  - https://docs.tensorlake.ai/applications/guides/logging.md
  - https://docs.tensorlake.ai/applications/guides/autoscaling.md
SDK version: tensorlake 0.4.42
Last verified: 2026-04-08
-->

# TensorLake Applications SDK Reference

## Imports

```python
from tensorlake.applications import (
    application, function, cls,
    run_local_application, run_remote_application,
    get_remote_request,
    Future, RETURN_WHEN,
    RequestContext, Request, File, Image, Retries,
    ReplayMode, RequestError,
)
```

## Decorators

### @application()

Entry point decorator. Must wrap a function also decorated with `@function()`.

```python
@application(
    tags: dict[str, str] = {},
    retries: Retries | None = None,
    region: str | None = None,               # "us-east-1" or "eu-west-1"
)
```

### @function()

Decorates individual callable functions. Each call executes in its own container.

```python
@function(
    description: str = "",
    cpu: float = 1.0,              # 1.0-8.0
    memory: float = 1.0,           # GB, 1.0-32.0
    ephemeral_disk: float = 2.0,   # GB, 2.0-50.0 (SSD at /tmp)
    gpu: str | None = None,        # e.g., "T4", "H100"
    timeout: int = 300,            # seconds, 1-172800 (max 48 hours)
    image: Image = Image(),
    secrets: list[str] = [],
    retries: Retries | int | None = None,
    region: str | None = None,
    warm_containers: int | None = None,   # Pre-warmed for zero cold starts
    max_containers: int | None = None,    # Upper limit, excess queued FIFO
    concurrency: int | None = None,       # Concurrent requests per container
    durable: bool = True,                 # Enable/disable checkpointing
)
```

**Timeout auto-reset**: Calling `ctx.progress.update()` resets the timeout counter. A function can run indefinitely if it continuously sends progress updates.

### @cls()

Marks a class whose methods can be decorated with `@function()`. `__init__(self)` runs once for one-time initialization (no arguments).

```python
@cls()
class MyProcessor:
    def __init__(self):
        self.model = load_model()

    @application()
    @function(gpu="T4")
    def process(self, data: str) -> str:
        return self.model.predict(data)
```

## Calling Functions

```python
# Synchronous (blocks)
result = my_function(arg1, arg2)

# Non-blocking (returns Future)
future = my_function.future(arg1, arg2)
result = future.result()

# Async
result = await my_function.future(arg1, arg2)
```

## Input/Output Serialization

JSON deserialization via type hints. Supported types: `str`, `int`, `float`, `bool`, `list`, `dict`, `set`, `tuple`, `None`, `Any`, `|` (union), Pydantic model classes.

## Map & Reduce

```python
# Map: apply function to each item in parallel
results = my_function.map([item1, item2, item3])

# Non-blocking map
future = my_function.future.map([item1, item2, item3])
results = future.result()

# Reduce: fold items with function (signature: accumulated, next_item -> accumulated)
total = add.reduce([1, 2, 3, 4, 5], 0)

# Non-blocking reduce
future = add.future.reduce([1, 2, 3, 4, 5], 0)
total = future.result()

# Chain: map over a future's result
numbers = get_numbers.future()
squared = square.map(numbers)  # Waits for get_numbers, then maps
```

**Tail call optimization**: Map and reduce Futures can be returned from functions as tail calls. The returning function completes immediately, freeing its container.

## Future API

```python
future = my_function.future(arg1, arg2)
future.run()                          # Start immediately, returns self for chaining
future.result(timeout=None)           # Block for result (raises FunctionError/TimeoutError)
future.done()                         # Check completion (bool)
future.exception                      # Property: TensorlakeError | None

# Async support
await future                          # Via __await__()
coro = future.coroutine()             # Convert to coroutine (call before .run())

# Wait for multiple futures
done, not_done = Future.wait(
    futures,
    timeout=None,
    return_when=RETURN_WHEN.ALL_COMPLETED,
    # ALL_COMPLETED | FIRST_COMPLETED | FIRST_EXCEPTION
)
```

Futures passed as arguments to other functions are auto-resolved:

```python
a = double.future(x)
b = double.future(x + 1)
result = add(a, b)  # add waits for a and b automatically
```

## Async Functions

An `async` Tensorlake function returns a coroutine when called:

```python
@function()
async def fetch_data(url: str) -> dict: ...

# Usage patterns
result = await fetch_data(url)                          # blocks
task = asyncio.create_task(fetch_data(url))             # background
results = await asyncio.gather(fetch_a(x), fetch_b(y))  # parallel

# Async map/reduce
doubled = await double.map(numbers)
total = await add.reduce(doubled)
```

Returning a coroutine or Future as a tail call frees the container immediately.

Calling sync from async: use `.future()` to avoid blocking the event loop. Calling async from sync: use `.future().result()`.

## Running Applications

```python
# Local (dev/test, in-process, no containers)
request: Request = run_local_application(my_app, *args, **kwargs)
output = request.output()  # Blocks, raises on failure

# Remote (TensorLake Cloud, containers, auto-scaling)
request: Request = run_remote_application(my_app, *args, **kwargs)
# or by name:
request: Request = run_remote_application("app_name", *args, **kwargs)
print(request.id)    # Request identifier
output = request.output()
```

```bash
# Deploy before running remotely
tl deploy path/to/app.py
```

## Durable Execution

Every `@function()` call is automatically checkpointed. On replay, previously successful calls return cached outputs instantly.

```python
from tensorlake.applications import Request, get_remote_request, ReplayMode

request: Request = get_remote_request(application_name, request_id)
request.replay()                                          # Adaptive mode (default)
request.replay(upgrade_to_latest_version=True)
request.replay(mode=ReplayMode.STRICT)                    # Fails if new calls added
request.replay(mode=ReplayMode.ADAPTIVE)                  # Allows new calls
```

Disable checkpointing for non-deterministic functions:

```python
@function(durable=False)
def get_current_weather() -> str: ...  # Always re-executes during replays
```

## RequestContext

Available only during function execution.

```python
ctx: RequestContext = RequestContext.get()
ctx.request_id                           # str

# Key-value state (scoped to request)
ctx.state.set(key, value)
ctx.state.get(key, default=None)

# Metrics
ctx.metrics.timer(name, value)
ctx.metrics.counter(name, value)

# Progress reporting (also resets timeout)
ctx.progress.update(current=10, total=100, message="Processing...")
```

## Image Builder

Build custom container images for functions.

```python
img = (
    Image(name="my-image", base_image="python:3.11-slim")
    .run("pip install numpy torch")
)

@function(image=img, gpu="T4")
def inference(data: str) -> str:
    import torch  # Must import inside function body
    ...
```

**Important**: Packages installed in the image must be imported inside the function body, not at module level.

Default base image: `python:{LOCAL_PYTHON_VERSION}-slim-bookworm`

Image builder methods (chainable): `.run(command)`

## File Type

```python
file = File(content=b"bytes", content_type="application/pdf")
file.content       # bytes
file.content_type  # str
```

## Retries

```python
from tensorlake.applications import Retries

@function(retries=Retries(max_retries=3))
def risky_step(): ...

# Shorthand
@function(retries=3)
def risky_step(): ...
```

Uses exponential backoff. Rate limit errors, timeouts, and exceptions trigger retries. Nested calls that already succeeded use cached checkpoints.

**Tip**: Disable client-level retries (e.g., OpenAI's `max_retries=0`) when using Tensorlake retries.

## Scaling

```python
@function(warm_containers=2, max_containers=20, concurrency=5)
def agent(prompt: str) -> str: ...
```

- `warm_containers`: Pre-warmed containers for zero cold-start latency
- `max_containers`: Upper limit; excess requests queued FIFO
- `concurrency`: Concurrent requests per container
- Default (no params): scales dynamically from zero, no upper limit

## Cron Scheduler

Schedule periodic application runs via REST API:

```python
import requests, base64, json

payload = {"cron_expression": "0 * * * *"}
input_data = json.dumps({"report_type": "daily"}).encode()
payload["input_base64"] = base64.b64encode(input_data).decode()

response = requests.post(
    f"https://api.tensorlake.ai/applications/{application}/cron-schedules",
    json=payload,
    headers={"Authorization": "Bearer TENSORLAKE_API_KEY"},
)
```

Minimum interval: 60 seconds. Max 100 schedules per application.

## Exceptions

| Exception | When |
|---|---|
| `RequestError` | Raise to explicitly fail a request |
| `TensorlakeError` | Base class (on Future.exception) |
| `ReplayError` | Strict replay encounters new function calls |

## Secrets

```bash
tl secrets set OPENAI_API_KEY=<value>
tl secrets list
tl secrets unset OPENAI_API_KEY
```

```python
@function(secrets=["OPENAI_API_KEY"])
def my_func() -> str:
    key = os.environ["OPENAI_API_KEY"]
```

Redeploy applications after updating secrets. AES-256-GCM encryption, in-memory decryption only during execution.

## Observability

Every `@function()` call is automatically traced. The dashboard shows function call sequence, timing (including cold starts), dependency visualization, and status. Use standard Python `logging` module; logs are captured automatically.

```python
from tensorlake.applications import Logger

logger = Logger.get_logger(module="my_app")
logger.info("starting run", log_attributes={"request_id": "req-123"})
```
