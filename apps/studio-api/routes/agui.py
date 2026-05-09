from __future__ import annotations

import json
from typing import AsyncGenerator


def _json_default(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langgraph.types import Command

from pod_brain import PodState, get_graph

router = APIRouter(prefix="/api", tags=["agui"])

_AGUI_MAP: dict[str, str] = {
    "on_chain_start": "RUN_STARTED",
    "on_chain_end": "RUN_FINISHED",
    "on_chain_error": "RUN_ERROR",
    "on_tool_start": "TOOL_CALL_START",
    "on_tool_end": "TOOL_CALL_END",
    "on_chat_model_stream": "TEXT_MESSAGE_CONTENT",
}

_NODE_LABELS: dict[str, str] = {
    "architect": "Architect is planning...",
    "builder": "Builder is writing code...",
    "qa": "QA is testing...",
    "supervisor": "Supervisor is routing...",
    "human_review": "Awaiting human review...",
    "tool_executor": "Executing tools...",
}


class RunRequest(BaseModel):
    task: str
    target_repo: str
    thread_id: str
    max_builder_loops: int = 3
    max_architect_loops: int = 2


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool
    instructions: str = ""


async def _stream_events(graph, initial_state, config) -> AsyncGenerator[str, None]:
    """Shared SSE generator for both /run and /resume."""
    interrupt_emitted = False

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            etype = event["event"]
            ename = event.get("name", "")

            # 1. Interrupt — explicit on_interrupt event (LangGraph may or may not emit this)
            if etype == "on_interrupt":
                interrupt_emitted = True
                payload = {
                    "type": "INTERRUPT",
                    "data": {
                        "message": event.get("data", {}).get("value", "Human review required."),
                        "thread_id": config["configurable"]["thread_id"],
                    },
                }
                yield f"data: {json.dumps(payload, default=_json_default)}\n\n"
                continue

            # 2. Node-level progress label
            if etype == "on_chain_start" and ename in _NODE_LABELS:
                label_payload = {
                    "type": "NODE_STARTED",
                    "data": {"node": ename, "label": _NODE_LABELS[ename]},
                }
                yield f"data: {json.dumps(label_payload, default=_json_default)}\n\n"

            # 3. Generic map
            if agui_type := _AGUI_MAP.get(etype):
                yield f"data: {json.dumps({'type': agui_type, 'data': event.get('data', {})}, default=_json_default)}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'RUN_ERROR', 'data': {'error': str(exc)}})}\n\n"

    # Fallback: detect interrupt via checkpoint state if the event wasn't surfaced
    if not interrupt_emitted:
        snapshot = await graph.aget_state(config)
        if snapshot.next:
            interrupts = [i for task in snapshot.tasks for i in getattr(task, "interrupts", [])]
            message = str(interrupts[0].value) if interrupts else "Human review required."
            payload = {
                "type": "INTERRUPT",
                "data": {"message": message, "thread_id": config["configurable"]["thread_id"]},
            }
            yield f"data: {json.dumps(payload, default=_json_default)}\n\n"

    yield 'data: {"type": "DONE"}\n\n'


@router.post("/run")
async def run_task(payload: RunRequest):
    """Start a new agent run. Returns an SSE stream of AG-UI events."""
    graph = await get_graph()

    initial_state: PodState = {
        "task": payload.task,
        "target_repo": payload.target_repo,
        "thread_id": payload.thread_id,
        "current_node": "start",
        "next_node": "supervisor",
        "builder_iterations": 0,
        "architect_iterations": 0,
        "max_builder_loops": payload.max_builder_loops,
        "max_architect_loops": payload.max_architect_loops,
        "messages": [],
        "design_plan": None,
        "qa_result": None,
        "human_decision": None,
        "awaiting_human": False,
        "human_instructions": "",
        "files_written": [],
        "branch_name": None,
        "pr_url": None,
        "error": None,
        "status": "running",
    }
    config = {"configurable": {"thread_id": payload.thread_id}}

    return StreamingResponse(_stream_events(graph, initial_state, config), media_type="text/event-stream")


@router.post("/resume")
async def resume_task(payload: ResumeRequest):
    """Resume a paused run after a human-review interrupt."""
    graph = await get_graph()
    config = {"configurable": {"thread_id": payload.thread_id}}

    # Command(resume=...) passes the value back to the interrupt() call inside the graph.
    # approved=True routes to builder; False routes to done/failed.
    command = Command(resume={"approved": payload.approved, "instructions": payload.instructions})

    return StreamingResponse(_stream_events(graph, command, config), media_type="text/event-stream")
