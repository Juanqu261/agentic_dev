"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface RunFormProps {
  onSubmit: (input: { task: string; target_repo: string }) => void;
  disabled?: boolean;
}

export function RunForm({ onSubmit, disabled }: RunFormProps) {
  const [task, setTask] = useState("");
  const [targetRepo, setTargetRepo] = useState("");

  const isValid = task.trim().length > 0 && targetRepo.trim().length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>New run</CardTitle>
        <CardDescription>
          Describe a development task and point the agent at a target
          repository. The orchestrator (architect → builder → QA) will plan,
          implement, and test the change. You will be asked to review the
          design plan before any code is written.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!isValid || disabled) return;
            onSubmit({ task: task.trim(), target_repo: targetRepo.trim() });
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="task">Task</Label>
            <Textarea
              id="task"
              placeholder="e.g. Add a /healthz endpoint that returns JSON {status: 'ok'}."
              value={task}
              onChange={(e) => setTask(e.target.value)}
              rows={5}
              disabled={disabled}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="target_repo">Target repository path</Label>
            <Input
              id="target_repo"
              placeholder="C:\\Users\\you\\path\\to\\repo"
              value={targetRepo}
              onChange={(e) => setTargetRepo(e.target.value)}
              disabled={disabled}
              required
              spellCheck={false}
            />
            <p className="text-xs text-[var(--muted-foreground)]">
              Absolute path to a local git repository the agent will modify.
            </p>
          </div>
          <Button
            type="submit"
            disabled={!isValid || disabled}
            className="self-start"
          >
            Start run
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
