from __future__ import annotations

import sqlite3
from functools import partial
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from pod_brain.agents.architect import architect_node
from pod_brain.agents.builder import builder_node
from pod_brain.agents.qa import qa_node
from pod_brain.config import settings
from pod_brain.graph.state import HumanDecision, PodState, QAResult
from pod_brain.tools import AgentToolsets

# ── Supervisor (pure routing function — no LLM call) ─────────────────────────

def supervisor_node(state: PodState) -> dict:
    """
    Reads state and returns the next routing target.
    Fires an explicit interrupt() before the first Builder invocation so the
    human can review the design plan before any code is written to the target repo.
    QA→Builder loop-backs are NOT interrupted.
    """
    node = state.get("current_node", "start")
    qa: QAResult | None = state.get("qa_result")

    if node == "start":
        return {"next_node": "architect", "current_node": "supervisor"}

    if node == "architect":
        if state["builder_iterations"] == 0:
            # First build: pause for human design review
            interrupt("Review the design plan before the Builder writes to the target repo.")
        return {"next_node": "builder", "current_node": "supervisor"}

    if node == "qa" and qa is not None:
        if qa.passed:
            return {"next_node": "human_review", "awaiting_human": True, "current_node": "supervisor"}
        if qa.failure_category == "implementation_error":
            if state["builder_iterations"] < state["max_builder_loops"]:
                return {"next_node": "builder", "current_node": "supervisor"}
            return {"next_node": "human_review", "awaiting_human": True, "current_node": "supervisor"}
        if qa.failure_category == "design_error":
            if state["architect_iterations"] < state["max_architect_loops"]:
                return {"next_node": "architect", "current_node": "supervisor"}
            return {"next_node": "human_review", "awaiting_human": True, "current_node": "supervisor"}
        # environment_error or unknown → escalate
        return {"next_node": "human_review", "awaiting_human": True, "current_node": "supervisor"}

    if node == "human_review":
        decision: HumanDecision | None = state.get("human_decision")
        if decision and decision.approved:
            return {"next_node": "done", "status": "done", "current_node": "supervisor"}
        if decision and decision.override_target:
            return {"next_node": decision.override_target, "current_node": "supervisor"}
        return {"next_node": "done", "status": "failed", "current_node": "supervisor"}

    return {"next_node": "done", "current_node": "supervisor"}


def _human_review_passthrough(state: PodState) -> dict:
    """Passthrough — reached only after the human resumes via graph.update_state()."""
    return {"current_node": "human_review", "awaiting_human": False}


# ── Conditional edge functions ────────────────────────────────────────────────

def _route_from_supervisor(state: PodState) -> str:
    return state.get("next_node", "done")


def _route_from_builder(state: PodState) -> Literal["tool_executor", "qa"]:
    """If the last message has tool calls, run the tool executor; otherwise go to QA."""
    messages = state.get("messages", [])
    last = messages[-1] if messages else None
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tool_executor"
    return "qa"


# ── Graph factory ─────────────────────────────────────────────────────────────

