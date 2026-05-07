# Agent Briefing — Agentic DevStudio

Read this before starting any work on this repo.

## What This Project Is

**Agentic DevStudio** is an agentic SDLC orchestration engine — a tool/package
that, when given a task, autonomously builds features in **external target repos**
using a team of AI agents (Architect → Builder → QA).

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
  ├── feat/login-form (branch created by pod-mcp/git_gatekeeper)
  ├── src/LoginForm.tsx (file written by Builder agent via pod-mcp)
  └── PR #42 (opened by git_gatekeeper, reviewed by human)
```

## Folder Structure (quick reference)

| Folder | Purpose | Status |
|---|---|---|
| `packages/pod-brain/` | LangGraph agent graph (Architect, Builder, QA nodes) | **Implemented (Phase 1)** |
| `packages/pod-mcp/` | MCP server tools: filesystem, shell, git — all on TARGET repos | Scaffold only |
| `packages/pod-memory/` | ChromaDB client/indexer/retriever — indexes TARGET repo code | Scaffold only |
| `packages/pod-ui/` | React + CopilotKit dashboard for task assignment | Scaffold only |
| `apps/studio-api/` | FastAPI app wiring the packages together | Partially implemented |
| `apps/studio-ui/` | Vite/Next app serving the dashboard | Scaffold only |
| `templates/github-actions/` | Workflow YAML files injected INTO target repos by git_gatekeeper | Done |
| `.context/` | THIS folder — dev-time knowledge, not a product feature | — |

## Deployment Options
- **Python package**: `pip install agentic-devstudio` → `devstudio run --target <repo>`
- **Docker**: `docker run agentic-devstudio` pointed at a target repo

## Current Status: Phase 1 Complete — pod-brain implemented

### What exists and works in pod-brain

**`packages/pod-brain/pod_brain/config.py`**
- `PodBrainSettings` (pydantic-settings). All config via `POD_BRAIN_*` env vars or `.env`.
- Key settings: `ANTHROPIC_MODEL`, `ANTHROPIC_API_KEY`, `POD_MCP_URL` (default `http://localhost:8001`),
  `CHROMA_URL` (default `http://localhost:8000`), `CHECKPOINTER_DB` (SQLite path or `postgres://...`),
  `MAX_BUILDER_LOOPS` (3), `MAX_ARCHITECT_LOOPS` (2).

**`packages/pod-brain/pod_brain/graph/state.py`**
- `PodState` — TypedDict used as the LangGraph state. Fields:
  - Input: `task`, `target_repo`, `thread_id`
  - Routing: `current_node`, `next_node`
  - Loop control: `builder_iterations`, `architect_iterations`, `max_builder_loops`, `max_architect_loops`
  - Accumulated (operator.add): `messages: list[Any]`, `files_written: list[str]`
  - Agent outputs: `design_plan: DesignPlan | None`, `qa_result: QAResult | None`
  - Human-in-loop: `human_decision: HumanDecision | None`, `awaiting_human: bool`
  - Final: `branch_name`, `pr_url`, `error`, `status`
- Pydantic models at node boundaries: `DesignPlan`, `QAResult`, `HumanDecision`

**`packages/pod-brain/pod_brain/tools/__init__.py`**
- `load_mcp_tools(url)` — connects to pod-mcp via SSE, returns `AgentToolsets(architect, builder, qa)`
- `make_mock_toolsets()` — no-op stubs for unit tests (no pod-mcp needed)

**`packages/pod-brain/pod_brain/agents/`**
- `architect.py` — queries ChromaDB for context, produces `DesignPlan` via `with_structured_output`
- `builder.py` — binds MCP tools, emits AIMessage; tool calls handled by `ToolNode` in graph edges
- `qa.py` — two-phase: (1) ReAct tool loop to run lints/tests, (2) structured `QAResult` evaluator

**`packages/pod-brain/pod_brain/graph/pod_graph.py`**
- Supervisor-first hybrid pattern. Supervisor is a pure Python function (no LLM call).
- Graph: `supervisor → architect → supervisor → builder ↔ tool_executor → qa → supervisor → human_review → END`
- Interrupt: explicit `interrupt()` in supervisor when `builder_iterations == 0` (first build only)
- QA→Builder and QA→Architect loops run without re-interrupting.
- Loop limits enforced: if `builder_iterations >= max_builder_loops` → escalate to `human_review`
- Checkpointer: `AsyncSqliteSaver` (`:memory:` default) or `AsyncPostgresSaver` (if `postgres://` URL)
- `build_graph(toolsets, checkpointer_db)` — synchronous, used in tests
- `get_graph()` — async lazy singleton, used by studio-api

**`apps/studio-api/`**
- `main.py` — FastAPI + lifespan that calls `await get_graph()` at startup
- `routes/agui.py`:
  - `POST /api/run` — accepts `{task, target_repo, thread_id}`, returns SSE stream of AG-UI events
  - `POST /api/resume` — accepts `{thread_id, approved, comment, override_target?}`, injects `HumanDecision` and resumes stream

### How to run

```bash
# Install all workspace packages (uv recommended)
uv sync --all-packages

# Run unit tests (no external services needed — mocks replace LLM and MCP)
uv run pytest packages/pod-brain/tests/ -v

# Start the API (requires POD_BRAIN_ANTHROPIC_API_KEY env var)
# --app-dir adds apps/studio-api/ to sys.path so "from routes import agui" resolves
uv run uvicorn main:app --app-dir apps/studio-api --reload

# Trigger a task (SSE stream)
# If pod-mcp is not running, get_graph() falls back to mock toolsets automatically.
# Architect will call real Claude; Builder/QA tool calls will be no-ops.
curl -N -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"task":"Add a hello world endpoint","target_repo":"/path/to/repo","thread_id":"dev1-req1"}'

# Resume after design-review interrupt (human approves)
curl -X POST http://localhost:8000/api/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"dev1-req1","approved":true}'
```

### uv workspace model

The root `pyproject.toml` declares a uv workspace with four members:
```
packages/pod-brain    → Python package "pod-brain"
packages/pod-mcp      → Python package "pod-mcp"      (scaffold only)
packages/pod-memory   → Python package "pod-memory"   (scaffold only)
apps/studio-api       → Python package "studio-api"
```
`uv sync --all-packages` resolves all deps into a single shared `.venv` and installs
every member as an editable install. Cross-member deps (e.g. `studio-api` depends on
`pod-brain`) are linked locally, never fetched from PyPI.

`requirements.txt` at the repo root is the pip fallback (Docker / bare CI).
Regenerate it with: `uv export --all-packages --no-hashes --no-editable > requirements.txt`

## Source of Truth Docs
- `README.md` — goals and architecture overview
- `Phases.md` — 5-phase implementation plan
- `architecture.md` — layer diagram and communication protocols
- `.context/project_state.md` — current completion checklist

## What's Next (Phase 2 — pod-mcp)

pod-brain is fully wired to call MCP tools but pod-mcp is not implemented yet.
See `.context/decisions/003-pod-mcp-architecture.md` for the full design:
local vs remote modes, tool contract, and files to implement.