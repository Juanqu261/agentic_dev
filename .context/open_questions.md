# Open Questions

## Unresolved Design Decisions

### 1. Primary distribution format
- **Option A**: Pure Python package (`pip install agentic-devstudio`)
- **Option B**: Docker-first (`docker run agentic-devstudio`)
- **Option C**: Both (package wraps the Docker image)
- *Current lean: Both — Docker for self-hosted, package for local dev*

### 2. How does the tool authenticate with target repos?
- SSH keys? GitHub App? Personal access token?
- Does the user pass `--target-repo <path>` (local clone) or `--target-repo <github-url>` (remote)?

### 3. Multi-developer sync — how are pods isolated?
- Is each "pod" a separate running instance of the studio-api?
- Or is it a namespace within a single running instance?

### 4. ChromaDB hosting for multi-dev scenarios
- Local ChromaDB per developer vs. shared hosted instance (e.g., Chroma Cloud)
- Phase 3 decision

### 5. Frontend framework for studio-ui
- Vite + React vs. Next.js
- Next.js adds SSR which may be overkill for a local dashboard
