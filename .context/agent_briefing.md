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

| Folder | Purpose |
|---|---|
| `packages/pod-brain/` | LangGraph agent graph (Architect, Builder, QA nodes) |
| `packages/pod-mcp/` | MCP server tools: filesystem, shell, git — all on TARGET repos |
| `packages/pod-memory/` | ChromaDB client/indexer/retriever — indexes TARGET repo code |
| `packages/pod-ui/` | React + CopilotKit dashboard for task assignment |
| `apps/studio-api/` | FastAPI app wiring the packages together |
| `apps/studio-ui/` | Vite/Next app serving the dashboard |
| `templates/github-actions/` | Workflow YAML files injected INTO target repos by git_gatekeeper |
| `.context/` | THIS folder — dev-time knowledge, not a product feature |

## Deployment Options
- **Python package**: `pip install agentic-devstudio` → `devstudio run --target <repo>`
- **Docker**: `docker run agentic-devstudio` pointed at a target repo

## Current Status
Phase 0 complete — scaffold only, no implementation yet.
Active work: **Phase 1 (pod-brain)** — LangGraph state + agent nodes.

## Source of Truth Docs
- `README.md` — goals and architecture overview
- `Phases.md` — 5-phase implementation plan
- `architecture.md` — layer diagram and communication protocols
