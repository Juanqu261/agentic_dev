# studio-ui

Next.js 16 frontend for `apps/studio-api`. Renders a form to start agentic
runs, streams progress live from the backend, and surfaces the human-review
interrupt as a modal.

## Architecture

This app **does not use CopilotKit**. It was originally scaffolded from the
CopilotKit + LangGraph template, but the agent communication contract of
`studio-api` (custom AG-UI SSE) is incompatible with the LangGraph SDK
protocol that CopilotKit's `LangGraphAgent` expects. We replaced the wiring
with a small custom SSE client.

### Data flow

```
RunForm  ──user submit──►  useAgenticRun.start()
                              │
                              ├── POST {API_BASE_URL}/api/run  (SSE)
                              │       body: {task, target_repo, thread_id}
                              ▼
                          readSSE() yields AGUIEvent objects
                              │
                              ▼
                          reducer(state, event)
                              │
              ┌───────────────┼────────────────┬──────────────┐
              ▼               ▼                ▼              ▼
       ProgressDashboard  HumanReviewModal  RunResult      (cancel)
                              │
                              ▼
                          useAgenticRun.resume({approved, instructions})
                              │
                              └── POST /api/resume  (SSE; same reducer)
```

### Key files

| Concern                           | File                                           |
| --------------------------------- | ---------------------------------------------- |
| Event type definitions            | `src/lib/agui-events.ts`                       |
| POST helpers (run / resume)       | `src/lib/api.ts`                               |
| SSE iterator (POST-friendly)      | `src/lib/sse.ts`                               |
| Run state machine + lifecycle     | `src/hooks/use-agentic-run.tsx`                |
| Form (task + target_repo)         | `src/components/run-form.tsx`                  |
| Live progress / activity log     | `src/components/progress-dashboard.tsx`        |
| Human-review modal (on INTERRUPT) | `src/components/human-review-modal.tsx`       |
| Final summary                     | `src/components/run-result.tsx`                |
| Page composition                  | `src/app/page.tsx`                             |

### Backend contract

The frontend assumes the contract in
`apps/studio-api/routes/agui.py`:

- `POST /api/run` body: `{ task, target_repo, thread_id, max_builder_loops?, max_architect_loops? }`
- `POST /api/resume` body: `{ thread_id, approved, instructions? }`
- Both stream `data: <json>\n\n` SSE frames with `type` field in the AG-UI
  vocabulary (`NODE_STARTED`, `TEXT_MESSAGE_CONTENT`, `TOOL_CALL_START`,
  `TOOL_CALL_END`, `INTERRUPT`, `RUN_FINISHED`, `RUN_ERROR`, `DONE`).

If the backend contract changes, update `agui-events.ts` first, then the
reducer in `use-agentic-run.tsx`, then any visualisation in
`progress-dashboard.tsx`.

### Why custom SSE instead of EventSource?

`EventSource` is GET-only. The backend takes its task description in the
request body, so we use `fetch(POST)` and parse the response stream by hand
in `src/lib/sse.ts`. The trade-off is that we lose `EventSource`'s automatic
reconnect; the user clicks "New run" instead.

## State the hook keeps

```ts
type RunState = {
  status: "idle" | "running" | "awaiting_human" | "done" | "error";
  threadId: string | null;
  task: string | null;
  targetRepo: string | null;
  currentNode: string | null;
  nodeLabel: string | null;
  events: AGUIEvent[];      // raw event log (debug + activity rendering)
  textBuffer: string;       // accumulated TEXT_MESSAGE_CONTENT chunks
  toolCalls: ToolCallRecord[];
  interrupt: { message: string } | null;
  finalSummary: Record<string, unknown> | null;
  error: string | null;
};
```

`thread_id` is generated client-side with `crypto.randomUUID()` on `start()`
and reused for the matching `resume()`.

## Conventions

- All shadcn-style primitives live in `src/components/ui/`. They use the CSS
  variables defined in `globals.css` (`--background`, `--card`, `--primary`,
  `--destructive`, `--ring`, `--radius`, etc.) — keep them theme-agnostic.
- Feature components live one directory up at `src/components/`.
- The hook is the single source of truth for run state; components never
  fetch directly.
- `NEXT_PUBLIC_API_BASE_URL` is the only required env var (default
  `http://localhost:8000`).
