"use client";

import { useEffect, useRef } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Cog,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { UseAgenticRunResult } from "@/hooks/use-agentic-run";
import type { AGUIEvent, ToolCallRecord } from "@/lib/agui-events";

interface ProgressDashboardProps {
  run: UseAgenticRunResult;
}

const STATUS_VARIANTS: Record<
  UseAgenticRunResult["status"],
  { label: string; className: string }
> = {
  idle: { label: "idle", className: "" },
  running: {
    label: "running",
    className:
      "bg-[var(--accent)] text-[var(--accent-foreground)] border-transparent",
  },
  awaiting_human: {
    label: "awaiting human review",
    className:
      "bg-[var(--secondary)] text-[var(--secondary-foreground)] border-transparent",
  },
  done: {
    label: "done",
    className:
      "bg-[var(--primary)] text-[var(--primary-foreground)] border-transparent",
  },
  error: {
    label: "error",
    className:
      "bg-[var(--destructive)] text-[var(--destructive-foreground)] border-transparent",
  },
};

export function ProgressDashboard({ run }: ProgressDashboardProps) {
  const variant = STATUS_VARIANTS[run.status];
  const isStreaming = run.status === "running";

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <CardTitle>Run</CardTitle>
              <Badge className={cn("uppercase", variant.className)}>
                {variant.label}
              </Badge>
            </div>
            {run.threadId && (
              <p className="text-xs font-mono text-[var(--muted-foreground)]">
                thread: {run.threadId.slice(0, 8)}…
              </p>
            )}
            {run.task && (
              <p className="text-sm text-[var(--muted-foreground)] line-clamp-2 max-w-2xl">
                {run.task}
              </p>
            )}
          </div>
          {isStreaming && (
            <Button variant="outline" size="sm" onClick={run.cancel}>
              Cancel
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <CurrentNode
            label={run.nodeLabel}
            node={run.currentNode}
            running={isStreaming}
          />
          {run.error && (
            <div className="mt-4 flex items-start gap-2 rounded-[var(--radius)] border border-[var(--destructive)] bg-[var(--destructive)]/10 p-3 text-sm">
              <AlertTriangle className="h-4 w-4 mt-0.5 text-[var(--destructive)]" />
              <span className="font-mono text-xs">{run.error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      <ActivityLog
        events={run.events}
        toolCalls={run.toolCalls}
        textBuffer={run.textBuffer}
      />
    </div>
  );
}

function CurrentNode({
  label,
  node,
  running,
}: {
  label: string | null;
  node: string | null;
  running: boolean;
}) {
  if (!label && !running) {
    return (
      <p className="text-sm text-[var(--muted-foreground)]">
        Waiting for the first event…
      </p>
    );
  }
  return (
    <div className="flex items-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--secondary)] p-4">
      {running ? (
        <Spinner size="sm" />
      ) : (
        <CheckCircle2 className="h-4 w-4 text-[var(--primary)]" />
      )}
      <div className="flex flex-col">
        <span className="text-sm font-medium">
          {label ?? "Initialising…"}
        </span>
        {node && (
          <span className="text-xs font-mono text-[var(--muted-foreground)]">
            node: {node}
          </span>
        )}
      </div>
    </div>
  );
}

function ActivityLog({
  events,
  toolCalls,
  textBuffer,
}: {
  events: AGUIEvent[];
  toolCalls: ToolCallRecord[];
  textBuffer: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length, textBuffer.length]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          ref={scrollRef}
          className="flex flex-col gap-2 max-h-[480px] overflow-y-auto"
        >
          {events.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              No events yet.
            </p>
          )}
          {events.map((event, i) => (
            <ActivityRow key={i} event={event} toolCalls={toolCalls} />
          ))}
          {textBuffer && (
            <div className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--background)] p-3 whitespace-pre-wrap text-sm font-mono">
              {textBuffer}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityRow({
  event,
  toolCalls,
}: {
  event: AGUIEvent;
  toolCalls: ToolCallRecord[];
}) {
  switch (event.type) {
    case "NODE_STARTED":
      return (
        <div className="flex items-center gap-2 text-sm">
          <ChevronRight className="h-4 w-4 text-[var(--muted-foreground)]" />
          <span className="font-medium">{event.data.label}</span>
          <span className="font-mono text-xs text-[var(--muted-foreground)]">
            {event.data.node}
          </span>
        </div>
      );
    case "TOOL_CALL_START":
    case "TOOL_CALL_END": {
      const name = event.data.name ?? "(unnamed)";
      const record = toolCalls.find((t) => t.name === name);
      return <ToolCallRow record={record} fallbackName={name} />;
    }
    case "RUN_ERROR":
      return (
        <div className="flex items-start gap-2 text-sm text-[var(--destructive)]">
          <XCircle className="h-4 w-4 mt-0.5" />
          <span className="font-mono text-xs">
            {event.data.error ?? "error"}
          </span>
        </div>
      );
    case "INTERRUPT":
      return (
        <div className="flex items-start gap-2 text-sm">
          <AlertTriangle className="h-4 w-4 mt-0.5 text-[var(--accent-foreground)]" />
          <div className="flex flex-col">
            <span className="font-medium">Awaiting human review</span>
            <span className="text-xs text-[var(--muted-foreground)]">
              {event.data.message}
            </span>
          </div>
        </div>
      );
    case "RUN_FINISHED":
      return (
        <div className="flex items-center gap-2 text-sm">
          <CheckCircle2 className="h-4 w-4 text-[var(--primary)]" />
          <span>Run finished</span>
        </div>
      );
    case "DONE":
      return (
        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
          <CheckCircle2 className="h-4 w-4" />
          <span className="text-xs">Stream closed</span>
        </div>
      );
    case "TEXT_MESSAGE_CONTENT":
    case "RUN_STARTED":
      // Streamed text is rendered separately; RUN_STARTED is implicit.
      return null;
    default:
      return null;
  }
}

function ToolCallRow({
  record,
  fallbackName,
}: {
  record: ToolCallRecord | undefined;
  fallbackName: string;
}) {
  return (
    <details className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--background)] p-2 text-sm group">
      <summary className="flex items-center gap-2 cursor-pointer list-none">
        <Cog
          className={cn(
            "h-4 w-4 text-[var(--muted-foreground)]",
            record?.status === "running" && "animate-spin",
          )}
        />
        <span className="font-medium">{record?.name ?? fallbackName}</span>
        {record && (
          <Badge variant="outline" className="ml-auto text-[10px]">
            {record.status}
          </Badge>
        )}
      </summary>
      {record && (
        <div className="mt-2 grid gap-2 text-xs font-mono">
          {record.input !== undefined && (
            <pre className="bg-[var(--secondary)] rounded p-2 overflow-x-auto whitespace-pre-wrap">
              {safeStringify(record.input)}
            </pre>
          )}
          {record.output !== undefined && (
            <pre className="bg-[var(--secondary)] rounded p-2 overflow-x-auto whitespace-pre-wrap">
              {safeStringify(record.output)}
            </pre>
          )}
        </div>
      )}
    </details>
  );
}

function safeStringify(value: unknown): string {
  try {
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
