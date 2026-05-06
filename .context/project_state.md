# Project State — Agentic DevStudio

## What is this project?
An agentic SDLC orchestration engine. When run, it operates on **external target repos**
(other projects/apps). It does NOT manage its own codebase — it is the tool.

Deployment options:
- **Package**: `pip install agentic-devstudio`, run against any project
- **Docker**: `docker run agentic-devstudio` pointed at a target repo

## Current Phase
**Phase 0 — Repo scaffold complete**

The monorepo structure has been established. All packages, apps, templates,
and dev-context files are in place. No implementation code exists yet.

## What's Done
- [x] Monorepo structure scaffolded (Option B — domain-driven packages)
- [x] Git repo initialized, .gitignore + .gitattributes configured
- [x] Corrected mental model: this tool operates ON external repos, not itself
- [x] `pods/` folder removed (pods are runtime instances, not repo folders)
- [x] `templates/github-actions/` created for files injected into target repos
- [x] `Dockerfile` added for container deployment option

## What's Next (Phase 1 — The Brain)
- [ ] Define `LangGraphState` in `packages/pod-brain/pod_brain/graph/state.py`
- [ ] Implement Architect node
- [ ] Implement Builder node
- [ ] Implement QA node
- [ ] Wire the graph with loop-back from QA → Builder on failure

## Key Decisions Made
- See `.context/decisions/` for ADRs
