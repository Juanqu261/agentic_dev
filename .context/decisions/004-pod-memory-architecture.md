# ADR 004 — pod-memory Architecture

**Date:** 2026-05-08
**Status:** Accepted (pre-implementation)

## Context

The Architect agent currently has no semantic understanding of the target repo's
existing code. It can list files and read them individually, but cannot ask
"does an auth service already exist?" or "how is logging done across this repo?".

Phase 3 implements `packages/pod-memory/` — a ChromaDB-backed service that indexes
the target repo and answers semantic queries, giving the Architect contextual
awareness before it produces a design plan.

## Decision

### What pod-memory is

A **FastAPI service** running on port **8000** (ChromaDB's standard port, which
it wraps). It exposes three HTTP endpoints consumed by pod-brain's Architect agent:

- `POST /index` — chunk + embed all files in the target repo into ChromaDB
- `POST /query` — semantic similarity search: returns the most relevant code chunks
- `DELETE /index` — wipe the collection for a given target repo (reset on re-index)

pod-brain connects to it via plain `httpx` calls inside `architect.py`, not via MCP.
This is intentional: memory is a *read* concern for the Architect only, not a tool
the Builder or QA agent should call ad-hoc.

### What gets embedded

Each file in the target repo is chunked and embedded at index time:

| Field stored in ChromaDB | Value |
|---|---|
| `id` | `{repo_slug}::{relative_path}::{chunk_index}` |
| `document` | raw code chunk (≤ 400 tokens, overlap 50) |
| `metadata.path` | relative file path |
| `metadata.repo` | target repo identifier |
| `metadata.language` | file extension → language tag |

### Embedding model

`sentence-transformers/all-MiniLM-L6-v2` via the `chromadb` default embedding
function (`chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction`).
No external API call required — runs locally. Can be swapped via
`POD_MEMORY_EMBEDDING_MODEL` env var.

### When indexing runs

- **On demand:** studio-api calls `POST /index` during the lifespan startup if
  `POD_BRAIN_CHROMA_URL` is set, so the Architect has fresh context at boot.
- **After merge:** when QA passes and a PR is merged, studio-api calls `POST /index`
  again to refresh the collection with the newly committed code.

### Connection point with pod-brain

`packages/pod-brain/pod_brain/agents/architect.py` already has a placeholder
`chroma_url = settings.chroma_url`. Phase 3 replaces that with a real `httpx`
call to `POST /query` before the Architect LLM call:

```python
async with httpx.AsyncClient() as client:
    r = await client.post(
        f"{settings.chroma_url}/query",
        json={"repo": state["target_repo"], "query": state["task"], "n_results": 5},
    )
context_chunks = r.json()["results"]  # injected into the system prompt
```

### Multi-developer sync

All developers point their pod-brain at the **same** ChromaDB instance (shared
infra). When Dev A's PR merges and triggers a re-index, Dev B's Architect
immediately sees the new code on the next query. This is the cross-pod context
described in `architecture.md`.

## Files to implement

```
packages/pod-memory/
├── pyproject.toml              add: chromadb, sentence-transformers, fastapi, uvicorn, httpx
└── pod_memory/
    ├── __init__.py
    ├── config.py               PodMemorySettings (POD_MEMORY_ prefix): chroma_path, embedding_model, port
    ├── server.py               FastAPI app, lifespan initialises ChromaDB client
    ├── indexer.py              chunk_file(), index_repo(repo_path, repo_id) → walks files, embeds, upserts
    ├── retriever.py            query(repo_id, text, n_results) → returns list[ChunkResult]
    └── routes/
        ├── __init__.py
        └── memory.py           POST /index, POST /query, DELETE /index
```

## Run command

```bash
uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000
```
