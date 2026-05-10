# Agentic DevStudio: Multi-Developer Orchestration Framework

## Goal
To provide a decentralized, multi-user environment where teams of Humans and Agents collaborate on a single codebase. Each "Developer" is a **Power-Pod** (Human + Agent Team) that builds modular components in isolation, synchronized by a global memory layer and automated Git orchestration.

---

## Architecture: The "Decentralized Pod" Model

### 1. The Power-Pod (Per Developer)
Each team member operates their own SDLC stack:
*   **LangGraph Pod:** Orchestrates the local Builder and QA agents.
*   **CopilotKit:** The interface for the specific human developer to assign tasks.
*   **A2UI:** Renders local previews of the component being built.

### 2. Global Axiom Layer (ChromaDB Cloud)
To keep the team synchronized without massive token costs:
*   **Axiom Indexing:** Every time a branch is merged, an agent generates a semantic summary of the changes and stores it as **axioms** in ChromaDB Cloud — shared across all pods.
*   **Axiom Injection:** When Dev B starts the "Home Page," their Architect agent queries the axiom layer: *"What is the status of the Login Form?"* It receives the API endpoints and component names created by Dev A, ensuring consistent naming and integration.

### 3. The "Traffic Light" (Git Orchestration)
To prevent merge conflicts and human error:
*   **Automated Branching:** Tasks are strictly scoped to feature branches. 
*   **Pre-Flight Check:** The **Reviewer Agent** runs automated tests and a "Conflict Analysis" against the `main` branch before any code is committed.
*   **CI/CD Integration:** The agents interact with GitHub Actions to report build statuses back into the CopilotKit dashboard.

---

## Workflow: The Modular SDLC

1.  **Task Allocation:** Human assigns `feat/login` to their Pod.
2.  **Context Pull:** The Architect agent queries the axiom layer for existing UI patterns and shared constants.
3.  **Autonomous Build:** Builder Agent edits the files via **MCP (Filesystem Tool)**.
4.  **Local QA:** QA Agent runs tests in an isolated **MCP Terminal**.
5.  **Traffic Light Sync:** Agent creates a PR. If conflicts are detected with `main`, the **Architect Agent** proposes a resolution to the human.

---

## Quick Start

### 1. Prerequisites

```powershell
# Install uv (Python package manager)
pip install uv

# Clone and enter the repo
git clone https://github.com/your-org/agentic_dev.git
cd agentic-devstudio

# Install all dependencies
uv sync --all-packages
uv sync --all-extras

# Configure environment
Copy-Item .env.example .env
# Open .env and set POD_BRAIN_GEMINI_API_KEY
```

### 2. Start all backend services (Windows)

```powershell
# Point at the repo you want agents to work on
.\scripts\start_services.ps1
```

This opens **three terminal windows** automatically:

| Window | Service | Port |
|---|---|---|
| Green | `pod-memory` — ChromaDB semantic index | 8000 |
| Yellow | `pod-mcp` — filesystem / shell / git tools | 8001 |
| Magenta | `studio-api` — agent orchestration API | 8080 |

Wait ~10 seconds for the sentence-transformer model to load before sending requests.

> **`-TargetRepo`** sets the root directory the Builder and QA agents will read and write files in. It must be an absolute path to an existing local directory (your cloned project). You can also set `TARGET_REPO_PATH` in `.env` and omit the flag.

### 3. Start the frontend (Next.js UI)

The web UI lives in `apps/studio-ui`. It posts tasks to `studio-api`, streams progress live and renders the human-review interrupt as a modal.

```powershell
cd apps\studio-ui

# Install JS dependencies (first time only)
npm install

# Point the UI at studio-api (defaults to http://localhost:8000)
"NEXT_PUBLIC_API_BASE_URL=http://localhost:8080" | Out-File -Encoding utf8 .env.local

# Start the dev server (Turbopack)
npm run dev
```

Open http://localhost:3000 — fill in the task and `target_repo`, submit, and watch the activity log stream. When the agent pauses for review, approve or send instructions from the modal.

Other scripts:

| Command | Purpose |
|---|---|
| `npm run dev` | Dev server with hot reload (port 3000) |
| `npm run build` | Production build |
| `npm run start` | Run the production build |
| `npm run lint` | Lint with Next/ESLint |

### 4. Trigger your first task

```powershell
# Start a new agent run — replace the values with your task and repo name
curl -N -X POST http://localhost:8080/api/run `
  -H "Content-Type: application/json" `
  -d '{
    "task": "Create a simple hello world webpage for kids using HTML, CSS, and JavaScript (basics).",
    "target_repo": "example",
    "thread_id": "dev1-task1"
  }'
```

The response is a **Server-Sent Events stream**. You will see events like:
```
data: {"type": "NODE_STARTED", "data": {"node": "architect", "label": "Architect is planning..."}}
data: {"type": "INTERRUPT", "data": {"message": "Human review required.", "thread_id": "dev1-task1"}}
```

When you receive `INTERRUPT`, inspect the design plan and resume:

```powershell
# Approve the plan and let the Builder proceed
curl -X POST http://localhost:8080/api/resume `
  -H "Content-Type: application/json" `
  -d '{
    "thread_id": "dev1-task1",
    "approved": true,
    "comment": "Looks good, proceed"
  }'
```

### 5. Optional — index the target repo for semantic context

Before running tasks, index the target repo so the Architect agent has codebase awareness:

```powershell
curl -X POST http://localhost:8000/index `
  -H "Content-Type: application/json" `
  -d '{
    "repo_path": "C:\\path\\to\\your\\target-repo",
    "repo_id": "org/my-app"
  }'
# Returns: {"indexed": 142, "repo_id": "org/my-app"}
```

> **`repo_id`** is a free-form string identifier for the repo (e.g. `"org/my-app"`). It must match the `target_repo` field you pass to `/api/run` — the Architect uses it to query the right axioms from ChromaDB.

---

## Updated Ecosystem Setup

### Step 1: The Global Registry
*   Set up **ChromaDB Cloud** (or a self-hosted instance) as the shared axiom store accessible by all pods.

### Step 2: GitHub / Git Middleware
*   Initialize the **Git-Gatekeeper MCP Server**. This allows agents to run `git checkout -b`, `git pull`, and `gh pr create` based on task status.

### Step 3: Semantic Indexing
*   Run the `index-project` script to generate the initial architectural "map" of the existing repo for the agents to read.

---

## The Vision: "Component-Driven Autonomy"
By focusing on **specific components** rather than the whole app, we minimize the "noise" the LLM has to process. We build the app like Lego bricks—each developer (Human+Agent) ensures their brick is perfect before the Git-Gatekeeper snaps it into the master project.
