/**
 * Event types emitted by studio-api over SSE.
 * Mirrors the contract in apps/studio-api/routes/agui.py:_AGUI_MAP and the
 * INTERRUPT/DONE/RUN_ERROR events emitted by _stream_events().
 */
export type RunStatus =
  | "idle"
  | "running"
  | "awaiting_human"
  | "done"
  | "error";

export interface NodeStartedEvent {
  type: "NODE_STARTED";
  data: { node: string; label: string };
}

export interface RunStartedEvent {
  type: "RUN_STARTED";
  data: Record<string, unknown>;
}

export interface RunFinishedEvent {
  type: "RUN_FINISHED";
  data: Record<string, unknown>;
}

export interface RunErrorEvent {
  type: "RUN_ERROR";
  data: { error?: string };
}

export interface TextMessageContentEvent {
  type: "TEXT_MESSAGE_CONTENT";
  data: {
    chunk?: { content?: unknown };
    [k: string]: unknown;
  };
}

export interface ToolCallStartEvent {
  type: "TOOL_CALL_START";
  data: {
    name?: string;
    input?: unknown;
    [k: string]: unknown;
  };
}

export interface ToolCallEndEvent {
  type: "TOOL_CALL_END";
  data: {
    name?: string;
    output?: unknown;
    [k: string]: unknown;
  };
}

export interface InterruptEvent {
  type: "INTERRUPT";
  data: { message: string; thread_id: string };
}

export interface DoneEvent {
  type: "DONE";
}

export type AGUIEvent =
  | NodeStartedEvent
  | RunStartedEvent
  | RunFinishedEvent
  | RunErrorEvent
  | TextMessageContentEvent
  | ToolCallStartEvent
  | ToolCallEndEvent
  | InterruptEvent
  | DoneEvent;

export interface ToolCallRecord {
  id: string;
  name: string;
  input?: unknown;
  output?: unknown;
  status: "running" | "completed";
  startedAt: number;
  endedAt?: number;
}

/** Extract a streamed text chunk from a TEXT_MESSAGE_CONTENT event payload.
 *  LangChain emits a `chunk` object whose `.content` may be either a string or
 *  a list of typed parts. We try both shapes and fall back to "". */
export function extractTextChunk(event: TextMessageContentEvent): string {
  const content = event.data?.chunk?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part: unknown) => {
        if (typeof part === "string") return part;
        if (
          part &&
          typeof part === "object" &&
          "text" in (part as Record<string, unknown>)
        ) {
          const t = (part as { text?: unknown }).text;
          return typeof t === "string" ? t : "";
        }
        return "";
      })
      .join("");
  }
  return "";
}
