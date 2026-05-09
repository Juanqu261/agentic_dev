# pod-memory

Semantic memory layer for Agentic DevStudio. Indexes a target repo's code into ChromaDB and exposes a REST API so the Architect agent can retrieve relevant context before planning.

---

## How it fits

```
Architect agent (pod-brain)
        │
        │  POST /query  { repo_id, query, n_results }
        ▼
┌──────────────────────────┐
│  pod-memory  (port 8000) │
│                          │
│  indexer   → ChromaDB    │
│  retriever ← ChromaDB    │
└──────────────────────────┘
        │
        │  reads files
        ▼
  [ Target repo on disk ]
```

The Architect calls `POST /query` before every design run. If pod-memory is unreachable the Architect continues with empty context — it is optional infrastructure.

---

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/index` | `{ repo_path, repo_id }` | `{ indexed: N, repo_id }` |
| `POST` | `/query` | `{ repo_id, query, n_results? }` | `{ results: [{path, content, distance}] }` |
| `DELETE` | `/index` | `{ repo_id }` | `{ deleted: true, repo_id }` |

---

## ChromaDB modes

| Mode | When | Config |
|---|---|---|
| **Local embedded** (default) | No external process needed, data persisted to disk | `POD_MEMORY_CHROMA_PATH=./chroma_data` |
| **Remote** | Points to a running `chroma run` server | `POD_MEMORY_CHROMA_HOST=localhost` + `POD_MEMORY_CHROMA_PORT=8000` |

When `POD_MEMORY_CHROMA_HOST` is set, the local path is ignored.

---

## Configuration

All vars prefixed `POD_MEMORY_`.

| Var | Default | Description |
|---|---|---|
| `POD_MEMORY_PORT` | `8000` | pod-memory FastAPI port |
| `POD_MEMORY_CHROMA_PATH` | `./chroma_data` | Local ChromaDB data dir |
| `POD_MEMORY_CHROMA_HOST` | _(unset)_ | Remote ChromaDB host — set to enable remote mode |
| `POD_MEMORY_CHROMA_PORT` | `8000` | Remote ChromaDB port |
| `POD_MEMORY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model (local, no API key) |
| `POD_MEMORY_CHUNK_SIZE` | `400` | Tokens per chunk (~1600 chars) |
| `POD_MEMORY_CHUNK_OVERLAP` | `50` | Overlap between chunks (~200 chars) |

---

## Running

```bash
uv sync --all-packages

# Local embedded ChromaDB
uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000

# Index a repo
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repo", "repo_id": "org/my-app"}'

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "org/my-app", "query": "authentication middleware", "n_results": 5}'
```

---

## Tests

Integration tests — real ChromaDB, real embeddings, no mocks.

```bash
uv run pytest packages/pod-memory/tests/ -v
```

First run downloads `all-MiniLM-L6-v2` (~90 MB). Subsequent runs use the cached model.
