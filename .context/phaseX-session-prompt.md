# Phase X Session Prompt — pod-memory (ChromaDB Layer)

Copy this entire prompt as the first message in a new Claude Code session.
It contains everything needed to build Phase X. Do NOT ask the agent to read
the full codebase — all relevant context is here.

---

## What you are building

**`packages/pod-memory/`** — a FastAPI service that gives the Architect agent
semantic memory of the target repo's existing code. It wraps ChromaDB and exposes
three HTTP endpoints. It runs on port **8000**.

This is Phase X of Agentic DevStudio. Phases A and B are complete. Do not touch
any other package. The only file outside `packages/pod-memory/` you will edit is
`packages/pod-brain/pod_brain/agents/architect.py` — one small addition to inject
ChromaDB query results into the Architect's context.

---

## Architecture decision (read this fully)

See `.context/decisions/00X-pod-memory-architecture.md` for the full ADR.
Key points:

- pod-memory is a **FastAPI** service (not MCP). pod-brain calls it via `httpx`.
- Three endpoints: `POST /index`, `POST /query`, `DELETE /index`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (local, no API key)
- ChromaDB runs embedded (same process), persisted to `POD_MEMORY_CHROMA_PATH`
- Config via `POD_MEMORY_*` env vars (pydantic-settings, same pattern as pod-brain)

---

## Files to create

```
packages/pod-memory/
├── pyproject.toml
└── pod_memory/
    ├── __init__.py
    ├── config.py
    ├── server.py
    ├── indexer.py
    ├── retriever.py
    └── routes/
        ├── __init__.py
        └── memory.py
```

### `pyproject.toml`

```toml
[project]
name = "pod-memory"
version = "0.1.0"
description = "ChromaDB semantic memory layer for target repo code"
requires-python = ">=3.12"
dependencies = [
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.2.0", "pytest-asyncio>=0.23.0", "httpx>=0.27.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["pod_memory"]
```

### `config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class PodMemorySettings(BaseSettings):
    chroma_path: str = "./chroma_data"       # where ChromaDB persists to disk
    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "target-repo"
    chunk_size: int = 400                    # tokens per chunk (approx chars/4)
    chunk_overlap: int = 50
    port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="POD_MEMORY_", extra="ignore")

settings = PodMemorySettings()
```

### `indexer.py` — key logic

```python
# Walk every file in repo_path, skip binary/hidden files
# Chunk each file's text into overlapping windows of ~chunk_size*4 chars
# Upsert into ChromaDB with metadata: {path, repo, language}
# ID format: f"{repo_id}::{relative_path}::{chunk_index}"
# Use chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction
```

Files to skip: `.git/`, `node_modules/`, `__pycache__/`, `*.pyc`, binary files
(detect via reading first 8192 bytes and checking for null bytes).

### `retriever.py` — key logic

```python
# query(repo_id, text, n_results=5) → list[dict]
# collection.query(query_texts=[text], n_results=n_results, where={"repo": repo_id})
# Return: [{"path": ..., "content": ..., "distance": ...}]
```

### `routes/memory.py` — endpoints

```python
POST /index
  body: {"repo_path": "/abs/path", "repo_id": "org/repo"}
  action: calls indexer.index_repo(), returns {"indexed": N, "repo_id": ...}

POST /query
  body: {"repo_id": "org/repo", "query": "auth service", "n_results": 5}
  action: calls retriever.query(), returns {"results": [...]}

DELETE /index
  body: {"repo_id": "org/repo"}
  action: deletes all documents with metadata.repo == repo_id
```

### `server.py`

FastAPI app with lifespan that initialises the ChromaDB client and embedding
function once at startup (they are expensive to construct). Store them on
`app.state` so routes can access via `request.app.state`.

---

## Connection point with pod-brain (the ONLY file to edit outside pod-memory)

**File:** `packages/pod-brain/pod_brain/agents/architect.py`

The architect currently has a `chroma_url = settings.chroma_url` placeholder.
Replace it with a real pre-call to pod-memory's `/query` endpoint:

```python
async with httpx.AsyncClient() as client:
    r = await client.post(
        f"{settings.chroma_url}/query",
        json={"repo_id": state["target_repo"], "query": state["task"], "n_results": 5},
        timeout=10.0,
    )
    r.raise_for_status()
    context_chunks = r.json()["results"]
```

Inject `context_chunks` into the system prompt as a "Existing codebase context"
section before the Architect LLM call. If the request fails (pod-memory not
running), catch the exception and continue with empty context — pod-memory is
optional infrastructure.

---

## Environment variables to add to `.env.example`

```bash
# ── pod-memory (ChromaDB layer) ──────────────────────────────────────────────
POD_MEMORY_CHROMA_PATH=./chroma_data
POD_MEMORY_EMBEDDING_MODEL=all-MiniLM-L6-v2
POD_MEMORY_COLLECTION_NAME=target-repo
POD_MEMORY_PORT=8000
```

---

## How to run

```bash
uv sync --all-packages

# Start pod-memory
uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000

# Index a target repo
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/target/repo", "repo_id": "org/my-app"}'

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "org/my-app", "query": "authentication middleware", "n_results": 3}'
```

---

## Coding conventions (match existing packages)

- `from __future__ import annotations` at top of every file
- pydantic-settings for config, `POD_MEMORY_` prefix
- No comments explaining what code does — only comments for non-obvious WHY
- Raise specific exceptions (`ValueError`, `RuntimeError`) not generic ones
- Follow the same pattern as `packages/pod-brain/pod_brain/config.py` for settings
- Do NOT mock ChromaDB in implementation — it runs embedded in-process

---

## What NOT to touch

- `packages/pod-brain/` — except `agents/architect.py` (one section only)
- `packages/pod-mcp/` — complete, do not modify
- `apps/studio-api/` — no changes needed for Phase 3
- `apps/studio-ui/` — Phase 4 concern
