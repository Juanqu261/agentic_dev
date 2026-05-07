# ADR 003 — pod-mcp Architecture

**Date:** 2026-05-07
**Status:** Accepted (pre-implementation)

## Context

pod-brain is fully wired to call MCP tools but pod-mcp does not exist yet.
Phase 2 requires implementing the MCP server so Builder and QA agents can
actually read/write files and run commands in a target repo.

## Decision

### What pod-mcp is

An **MCP server** built with `fastmcp`, served over HTTP/SSE on port 8001.
It is **not** a FastAPI server. pod-brain connects to it via
`langchain-mcp-adapters` (already configured in `pod_brain/tools/__init__.py`).

Every tool call is sandboxed to a single directory: `POD_MCP_TARGET_REPO`.
Nothing can read, write, or execute outside that root.

### Two deployment modes — same code, different config

**Local (single developer):**
- pod-mcp runs on the developer's machine, loopback only, no auth required.
- `POD_MCP_TARGET_REPO` points to a local clone of the target repo.

**Remote (cloud agent / shared team infra):**
- pod-mcp runs on a cloud VM or shared server, TLS + API key required.
- `POD_MCP_TARGET_REPO` points to a cloud clone; agents push to GitHub from there.
- Each pod-brain instance points to its own remote pod-mcp via `POD_BRAIN_POD_MCP_URL`.

### Multi-developer sync model

Multi-dev sync does **not** happen through a shared MCP server.
Each developer has their own pod-mcp pointing at their own repo clone.
Synchronization happens through:
- **Git** — branches and PRs (one branch per task, one PR per pod)
- **ChromaDB** — shared semantic memory updated after each merge

## Tool contract

Tool names must match exactly what `pod_brain/tools/__init__.py` picks by name:

| Tool | Used by | Purpose |
|---|---|---|
| `read_file` | Architect, Builder, QA | Read file from target repo |
| `write_file` | Builder | Write/overwrite file in target repo |
| `list_directory` | Architect, Builder, QA | List directory contents |
| `search_files` | Architect | Grep across target repo |
| `execute_command` | Builder, QA | Run shell command (cwd = target repo) |
| `create_branch` | Builder | Git branch creation |

## Files to implement

```
packages/pod-mcp/pod_mcp/
├── server.py          FastMCP("pod-mcp") instance, mounts all tools, SSE on :8001
├── config.py          PodMcpSettings (POD_MCP_ prefix): target_repo, port, api_key
└── tools/
    ├── filesystem.py  read_file, write_file, list_directory, search_files
    ├── shell.py       execute_command (timeout, output capture, cwd enforcement)
    └── git_gatekeeper.py  create_branch, commit, open_pr
```

## Run command (once implemented)

```bash
uv run fastmcp run packages/pod-mcp/pod_mcp/server.py --transport sse --port 8001
```
