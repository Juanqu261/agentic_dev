"use client";

import { useCallback, useReducer, useRef } from "react";
import {
  AGUIEvent,
  RunStatus,
  ToolCallRecord,
  extractTextChunk,
} from "@/lib/agui-events";
import { resumeTask, runTask } from "@/lib/api";
import { readSSE } from "@/lib/sse";

interface RunState {
  status: RunStatus;
  threadId: string | null;
  task: string | null;
  targetRepo: string | null;
  currentNode: string | null;
  nodeLabel: string | null;
  events: AGUIEvent[];
  textBuffer: string;
  toolCalls: ToolCallRecord[];
  interrupt: { message: string } | null;
  finalSummary: Record<string, unknown> | null;
  error: string | null;
}

const INITIAL_STATE: RunState = {
  status: "idle",
  threadId: null,
  task: null,
  targetRepo: null,
  currentNode: null,
  nodeLabel: null,
  events: [],
  textBuffer: "",
  toolCalls: [],
  interrupt: null,
  finalSummary: null,
  error: null,
};

type Action =
  | { type: "START"; threadId: string; task: string; targetRepo: string }
  | { type: "EVENT"; event: AGUIEvent }
  | { type: "RESUME_SENT" }
  | { type: "ERROR"; error: string }
  | { type: "RESET" };

function reducer(state: RunState, action: Action): RunState {
  switch (action.type) {
    case "START":
      return {
        ...INITIAL_STATE,
        status: "running",
        threadId: action.threadId,
        task: action.task,
        targetRepo: action.targetRepo,
      };
    case "RESUME_SENT":
      return {
        ...state,
        status: "running",
        interrupt: null,
        // Keep history but reset transient streaming buffers for the new leg.
        textBuffer: "",
      };
    case "ERROR":
      return { ...state, status: "error", error: action.error };
    case "RESET":
      return INITIAL_STATE;
    case "EVENT":
      return applyEvent(state, action.event);
    default:
      return state;
  }
}

function applyEvent(state: RunState, event: AGUIEvent): RunState {
  const next: RunState = { ...state, events: [...state.events, event] };

  switch (event.type) {
    case "NODE_STARTED":
      next.currentNode = event.data.node;
      next.nodeLabel = event.data.label;
      return next;

    case "TEXT_MESSAGE_CONTENT": {
      const chunk = extractTextChunk(event);
      if (chunk) next.textBuffer = state.textBuffer + chunk;
      return next;
    }

    case "TOOL_CALL_START": {
      const id = `tc-${state.toolCalls.length}-${Date.now()}`;
      const record: ToolCallRecord = {
        id,
        name: event.data.name ?? "(unnamed)",
        input: event.data.input,
        status: "running",
        startedAt: Date.now(),
      };
      next.toolCalls = [...state.toolCalls, record];
      return next;
    }

    case "TOOL_CALL_END": {
      // Match the most recent running tool call (queue order).
      const idx = [...state.toolCalls]
        .map((t, i) => ({ t, i }))
        .reverse()
        .find(({ t }) => t.status === "running")?.i;
      if (idx === undefined) return next;
      const updated = [...state.toolCalls];
      updated[idx] = {
        ...updated[idx],
        output: event.data.output,
        status: "completed",
        endedAt: Date.now(),
      };
      next.toolCalls = updated;
      return next;
    }

    case "INTERRUPT":
      next.status = "awaiting_human";
      next.interrupt = { message: event.data.message };
      return next;

    case "RUN_FINISHED":
      next.finalSummary = event.data;
      return next;

    case "RUN_ERROR":
      next.status = "error";
      next.error = event.data.error ?? "Unknown error";
      return next;

    case "DONE":
      // Only flip to "done" if the stream wasn't already terminated by an
      // error or paused for human review.
      if (state.status === "running") next.status = "done";
      return next;

    default:
      return next;
  }
}

export interface UseAgenticRunResult extends RunState {
  start: (input: { task: string; target_repo: string }) => Promise<void>;
  resume: (input: { approved: boolean; instructions?: string }) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

export function useAgenticRun(): UseAgenticRunResult {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);
  const threadIdRef = useRef<string | null>(null);

  const consume = useCallback(async (response: Response, signal: AbortSignal) => {
    try {
      for await (const event of readSSE<AGUIEvent>(response, signal)) {
        dispatch({ type: "EVENT", event });
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      dispatch({ type: "ERROR", error: (err as Error).message });
    }
  }, []);

  const start = useCallback(
    async ({ task, target_repo }: { task: string; target_repo: string }) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const threadId = crypto.randomUUID();
      threadIdRef.current = threadId;

      dispatch({ type: "START", threadId, task, targetRepo: target_repo });

      try {
        const response = await runTask(
          { task, target_repo, thread_id: threadId },
          controller.signal,
        );
        await consume(response, controller.signal);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        dispatch({ type: "ERROR", error: (err as Error).message });
      }
    },
    [consume],
  );

  const resume = useCallback(
    async ({
      approved,
      instructions = "",
    }: {
      approved: boolean;
      instructions?: string;
    }) => {
      const threadId = threadIdRef.current;
      if (!threadId) {
        dispatch({ type: "ERROR", error: "No active thread to resume." });
        return;
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: "RESUME_SENT" });

      try {
        const response = await resumeTask(
          { thread_id: threadId, approved, instructions },
          controller.signal,
        );
        await consume(response, controller.signal);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        dispatch({ type: "ERROR", error: (err as Error).message });
      }
    },
    [consume],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    threadIdRef.current = null;
    dispatch({ type: "RESET" });
  }, []);

  return { ...state, start, resume, cancel, reset };
}
