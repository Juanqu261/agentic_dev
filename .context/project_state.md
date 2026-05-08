# Project State — Agentic DevStudio

## What is this project?
An agentic SDLC orchestration engine. When run, it operates on **external target repos**
(other projects/apps). It does NOT manage its own codebase — it is the tool.

Deployment options:
- **Package**: `pip install agentic-devstudio`, run against any project
- **Docker**: `docker run agentic-devstudio` pointed at a target repo

## Current Phase
**Phase 2 — The Hands & Nerves (pod-mcp + AG-UI) — complete**

## What's Done
- [x] Monorepo structure scaffolded
- [x] Git repo initialized, .gitignore + .gitattributes configured
- [x] Corrected mental model: this tool operates ON external repos, not itself
- [x] `pods/` folder removed (pods are runtime instances, not repo folders)
- [x] `templates/github-actions/` created for files injected into target repos
- [x] `Dockerfile` added for container deployment option
- [x] Root `pyproject.toml` — uv workspace configured
- [x] `packages/pod-brain/pyproject.toml` — deps declared (langgraph, langchain-anthropic, chromadb, etc.)
- [x] `pod_brain/config.py` — `PodBrainSettings` (pydantic-settings, `POD_BRAIN_` prefix)
- [x] `pod_brain/graph/state.py` — `PodState` TypedDict + `DesignPlan`, `QAResult`, `HumanDecision` Pydantic models
- [x] `pod_brain/tools/__init__.py` — `load_mcp_tools()` (SSE) + `make_mock_toolsets()` for tests
- [x] `pod_brain/agents/architect.py` — queries ChromaDB, produces `DesignPlan` via structured output
- [x] `pod_brain/agents/builder.py` — ReAct tool loop (tool calls handled by graph edges)
- [x] `pod_brain/agents/qa.py` — two-phase: tool loop then structured `QAResult` evaluator
- [x] `pod_brain/graph/pod_graph.py` — supervisor + pipeline hybrid, interrupt on first build, SQLite checkpointer
- [x] `pod_brain/__init__.py` — public API surface
- [x] `apps/studio-api/main.py` — FastAPI app with lifespan graph init
- [x] `apps/studio-api/routes/agui.py` — `POST /api/run` (SSE) + `POST /api/resume`
- [x] Unit tests for state, supervisor routing, architect, builder, QA, graph

- [x] `packages/pod-mcp/` — MCP server implemented (FastMCP + FastAPI, port 8001)
- [x] `apps/studio-api/routes/agui.py` — AG-UI enriched: `NODE_STARTED`, `INTERRUPT`, `DONE` events
- [x] `.env.example` — all env vars documented at repo root

## What's Next (Phase 3 — The Mind & UI)
- [ ] Implement `packages/pod-memory/` — ChromaDB indexer/retriever for target repo code
- [ ] Implement `apps/studio-ui/` — React + CopilotKit dashboard
- [ ] Connect studio-ui SSE stream to CopilotKit `useCoAgent` hook

## Key Decisions Made
- See `.context/decisions/` for ADRs
- Supervisor is a pure routing function (no LLM call) — deterministic and cheap to test
- Human interrupt fires only on first builder invocation (explicit `interrupt()` in supervisor)
- MCP transport: SSE/HTTP (consistent between local dev and Docker)
- Checkpointer: `AsyncSqliteSaver` for MVP, swap to `AsyncPostgresSaver` via `POD_BRAIN_CHECKPOINTER_DB=postgres://...`
- QA uses two-phase LLM calls: tool loop + separate structured-output evaluator
