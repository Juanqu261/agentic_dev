# ADR 002 — This Tool Operates on External Target Repos

**Date:** 2026-05-06
**Status:** Accepted

## Context
Initial scaffolding treated this repo as both the tool AND the project being
developed. The `pods/` folder and `semantic_index.yml` workflow were placed here
as if this repo was the target of the agents.

## Decision
Clarified the correct mental model:

- **This repo** = the agentic-devstudio engine (the tool/package)
- **Target repos** = external projects the tool is pointed at

Agents (Architect, Builder, QA) read and write files in the **target repo**,
not in this repo.

## Consequences
- `pods/` folder removed — pods are runtime instances, not repo folders
- `templates/github-actions/` added — workflow YAML files the tool injects
  INTO target repos (they don't belong in this repo's `.github/`)
- `.github/workflows/ci.yml` here only tests THIS package's own code
- `Dockerfile` added — the tool can be deployed as a container pointed
  at any external repo
- `scripts/index_project.py` runs against a target repo path argument,
  not against this repo
