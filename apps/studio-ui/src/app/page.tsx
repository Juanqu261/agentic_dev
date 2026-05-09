"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HumanReviewModal } from "@/components/human-review-modal";
import { ProgressDashboard } from "@/components/progress-dashboard";
import { RunForm } from "@/components/run-form";
import { RunResult } from "@/components/run-result";
import { useAgenticRun } from "@/hooks/use-agentic-run";
import { useTheme } from "@/hooks/use-theme";

export default function HomePage() {
  const run = useAgenticRun();
  const { theme, setTheme } = useTheme();

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-5xl px-6 py-10 flex flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Agentic DevStudio
            </h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              Architect → Builder → QA, with human-in-the-loop review.
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </header>

        {run.status === "idle" ? (
          <RunForm onSubmit={run.start} />
        ) : (
          <ProgressDashboard run={run} />
        )}

        <RunResult run={run} />

        <HumanReviewModal run={run} />
      </div>
    </main>
  );
}
