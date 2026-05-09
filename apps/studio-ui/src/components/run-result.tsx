"use client";

import { CheckCircle2, ExternalLink, FileText, GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { UseAgenticRunResult } from "@/hooks/use-agentic-run";

interface RunResultProps {
  run: UseAgenticRunResult;
}

export function RunResult({ run }: RunResultProps) {
  if (run.status !== "done" && run.status !== "error") return null;

  const summary = (run.finalSummary ?? {}) as {
    output?: { values?: Record<string, unknown> } | unknown;
    [k: string]: unknown;
  };

  // The shape of RUN_FINISHED data depends on LangGraph's astream_events output;
  // we look for likely fields, with graceful fallbacks.
  const values =
    (summary as { output?: { values?: Record<string, unknown> } }).output
      ?.values ?? (summary as Record<string, unknown>);
  const filesWritten = asStringArray(values["files_written"]);
  const branchName = asString(values["branch_name"]);
  const prUrl = asString(values["pr_url"]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          {run.status === "done" ? (
            <CheckCircle2 className="h-5 w-5 text-[var(--primary)]" />
          ) : (
            <CheckCircle2 className="h-5 w-5 text-[var(--destructive)]" />
          )}
          <CardTitle>
            {run.status === "done" ? "Run completed" : "Run ended with error"}
          </CardTitle>
        </div>
        <CardDescription>
          Thread {run.threadId?.slice(0, 8)}…
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {branchName && (
          <div className="flex items-center gap-2 text-sm">
            <GitBranch className="h-4 w-4 text-[var(--muted-foreground)]" />
            <span className="font-mono">{branchName}</span>
          </div>
        )}
        {prUrl && (
          <a
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-[var(--primary)] hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            View pull request
          </a>
        )}
        {filesWritten.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-sm font-medium">Files written</p>
            <ul className="flex flex-col gap-1">
              {filesWritten.map((f) => (
                <li
                  key={f}
                  className="flex items-center gap-2 text-xs font-mono text-[var(--muted-foreground)]"
                >
                  <FileText className="h-3 w-3" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )}
        {run.error && (
          <pre className="rounded-[var(--radius)] border border-[var(--destructive)] bg-[var(--destructive)]/10 p-3 text-xs font-mono whitespace-pre-wrap">
            {run.error}
          </pre>
        )}
        <Button variant="outline" onClick={run.reset} className="self-start">
          New run
        </Button>
      </CardContent>
    </Card>
  );
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}
