from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pod_brain import HumanDecision, PodState, get_graph

router = APIRouter(prefix="/api", tags=["agui"])

_AGUI_MAP: dict[str, str] = {
    "on_chain_start": "RUN_STARTED",
    "on_chain_end": "RUN_FINISHED",
    "on_chain_error": "RUN_ERROR",
    "on_tool_start": "TOOL_CALL_START",
    "on_tool_end": "TOOL_CALL_END",
    "on_chat_model_stream": "TEXT_MESSAGE_CONTENT",
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
    comment: str = ""
    override_target: str | None = None


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
        "files_written": [],
        "branch_name": None,
        "pr_url": None,
        "error": None,
        "status": "running",
    }
    config = {"configurable": {"thread_id": payload.thread_id}}

    async def event_stream():
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            agui_type = _AGUI_MAP.get(event["event"])
            if agui_type:
                yield f"data: {json.dumps({'type': agui_type, 'data': event.get('data', {})})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/resume")
async def resume_task(payload: ResumeRequest):
    """Resume a paused run after a human-review interrupt."""
    graph = await get_graph()
    config = {"configurable": {"thread_id": payload.thread_id}}

    decision = HumanDecision(
        approved=payload.approved,
        comment=payload.comment,
        override_target=payload.override_target,
    )
    await graph.aupdate_state(config, {"human_decision": decision, "awaiting_human": False})

    async def event_stream():
        async for event in graph.astream_events(None, config=config, version="v2"):
            agui_type = _AGUI_MAP.get(event["event"])
            if agui_type:
                yield f"data: {json.dumps({'type': agui_type, 'data': event.get('data', {})})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
