# ADR 001 — Monorepo Structure: Domain-Driven Packages (Option B)

**Date:** 2026-05-06
**Status:** Accepted

## Context
We need a single repo that contains the entire agentic-devstudio engine
(orchestration, tools, memory, UI) while keeping each concern independently
testable and deployable.

## Decision
Use a **domain-driven packages** layout under `packages/`:

- `pod-brain/` — LangGraph orchestration
- `pod-mcp/` — MCP server and tools
- `pod-memory/` — ChromaDB client/indexer
- `pod-ui/` — React + CopilotKit frontend

Thin runnable apps in `apps/` wire the packages together.

## Consequences
- Each package has its own `pyproject.toml` and `tests/`
- Root `pyproject.toml` acts as a `uv` workspace
- Adding a new capability = adding a new `packages/pod-X/` folder