def build_graph(
    toolsets: AgentToolsets,
    checkpointer_db: str = ":memory:",
):
    """
    Build and compile the PodGraph.

    Args:
        toolsets: per-agent tool lists from load_mcp_tools() or make_mock_toolsets()
        checkpointer_db: SQLite connection string or ":memory:" for tests.
                         Pass a "postgres://..." URL to swap to AsyncPostgresSaver.
    """
    graph_builder = StateGraph(PodState)

    # Bind dependencies via partial so node functions stay independently testable
    architect = partial(architect_node, tools=toolsets.architect)
    builder = partial(builder_node, tools=toolsets.builder)
    qa = partial(qa_node, tools=toolsets.qa)
    tool_executor = ToolNode(toolsets.builder)

    graph_builder.add_node("supervisor", supervisor_node)
    graph_builder.add_node("architect", architect)
    graph_builder.add_node("builder", builder)
    graph_builder.add_node("tool_executor", tool_executor)
    graph_builder.add_node("qa", qa)
    graph_builder.add_node("human_review", _human_review_passthrough)

    graph_builder.set_entry_point("supervisor")

    graph_builder.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "architect": "architect",
            "builder": "builder",
            "human_review": "human_review",
            "done": END,
        },
    )
    graph_builder.add_edge("architect", "supervisor")
    graph_builder.add_conditional_edges(
        "builder",
        _route_from_builder,
        {"tool_executor": "tool_executor", "qa": "qa"},
    )
    graph_builder.add_edge("tool_executor", "builder")
    graph_builder.add_edge("qa", "supervisor")
    graph_builder.add_edge("human_review", "supervisor")

    # ── Checkpointer selection ────────────────────────────────────────────
    # from_conn_string() on Async*Saver classes returns an async context manager
    # (not a direct instance) and cannot be passed to compile() directly.
    # Use sync variants here; async Postgres setup is handled in get_graph().
    if checkpointer_db == ":memory:":
        checkpointer = MemorySaver()
    elif checkpointer_db.startswith("postgres"):
        raise NotImplementedError(
            "Postgres checkpointer requires async setup. "
            "Call get_graph() instead of build_graph() for production use."
        )
    else:
        conn = sqlite3.connect(checkpointer_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

    return graph_builder.compile(checkpointer=checkpointer)


# ── Lazy singleton used by studio-api ────────────────────────────────────────

_graph_instance = None


async def get_graph(
    toolsets: AgentToolsets | None = None,
    db_path: str | None = None,
):
    """
    Async factory. Builds and caches the compiled graph on first call.
    Call from FastAPI's lifespan handler so the checkpointer connection is
    established at startup rather than on the first request.

    Checkpointer selection:
      ":memory:"    → MemorySaver (in-process, lost on restart)
      file path     → SqliteSaver (persistent, single-process)
      "postgres://…" → AsyncPostgresSaver (persistent, multi-process safe)
    """
    global _graph_instance
    if _graph_instance is None:
        from pod_brain.tools import load_mcp_tools
        ts = toolsets or await load_mcp_tools()
        resolved_db = db_path or settings.checkpointer_db

        if resolved_db.startswith("postgres"):
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            except ImportError as exc:
                raise ImportError(
                    "Postgres checkpointer requires an extra dependency. "
                    "Install it with:  pip install 'pod-brain[postgres]'"
                ) from exc
            # Keep the context manager open for the process lifetime.
            # FastAPI lifespan is responsible for graceful shutdown.
            async with AsyncPostgresSaver.from_conn_string(resolved_db) as pg_checkpointer:
                _graph_instance = _compile_graph(ts, pg_checkpointer)
        else:
            _graph_instance = build_graph(toolsets=ts, checkpointer_db=resolved_db)

    return _graph_instance


def _compile_graph(toolsets: AgentToolsets, checkpointer):
    """Internal helper used by get_graph() to build with a pre-created checkpointer."""
    graph_builder = StateGraph(PodState)
    architect = partial(architect_node, tools=toolsets.architect)
    builder = partial(builder_node, tools=toolsets.builder)
    qa = partial(qa_node, tools=toolsets.qa)
    tool_executor = ToolNode(toolsets.builder)

    graph_builder.add_node("supervisor", supervisor_node)
    graph_builder.add_node("architect", architect)
    graph_builder.add_node("builder", builder)
    graph_builder.add_node("tool_executor", tool_executor)
    graph_builder.add_node("qa", qa)
    graph_builder.add_node("human_review", _human_review_passthrough)

    graph_builder.set_entry_point("supervisor")
    graph_builder.add_conditional_edges(
        "supervisor", _route_from_supervisor,
        {"architect": "architect", "builder": "builder", "human_review": "human_review", "done": END},
    )
    graph_builder.add_edge("architect", "supervisor")
    graph_builder.add_conditional_edges(
        "builder", _route_from_builder, {"tool_executor": "tool_executor", "qa": "qa"},
    )
    graph_builder.add_edge("tool_executor", "builder")
    graph_builder.add_edge("qa", "supervisor")
    graph_builder.add_edge("human_review", "supervisor")

    return graph_builder.compile(checkpointer=checkpointer)
