<!--
Source:
  - https://docs.tensorlake.ai/integrations/overview.md
  - https://docs.tensorlake.ai/integrations/langchain.md
  - https://docs.tensorlake.ai/integrations/chroma.md
  - https://docs.tensorlake.ai/integrations/qdrant.md
  - https://docs.tensorlake.ai/integrations/databricks.md
  - https://docs.tensorlake.ai/integrations/motherduck.md
SDK version: tensorlake 0.4.39
Last verified: 2026-04-07
-->

# TensorLake Integration Patterns

Integration examples for using TensorLake as infrastructure alongside LLM providers, agent frameworks, and data platforms.

## Table of Contents

- [LangChain + TensorLake DocumentAI (langchain-tensorlake)](#langchain--tensorlake-documentai-langchain-tensorlake)
- [OpenAI + TensorLake Applications](#openai--tensorlake-applications)
- [Anthropic + TensorLake Applications](#anthropic--tensorlake-applications)
- [LangChain + TensorLake Sandbox](#langchain--tensorlake-sandbox)
- [LangChain + TensorLake DocumentAI (Custom)](#langchain--tensorlake-documentai-custom)
- [OpenAI Function Calling + TensorLake Sandbox](#openai-function-calling--tensorlake-sandbox)
- [Multi-Agent Orchestration](#multi-agent-orchestration)
- [ChromaDB + TensorLake DocumentAI](#chromadb--tensorlake-documentai)
- [Qdrant + TensorLake DocumentAI](#qdrant--tensorlake-documentai)
- [Databricks + TensorLake DocumentAI](#databricks--tensorlake-documentai)
- [MotherDuck + TensorLake DocumentAI](#motherduck--tensorlake-documentai)

## LangChain + TensorLake DocumentAI (langchain-tensorlake)

The official `langchain-tensorlake` package provides a ready-made LangChain tool:

```bash
pip install langchain-tensorlake
```

```python
from langchain_tensorlake import document_markdown_tool
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model="openai:gpt-4o-mini",
    tools=[document_markdown_tool],
    prompt="I have a document that needs to be parsed...",
    name="financial-analyst",
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "What is the quarterly revenue based on this file? https://example.com/report.pdf"
    }]
})
print(result["messages"][-1].content)
```

Direct SDK usage with LangChain vectorstore:

```python
from tensorlake.documentai import DocumentAI, ParsingOptions, ChunkingStrategy
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

doc_ai = DocumentAI()
file_id = doc_ai.upload("contract.pdf")

result = doc_ai.parse_and_wait(
    file_id=file_id,
    parsing_options=ParsingOptions(chunking_strategy=ChunkingStrategy.SECTION),
)

documents = [chunk.content for chunk in result.chunks]
vectorstore = Chroma.from_texts(documents, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
```

## OpenAI + TensorLake Applications

Use TensorLake to orchestrate multi-step LLM pipelines with OpenAI:

```python
from tensorlake.applications import application, function, run_local_application, Image

llm_image = Image(name="llm-openai", base_image="python:3.11-slim").run("pip install openai")

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

claude_image = Image(name="llm-anthropic", base_image="python:3.11-slim").run("pip install anthropic")

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
        model="claude-sonnet-4-20250514", max_tokens=1024,
        messages=[{"role": "user", "content": f"Analyze this document:\n{doc}"}],
    )
    return {"document": doc[:100], "analysis": response.content[0].text}

@function(image=claude_image, secrets=["ANTHROPIC_API_KEY"])
def synthesize(accumulated: str, analysis: dict) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1024,
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
    sandbox = client.create_and_connect(memory_mb=2048, timeout_secs=120)
    try:
        result = sandbox.run("python", ["-c", code])
        if result.exit_code != 0:
            return f"Error (exit {result.exit_code}):\n{result.stderr}"
        return result.stdout
    finally:
        sandbox.close()

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
sandbox = client.create_and_connect(timeout_secs=600)

@tool
def run_python(code: str) -> str:
    """Execute Python in a persistent sandbox. Variables and files persist between calls."""
    sandbox.write_file("/tmp/script.py", code.encode())
    result = sandbox.run("python", ["/tmp/script.py"])
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
    result = sandbox.run("pip", ["install"] + packages.split())
    if result.exit_code != 0:
        return f"Install failed:\n{result.stderr}"
    return f"Installed: {packages}"
```

## LangChain + TensorLake DocumentAI (Custom)

Use TensorLake DocumentAI as a custom LangChain document loader:

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
                chunking_strategy=ChunkingStrategy.SECTION,
            ),
        )
        for chunk in result.chunks:
            documents.append(Document(
                page_content=chunk.content,
                metadata={"source": path, "page_number": chunk.page_number},
            ))
    return documents

# Use in a RAG pipeline
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

docs = load_documents_with_tensorlake(["report.pdf", "manual.pdf"])
vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
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
    sandbox = client.create_and_connect()
    try:
        result = sandbox.run("python", ["-c", code])
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"
    finally:
        sandbox.close()

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

research_image = Image(name="agent-anthropic", base_image="python:3.11-slim").run("pip install anthropic")
coding_image = Image(name="agent-openai", base_image="python:3.11-slim").run("pip install openai")

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
    sandbox = client.create_and_connect()
    try:
        result = sandbox.run("python", ["-c", code])
        return result.stdout if result.exit_code == 0 else f"Error: {result.stderr}"
    finally:
        sandbox.close()

@function(image=research_image, secrets=["ANTHROPIC_API_KEY"])
def reviewer(task: str, output: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    return client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=512,
        messages=[{"role": "user", "content": f"Task: {task}\nOutput: {output}\nDoes the output correctly solve the task? Explain."}],
    ).content[0].text
```

## ChromaDB + TensorLake DocumentAI

Parse documents with TensorLake and store in ChromaDB with citation tracking:

```bash
pip install tensorlake chromadb
```

```python
import json
import chromadb
from chromadb.utils import embedding_functions
from tensorlake.documentai import DocumentAI, ParseStatus

doc_ai = DocumentAI()
file_id = doc_ai.upload("research_paper.pdf")
result = doc_ai.parse_and_wait(file_id=file_id)
assert result.status == ParseStatus.SUCCESSFUL

# Build citation-aware chunks from page fragments
def build_citation_chunks(result, file_name):
    sections = []
    current_section = None
    for page in result.pages:
        for fragment in page.page_fragments:
            content = fragment.content.content.strip()
            bbox = fragment.bbox
            if fragment.fragment_type == "section_header":
                if current_section:
                    sections.append(current_section)
                current_section = [{"page_number": page.page_number, "text": content, "bbox": bbox}]
            elif content and current_section is not None:
                current_section.append({"page_number": page.page_number, "text": content, "bbox": bbox})
    if current_section:
        sections.append(current_section)

    chunks, metadatas, ids = [], [], []
    for sec_idx, section in enumerate(sections, start=1):
        citation_map = {}
        text_lines = []
        for elem_idx, element in enumerate(section, start=1):
            anchor_id = f"S{sec_idx}.{elem_idx}"
            text_lines.append(f"<c id={anchor_id}>{element['text']}</c>")
            citation_map[anchor_id] = {"page_number": element["page_number"], "bbox": element["bbox"]}
        chunks.append("\n".join(text_lines))
        metadatas.append({"file": file_name, "citations": json.dumps(citation_map)})
        ids.append(f"section-{sec_idx}")
    return chunks, metadatas, ids

client = chromadb.Client()
collection = client.create_collection(
    name="citation_aware_rag",
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-3-small"
    ),
)
chunks, metadatas, ids = build_citation_chunks(result, "research_paper.pdf")
collection.add(documents=chunks, metadatas=metadatas, ids=ids)
```

## Qdrant + TensorLake DocumentAI

Parse documents and store with rich metadata in Qdrant:

```bash
pip install tensorlake qdrant-client sentence-transformers
```

```python
from tensorlake.documentai import (
    DocumentAI, ParsingOptions, StructuredExtractionOptions,
    EnrichmentOptions, ChunkingStrategy, TableParsingFormat, TableOutputMode,
)
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from uuid import uuid4

doc_ai = DocumentAI()

parsing_options = ParsingOptions(
    chunking_strategy=ChunkingStrategy.SECTION,
    table_parsing_strategy=TableParsingFormat.TSR,
    table_output_mode=TableOutputMode.MARKDOWN,
)

enrichment_options = EnrichmentOptions(
    figure_summarization=True,
    table_summarization=True,
)

parse_id = doc_ai.parse(
    "https://example.com/paper.pdf",
    parsing_options,
    structured_extraction_options=[StructuredExtractionOptions(
        schema_name="ResearchPaper",
        json_schema={
            "title": "ResearchPaper",
            "type": "object",
            "properties": {
                "authors": {"type": "array", "items": {"type": "string"}},
                "publication_year": {"type": "integer"},
            },
        },
    )],
    enrichment_options=enrichment_options,
)
result = doc_ai.wait_for_completion(parse_id)

# Store in Qdrant
model = SentenceTransformer("all-MiniLM-L6-v2")
qdrant = QdrantClient(":memory:")
qdrant.create_collection("papers", vectors_config=models.VectorParams(
    size=model.get_sentence_embedding_dimension(), distance=models.Distance.COSINE,
))

metadata = result.structured_data[0].data if result.structured_data else {}
points = []

for chunk in result.chunks:
    points.append(models.PointStruct(
        id=str(uuid4()),
        vector=model.encode(chunk.content).tolist(),
        payload={**metadata, "content": chunk.content, "type": "text"},
    ))

for page in result.pages:
    for fragment in page.page_fragments:
        if fragment.fragment_type == "table" and fragment.content.summary:
            points.append(models.PointStruct(
                id=str(uuid4()),
                vector=model.encode(fragment.content.summary).tolist(),
                payload={**metadata, "content": fragment.content.summary, "type": "table", "page": page.page_number},
            ))

qdrant.upsert(collection_name="papers", points=points)
qdrant.create_payload_index("papers", "authors", "keyword")

# Filtered search
hits = qdrant.query_points("papers",
    query=model.encode("main results").tolist(),
    query_filter=models.Filter(must=[
        models.FieldCondition(key="authors", match=models.MatchValue(value="Author Name"))
    ]),
    limit=5,
).points
```

## Databricks + TensorLake DocumentAI

Extract structured data from documents and load into Databricks tables:

```bash
pip install tensorlake databricks-sql-connector pandas pyarrow
```

```python
import pandas as pd
from pydantic import BaseModel, Field
from tensorlake.documentai import DocumentAI, StructuredExtractionOptions, ParseStatus

class CompanyInfo(BaseModel):
    company_name: str = Field(description="Name of the company")
    revenue: str = Field(description="Annual revenue")
    industry: str = Field(description="Primary industry")

doc_ai = DocumentAI()
parse_id = doc_ai.extract(
    file="https://example.com/company-report.pdf",
    structured_extraction_options=[
        StructuredExtractionOptions(schema_name="CompanyInfo", json_schema=CompanyInfo),
    ],
)
result = doc_ai.wait_for_completion(parse_id)

records = []
if result.status == ParseStatus.SUCCESSFUL:
    for data in result.structured_data:
        records.append(data.data)

df = pd.DataFrame(records)
# spark.createDataFrame(df).write.mode("append").saveAsTable("companies.company_info")
```

## MotherDuck + TensorLake DocumentAI

Extract structured data and query with DuckDB/MotherDuck:

```bash
pip install tensorlake duckdb==1.3.2
```

```python
import duckdb
import pandas as pd
from pydantic import BaseModel, Field
from tensorlake.documentai import DocumentAI, StructuredExtractionOptions

class CompanyInfo(BaseModel):
    company_name: str = Field(description="Name of the company")
    revenue: str = Field(description="Annual revenue")
    industry: str = Field(description="Primary industry")

doc_ai = DocumentAI()
result = doc_ai.parse_and_wait(
    file="https://example.com/company-report.pdf",
    structured_extraction_options=[
        StructuredExtractionOptions(schema_name="CompanyInfo", json_schema=CompanyInfo)
    ],
)

data = result.structured_data[0].data
df = pd.DataFrame([data])

con = duckdb.connect("md:my_database")  # MotherDuck connection
con.execute("CREATE OR REPLACE TABLE companies AS SELECT * FROM df")
print(con.execute("SELECT * FROM companies").fetchdf())
```
