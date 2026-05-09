"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { UseAgenticRunResult } from "@/hooks/use-agentic-run";

interface HumanReviewModalProps {
  run: UseAgenticRunResult;
}

export function HumanReviewModal({ run }: HumanReviewModalProps) {
  const open = run.status === "awaiting_human" && run.interrupt !== null;
  const [instructions, setInstructions] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Clear the textarea every time a new interrupt arrives.
  useEffect(() => {
    if (open) setInstructions("");
  }, [open, run.interrupt?.message]);

  const handleDecision = async (approved: boolean) => {
    setSubmitting(true);
    try {
      await run.resume({ approved, instructions: instructions.trim() });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Human review required</DialogTitle>
          <DialogDescription>
            {run.interrupt?.message ?? ""}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor="instructions">Instructions (optional)</Label>
          <Textarea
            id="instructions"
            placeholder="Add notes for the agent (e.g. constraints, things to keep, things to avoid)…"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={4}
            disabled={submitting}
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleDecision(false)}
            disabled={submitting}
          >
            Reject
          </Button>
          <Button
            onClick={() => handleDecision(true)}
            disabled={submitting}
          >
            Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
