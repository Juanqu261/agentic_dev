# studio-ui

Frontend for **Agentic DevStudio**. A Next.js 16 + React 19 single-page app that drives the multi-agent orchestrator exposed by `apps/studio-api`.

## What it does

1. The user describes a development task and points the agent at a target repository.
2. The frontend opens a streaming SSE connection to `studio-api` (`POST /api/run`).
3. As `pod-brain` runs (Architect → Builder → QA), the UI shows live progress, tool calls, and streamed model output.
4. When the orchestrator pauses for human review (an `INTERRUPT` event), a modal lets the user approve or reject the design plan, optionally with extra instructions, and `POST /api/resume` continues the run.
5. The final result (status, branch name, files written, PR URL when applicable) is rendered when the stream closes.

## Run locally

Backend (in `apps/studio-api`):

```bash
uv sync --all-packages
uv run uvicorn main:app --app-dir apps/studio-api --reload --port 8000
```

Frontend (this folder):

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. Override the backend URL with `NEXT_PUBLIC_API_BASE_URL` in `.env.local`.

## Layout

```
src/
├── app/
│   ├── layout.tsx          # ThemeProvider only — no CopilotKit
│   ├── page.tsx            # Form ↔ Dashboard ↔ Result + review modal
│   └── globals.css
├── components/
│   ├── run-form.tsx        # task + target_repo input
│   ├── progress-dashboard.tsx  # live status, current node, activity log
│   ├── human-review-modal.tsx  # opens on INTERRUPT
│   ├── run-result.tsx      # final summary
│   └── ui/                 # shadcn-style primitives
├── hooks/
│   ├── use-agentic-run.tsx # POST /api/run + /api/resume, SSE reducer
│   └── use-theme.tsx
└── lib/
    ├── agui-events.ts      # event type definitions
    ├── api.ts              # POST helpers
    └── sse.ts              # POST-friendly SSE iterator
```

## Backend contract

`studio-api` emits the following SSE event types (see `apps/studio-api/routes/agui.py`):

| Event                  | Meaning                                           |
| ---------------------- | ------------------------------------------------- |
| `NODE_STARTED`         | A LangGraph node (architect, builder, qa, …) ran. |
| `TEXT_MESSAGE_CONTENT` | Streamed token from a chat model.                 |
| `TOOL_CALL_START`      | A tool invocation began.                          |
| `TOOL_CALL_END`        | The tool invocation finished.                     |
| `INTERRUPT`            | The graph is paused waiting for human review.     |
| `RUN_FINISHED`         | The graph completed without error.                |
| `RUN_ERROR`            | An exception terminated the run.                  |
| `DONE`                 | Stream is closed (sent unconditionally last).     |

The frontend's `use-agentic-run.tsx` hook reduces these into a single `RunState` object that the UI components observe.
