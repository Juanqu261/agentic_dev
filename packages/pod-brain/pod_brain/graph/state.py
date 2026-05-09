from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


class DesignPlan(BaseModel):
    summary: str
    files_to_create: list[str]
    files_to_modify: list[str]
    branch_name: str = Field(description="kebab-case branch name, e.g. feat/login-form-a1b2c3d4")
    tech_context: list[str] = Field(default_factory=list, description="relevant snippets from pod-memory")
    constraints: list[str] = Field(default_factory=list, description="architectural rules Builder must respect")


class QAResult(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    failures: list[str] = Field(default_factory=list)
    feedback: str
    failure_category: Literal["none", "implementation_error", "design_error", "environment_error"]


class HumanDecision(BaseModel):
    approved: bool
    comment: str = ""
    override_target: Literal["builder", "architect", "done"] | None = None


class PodState(TypedDict):
    # ── Input (set once at invocation) ───────────────────────────────────
    task: str
    target_repo: str
    thread_id: str

    # ── Routing ──────────────────────────────────────────────────────────
    current_node: str
    next_node: str

    # ── Loop control ─────────────────────────────────────────────────────
    builder_iterations: int
    architect_iterations: int
    max_builder_loops: int
    max_architect_loops: int

    # ── Accumulated (operator.add reducer appends across updates) ────────
    messages: Annotated[list[Any], operator.add]
    files_written: Annotated[list[str], operator.add]

    # ── Agent outputs (last-writer wins) ─────────────────────────────────
    design_plan: DesignPlan | None
    qa_result: QAResult | None

    # ── Human-in-the-loop ────────────────────────────────────────────────
    human_decision: HumanDecision | None
    awaiting_human: bool
    human_instructions: str

    # ── Artifacts ────────────────────────────────────────────────────────
    branch_name: str | None
    pr_url: str | None
    error: str | None
    status: Literal["running", "awaiting_human", "done", "failed"]
