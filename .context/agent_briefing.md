# Agent Briefing — Agentic DevStudio

Read this before starting any work on this repo.

## What This Project Is

**Agentic DevStudio** is an agentic SDLC orchestration engine that autonomously builds features
in **external target repos** using a team of AI agents (Architect → Builder → QA).
It is NOT a project that manages its own development. It IS the tool.

## Mental Model

```
User: "Build a login form for github.com/org/my-app"
          │
          ▼
[ agentic-devstudio (THIS REPO) ]
  ├── pod-brain: LangGraph orchestrates Architect → Builder → QA
  ├── pod-mcp:   MCP server reads/writes files in the TARGET repo
  ├── pod-memory: ChromaDB indexes the TARGET repo's code
  └── pod-ui:    Dashboard where the human assigns tasks
          │
          ▼
[ Target repo: github.com/org/my-app ]
  ├── feat/login-form   (branch created by pod-mcp/git_gatekeeper)
  ├── src/LoginForm.tsx (file written by Builder agent via pod-mcp)
  └── PR #42            (opened by git_gatekeeper, reviewed by human)
```

## Folder Structure

| Folder | Purpose | Status |
|---|---|---|
| `packages/pod-brain/` | LangGraph agent graph (Architect, Builder, QA nodes) | **Done (Phase 1)** |
| `packages/pod-mcp/` | MCP server: filesystem, shell, git tools on TARGET repos | **Done (Phase 2)** |
| `packages/pod-memory/` | ChromaDB indexer/retriever for TARGET repo code | **Done (Phase 3)** |
| `packages/pod-ui/` | React + CopilotKit dashboard for task assignment | Scaffold only |
| `apps/studio-api/` | FastAPI — wires pod-brain + exposes AG-UI SSE endpoints | **Done (Phase 1–2)** |
| `apps/studio-ui/` | Vite/Next app serving the dashboard | Scaffold only |
| `templates/github-actions/` | Workflow YAMLs injected INTO target repos | Done |
| `.context/` | Dev-time knowledge, not a product feature | — |

## Port Map

| Service | Port | Notes |
|---|---|---|
| `studio-api` (Brain API) | **8080** | FastAPI / uvicorn |
| `pod-mcp` (MCP tool server) | **8001** | FastMCP over SSE |
| `pod-memory` (ChromaDB layer) | **8000** | FastAPI + embedded ChromaDB |

## How to Run

```bash
cp .env.example .env        # fill in your values
uv sync --all-packages

# Terminal 1 — MCP tool server
TARGET_REPO_PATH=/path/to/target uv run uvicorn pod_mcp.server:app --app-dir packages/pod-mcp --port 8001

# Terminal 2 — Brain API
uv run uvicorn main:app --app-dir apps/studio-api --port 8080 --reload

# Terminal 3 — pod-memory (ChromaDB layer)
uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000

# Trigger a task
curl -N -X POST http://localhost:8080/api/run \
  -H "Content-Type: application/json" \
  -d '{"task":"Add a hello world endpoint","target_repo":"/path/to/repo","thread_id":"dev1-req1"}'

# Resume after human-review interrupt
curl -X POST http://localhost:8080/api/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"dev1-req1","approved":true}'

# Run unit tests (no external services needed)
uv run pytest packages/pod-brain/tests/ -v
```

## uv Workspace

```
packages/pod-brain   → "pod-brain"   (LangGraph graph)
packages/pod-mcp     → "pod-mcp"     (MCP server)
packages/pod-memory  → "pod-memory"  (scaffold)
apps/studio-api      → "studio-api"  (FastAPI)
```
Cross-member deps are linked locally (editable installs). Regenerate pip fallback:
`uv export --all-packages --no-hashes --no-editable > requirements.txt`

---

## Phase 1 — pod-brain (complete)

**Key files:**
- `config.py` — `PodBrainSettings` (pydantic-settings, `POD_BRAIN_*` prefix)
- `graph/state.py` — `PodState` TypedDict + `DesignPlan`, `QAResult`, `HumanDecision` models
- `tools/__init__.py` — `load_mcp_tools()` (SSE→pod-mcp) + `make_mock_toolsets()` (tests)
- `agents/architect.py` — queries ChromaDB, produces `DesignPlan` via structured output
- `agents/builder.py` — ReAct tool loop; tool calls handled by `ToolNode` graph edges
- `agents/qa.py` — two-phase: tool loop → structured `QAResult` evaluator
- `graph/pod_graph.py` — supervisor (pure Python, no LLM) → architect → builder ↔ tool_executor → qa → human_review
  - Interrupt fires only on first builder invocation
  - Loop limits: `MAX_BUILDER_LOOPS` / `MAX_ARCHITECT_LOOPS` → escalate to human_review
  - `build_graph()` (sync, tests) / `get_graph()` (async singleton, studio-api)
- `apps/studio-api/main.py` — FastAPI + lifespan init
- `apps/studio-api/routes/agui.py` — `POST /api/run` + `POST /api/resume` (SSE streams)

---

## Phase 2 — pod-mcp + AG-UI enrichment (complete)

**`packages/pod-mcp/pod_mcp/`** (FastMCP server, port 8001)
- `mcp_instance.py` — singleton `FastMCP`; imported by tool modules to avoid circular deps
- `server.py` — mounts SSE at `/mcp` via `mcp.sse_app()`; entry point for uvicorn
- `tools/_security.py` — `_repo_root()` + `_safe_path()`: path traversal + symlink guard
- `tools/filesystem.py` — `read_file`, `write_file`, `list_directory`, `search_files`
- `tools/shell.py` — `execute_command` (cwd locked to `TARGET_REPO_PATH`, 1–300s cap)
- `tools/git_gatekeeper.py` — `create_branch` (GitPython, branch name validated)

**`apps/studio-api/routes/agui.py`** — AG-UI event enrichment
- `NODE_STARTED` — per-node progress labels ("Architect is planning...", etc.)
- `INTERRUPT` — emitted when supervisor calls `interrupt()` for human review
- `DONE` — end-of-stream sentinel for frontend `EventSource` cleanup

---

---

## Phase 3 — pod-memory (complete)

**`packages/pod-memory/pod_memory/`** (FastAPI + embedded ChromaDB, port 8000)
- `config.py` — `PodMemorySettings` (`POD_MEMORY_*` prefix, pydantic-settings)
- `indexer.py` — walks target repo files, chunks (~400 tok), upserts into ChromaDB; skips `.git/`, `node_modules/`, binaries
- `retriever.py` — `query(repo_id, text, n_results)` → `[{path, content, distance}]`
- `routes/memory.py` — `POST /index`, `POST /query`, `DELETE /index`
- `server.py` — FastAPI lifespan inits ChromaDB client + `SentenceTransformerEmbeddingFunction` on `app.state`

**Connection to pod-brain:**
- `packages/pod-brain/pod_brain/agents/architect.py` — pre-call to `POST /query` injects codebase context into Architect system prompt; failure is non-fatal (empty context fallback)

## What's Next (Phase 4 — UI)
- Connect studio-ui SSE stream to CopilotKit `useCoAgent` hook
