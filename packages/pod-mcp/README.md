# pod-mcp

MCP tool server for Agentic DevStudio. Gives AI agents (Architect, Builder, QA)
controlled access to a **target repo** — filesystem, shell, and git — over SSE.

Agents never touch the OS directly. Every call goes through this server,
which enforces that all paths stay inside `TARGET_REPO_PATH`.

## Tools

| Tool | Agent | Description |
|---|---|---|
| `read_file` | Architect, Builder, QA | Read a file's UTF-8 contents |
| `write_file` | Builder | Write/overwrite a file (creates parent dirs) |
| `edit_file` | Builder | Surgical string replacement inside a file |
| `delete_file` | Builder | Delete a file |
| `list_directory` | All | List immediate children of a directory |
| `get_file_tree` | Architect | Recursive tree view up to `max_depth` |
| `search_files` | Architect | Glob for files by name pattern |
| `find_in_files` | Architect, QA | Regex search across file contents |
| `execute_command` | Builder, QA | Run a shell command (cwd = target repo, 1–300s timeout) |
| `create_branch` | Builder | Create and checkout a git branch |
| `git_add` | Builder | Stage files for commit |
| `git_commit` | Builder | Commit staged changes |
| `git_diff` | QA | Show staged or unstaged diff |
| `open_pr` | Builder | Push branch and open a GitHub PR (requires `GITHUB_TOKEN`) |

## Run

```bash
# Required env vars
export TARGET_REPO_PATH=/absolute/path/to/target/repo
export GITHUB_TOKEN=ghp_...   # only needed for open_pr

uv run uvicorn pod_mcp.server:app --app-dir packages/pod-mcp --port 8001
```

The SSE endpoint is at `http://localhost:8001/mcp`.
pod-brain connects to it automatically via `POD_BRAIN_POD_MCP_URL`.

## Security

- All paths are resolved and validated against `TARGET_REPO_PATH` before any I/O.
- Symlinks that point outside the repo root are blocked.
- `execute_command` cwd is hard-locked to `TARGET_REPO_PATH` — callers cannot change it.
- Branch names are validated against a safe-character regex before any git operation.
