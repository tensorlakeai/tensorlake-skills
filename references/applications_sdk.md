# TensorLake Applications SDK Reference

## Imports

```python
from tensorlake.applications import (
    application, function, cls,
    run_local_application, run_remote_application,
    Future, RETURN_WHEN,
    RequestContext, File, Image, Retries,
    TensorlakeError, RequestError, FunctionError,
    Logger,
)
```

## Decorators

### @application()

Entry point decorator. Must wrap a function also decorated with `@function()`.

```python
@application(
    tags: Dict[str, str] = {},
    retries: Retries = Retries(),
    region: Literal["us-east-1", "eu-west-1"] | None = None,
)
```

### @function()

Decorates individual callable functions.

```python
@function(
    description: str = "",
    cpu: float = 1.0,              # CPU cores
    memory: float = 1.0,           # GB
    ephemeral_disk: float = 2.0,   # GB
    gpu: None | str | List[str] = None,
    timeout: int = 300,            # seconds
    image: Image = Image(),
    secrets: List[str] = [],
    retries: Retries | None = None,
    region: str | None = None,
    warm_containers: int | None = None,
    min_containers: int | None = None,
    max_containers: int | None = None,
)
```

### @cls()

Marks a class whose methods can be decorated with `@function()`.

```python
@cls(init_timeout: int | None = None)
class MyProcessor:
    def __init__(self):
        self.model = load_model()

    @function(gpu="nvidia-t4")
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

## Map & Reduce

```python
# Map: apply function to each item in parallel
results = my_function.map([item1, item2, item3])

# Non-blocking map
future = my_function.future.map([item1, item2, item3])
results = future.result()

# Reduce: fold items with function
total = add.reduce([1, 2, 3, 4, 5], initial=0)

# Non-blocking reduce
future = add.future.reduce([1, 2, 3, 4, 5], initial=0)
total = future.result()

# Chain: map over a future's result
numbers = get_numbers.future()
squared = square.map(numbers)  # Waits for get_numbers, then maps
```

## Future API

```python
future.run()                          # Start immediately
future.run_later(delay=5.0)           # Schedule with delay
future.result(timeout=None)           # Block for result
future.done()                         # Check completion
future.exception()                    # Get error if failed

# Wait for multiple futures
done, not_done = Future.wait(
    futures,
    timeout=None,
    return_when=RETURN_WHEN.ALL_COMPLETED  # or FIRST_COMPLETED, FIRST_FAILURE
)
```

## Running Applications

```python
# Local (dev/test, in-process, no containers)
request = run_local_application(my_app, *args, **kwargs)
output = request.output()  # Blocks, raises on failure

# Remote (TensorLake Cloud, containers, auto-scaling)
request = run_remote_application("app_name", *args, **kwargs)
# or
request = run_remote_application(my_app, *args, **kwargs)
output = request.output()
```

## RequestContext

Available only during function execution.

```python
ctx = RequestContext.get()
ctx.request_id                           # str

# Key-value state (scoped to request)
ctx.state.set(key, value)
ctx.state.get(key, default=None)

# Metrics
ctx.metrics.timer(name, value_ms)
ctx.metrics.counter(name, amount=1)

# Progress reporting
ctx.progress.update(current=10, total=100, message="Processing...")
```

## Image Builder

Build custom container images for functions.

```python
img = Image(base_image="python:3.11-slim")
img.run("pip install numpy torch")
img.env("MODEL_PATH", "/models/v1")
img.copy("src", "/app/src")

@function(image=img, gpu="nvidia-t4")
def inference(data: str) -> str:
    import torch
    ...
```

## File Type

```python
file = File(content=b"bytes", content_type="application/pdf")
file.content       # bytes
file.content_type  # str
```

## Retries

```python
@application(retries=Retries(max_retries=3))
@function()
def my_app(): ...

@function(retries=Retries(max_retries=5))  # Override per-function
def risky_step(): ...
```

## Exceptions

| Exception | When |
|---|---|
| `TensorlakeError` | Base class |
| `RequestError` | Explicit request failure (raise to fail) |
| `FunctionError` | Unhandled exception in function |
| `RemoteAPIError` | Cloud API error (.status_code) |
| `SDKUsageError` | Incorrect SDK usage |
| `TimeoutError` | Operation timed out |

## Logger

```python
logger = Logger.get_logger(request_id="123")
logger = logger.bind(user_id="456")
logger.info("message", extra_key="value")
```
