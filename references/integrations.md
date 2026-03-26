# TensorLake Integration Patterns

Integration examples for using TensorLake as infrastructure alongside LLM providers and agent frameworks.

## Table of Contents

- [OpenAI + TensorLake Applications](#openai--tensorlake-applications)
- [Anthropic + TensorLake Applications](#anthropic--tensorlake-applications)
- [LangChain + TensorLake Sandbox](#langchain--tensorlake-sandbox)
- [LangChain + TensorLake DocumentAI](#langchain--tensorlake-documentai)
- [CrewAI + TensorLake Sandbox](#crewai--tensorlake-sandbox)
- [LlamaIndex + TensorLake DocumentAI](#llamaindex--tensorlake-documentai)
- [OpenAI Function Calling + TensorLake Sandbox](#openai-function-calling--tensorlake-sandbox)
- [Multi-Agent Orchestration](#multi-agent-orchestration)

## OpenAI + TensorLake Applications

Use TensorLake to orchestrate multi-step LLM pipelines with OpenAI:

```python
from tensorlake.applications import application, function, run_local_application, Image

llm_image = Image(base_image="python:3.11-slim").run("pip install openai")

@application()
@function()
def research_pipeline(topics: list[str]) -> list[dict]:
    drafts = research.map(topics)
    reviewed = review.map(drafts)
    return list(reviewed)

@function(image=llm_image, secrets=["OPENAI_API_KEY"])
def research(topic: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Research this topic: {topic}"}],
    ).choices[0].message.content

@function(image=llm_image, secrets=["OPENAI_API_KEY"])
def review(draft: str) -> dict:
    from openai import OpenAI
    client = OpenAI()
    feedback = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Review and improve:\n{draft}"}],
    ).choices[0].message.content
    return {"draft": draft, "review": feedback}
```

## Anthropic + TensorLake Applications

```python
from tensorlake.applications import application, function, Image

claude_image = Image(base_image="python:3.11-slim").run("pip install anthropic")

@application()
@function()
def analyze_documents(docs: list[str]) -> list[dict]:
    analyses = analyze.map(docs)
    summary = synthesize.reduce(analyses, initial="")
    return {"analyses": list(analyses), "summary": summary}

@function(image=claude_image, secrets=["ANTHROPIC_API_KEY"])
def analyze(doc: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Analyze this document:\n{doc}"}],
    )
    return {"document": doc[:100], "analysis": response.content[0].text}

@function(image=claude_image, secrets=["ANTHROPIC_API_KEY"])
def synthesize(accumulated: str, analysis: dict) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Previous summary:\n{accumulated}\n\nNew analysis:\n{analysis['analysis']}\n\nUpdate the summary."}],
    )
    return response.content[0].text
```

## LangChain + TensorLake Sandbox

Expose TensorLake Sandbox as a LangChain tool for code execution:

```python
from langchain_core.tools import tool
from tensorlake.sandbox import SandboxClient

@tool
def execute_python(code: str) -> str:
    """Execute Python code in a secure TensorLake sandbox. Use for data analysis, calculations, or running scripts."""
    client = SandboxClient()
    with client.create_and_connect(
        image="python:3.11-slim",
        memory_mb=2048,
        timeout_secs=120,
    ) as sandbox:
        sandbox.write_file("/tmp/script.py", code.encode())
        result = sandbox.run("python", args=["/tmp/script.py"])
        if result.exit_code != 0:
            return f"Error (exit {result.exit_code}):\n{result.stderr}"
        return result.stdout

# Use with any LangChain agent
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4o")
agent = create_react_agent(llm, [execute_python])
result = agent.invoke({"messages": [{"role": "user", "content": "Calculate the first 20 fibonacci numbers"}]})
```

### Persistent Sandbox with LangChain

For multi-turn agents that need state across tool calls:

```python
from langchain_core.tools import tool
from tensorlake.sandbox import SandboxClient

client = SandboxClient()
sandbox = client.create_and_connect(
    image="python:3.11-slim",
    timeout_secs=600,
)
sandbox.__enter__()  # Keep sandbox alive across calls

@tool
def run_python(code: str) -> str:
    """Execute Python in a persistent sandbox. Variables and files persist between calls."""
    sandbox.write_file("/tmp/script.py", code.encode())
    result = sandbox.run("python", args=["/tmp/script.py"])
    if result.exit_code != 0:
        return f"Error:\n{result.stderr}"
    return result.stdout

@tool
def upload_file(filename: str, content: str) -> str:
    """Upload a file to the sandbox."""
    sandbox.write_file(f"/tmp/{filename}", content.encode())
    return f"Uploaded /tmp/{filename}"

@tool
def install_packages(packages: str) -> str:
    """Install Python packages in the sandbox. Pass space-separated package names."""
    result = sandbox.run("pip", args=["install"] + packages.split())
    if result.exit_code != 0:
        return f"Install failed:\n{result.stderr}"
    return f"Installed: {packages}"
```

## LangChain + TensorLake DocumentAI

Use TensorLake DocumentAI as a LangChain document loader:

```python
from langchain_core.documents import Document
from tensorlake.documentai import DocumentAI, ParsingOptions, ChunkingStrategy

def load_documents_with_tensorlake(file_paths: list[str]) -> list[Document]:
    """Load and chunk documents using TensorLake DocumentAI for LangChain RAG."""
    doc_ai = DocumentAI()
    documents = []
    for path in file_paths:
        result = doc_ai.parse_and_wait(
            file=path,
            parsing_options=ParsingOptions(
                chunking_strategy=ChunkingStrategy.SEMANTIC,
            ),
        )
        for chunk in result.chunks:
            documents.append(Document(
                page_content=chunk.content,
                metadata={"source": path, "chunk_index": chunk.chunk_index},
            ))
    return documents

# Use in a RAG pipeline
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

docs = load_documents_with_tensorlake(["report.pdf", "manual.pdf"])
vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
```

## CrewAI + TensorLake Sandbox

Use TensorLake Sandbox as a CrewAI tool:

```python
from crewai import Agent, Task, Crew
from crewai.tools import tool
from tensorlake.sandbox import SandboxClient

@tool
def sandbox_execute(code: str) -> str:
    """Execute Python code in a secure TensorLake sandbox for data analysis and computation."""
    client = SandboxClient()
    with client.create_and_connect() as sandbox:
        sandbox.write_file("/tmp/task.py", code.encode())
        result = sandbox.run("python", args=["/tmp/task.py"])
        if result.exit_code != 0:
            return f"Error: {result.stderr}"
        return result.stdout

analyst = Agent(
    role="Data Analyst",
    goal="Analyze data and produce insights",
    tools=[sandbox_execute],
)
task = Task(
    description="Analyze the sales data and find the top 5 products",
    agent=analyst,
)
crew = Crew(agents=[analyst], tasks=[task])
result = crew.kickoff()
```

## LlamaIndex + TensorLake DocumentAI

Use TensorLake DocumentAI as a LlamaIndex reader:

```python
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode
from tensorlake.documentai import DocumentAI, ParsingOptions, ChunkingStrategy

def tensorlake_reader(file_paths: list[str]) -> list[TextNode]:
    """Parse documents with TensorLake and return LlamaIndex nodes."""
    doc_ai = DocumentAI()
    nodes = []
    for path in file_paths:
        result = doc_ai.parse_and_wait(
            file=path,
            parsing_options=ParsingOptions(
                chunking_strategy=ChunkingStrategy.SEMANTIC,
            ),
        )
        for chunk in result.chunks:
            nodes.append(TextNode(
                text=chunk.content,
                metadata={"source": path, "chunk_index": chunk.chunk_index},
            ))
    return nodes

nodes = tensorlake_reader(["quarterly_report.pdf"])
index = VectorStoreIndex(nodes)
query_engine = index.as_query_engine()
```

## OpenAI Function Calling + TensorLake Sandbox

Wire TensorLake Sandbox directly into OpenAI's tool-use loop:

```python
import json
from openai import OpenAI
from tensorlake.sandbox import SandboxClient

tools = [{
    "type": "function",
    "function": {
        "name": "execute_code",
        "description": "Execute Python code in a secure sandbox",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        },
    },
}]

def handle_tool_call(code: str) -> str:
    client = SandboxClient()
    with client.create_and_connect() as sandbox:
        sandbox.write_file("/tmp/run.py", code.encode())
        result = sandbox.run("python", args=["/tmp/run.py"])
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"

# Agent loop
client = OpenAI()
messages = [{"role": "user", "content": "Calculate the mean and std of [23, 45, 12, 67, 34, 89, 11]"}]

while True:
    response = client.chat.completions.create(model="gpt-4o", messages=messages, tools=tools)
    msg = response.choices[0].message
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            output = handle_tool_call(args["code"])
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
    else:
        print(msg.content)
        break
```

## Multi-Agent Orchestration

Use TensorLake Applications to orchestrate multiple specialized agents that each use different LLMs:

```python
from tensorlake.applications import application, function, Image
from tensorlake.sandbox import SandboxClient

research_image = Image(base_image="python:3.11-slim").run("pip install anthropic")
coding_image = Image(base_image="python:3.11-slim").run("pip install openai")

@application()
@function()
def multi_agent_pipeline(task: str) -> dict:
    plan = planner(task)
    code = coder(plan)
    output = executor(code)
    verdict = reviewer(task, output)
    return {"plan": plan, "code": code, "output": output, "verdict": verdict}

@function(image=research_image, secrets=["ANTHROPIC_API_KEY"])
def planner(task: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    return client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1024,
        messages=[{"role": "user", "content": f"Break this task into steps:\n{task}"}],
    ).content[0].text

@function(image=coding_image, secrets=["OPENAI_API_KEY"])
def coder(plan: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Write Python code for this plan:\n{plan}"}],
    ).choices[0].message.content

@function(timeout=120)
def executor(code: str) -> str:
    client = SandboxClient()
    with client.create_and_connect() as sandbox:
        sandbox.write_file("/tmp/task.py", code.encode())
        result = sandbox.run("python", args=["/tmp/task.py"])
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"

@function(image=research_image, secrets=["ANTHROPIC_API_KEY"])
def reviewer(task: str, output: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    return client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=512,
        messages=[{"role": "user", "content": f"Task: {task}\nOutput: {output}\nDoes the output correctly solve the task? Explain."}],
    ).content[0].text
```
