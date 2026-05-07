"""
Graph-level tests. Mocks all three agent nodes so no LLM or MCP calls occur.
Uses MemorySaver (in-process, no disk I/O).

LangGraph 0.3+ interrupt behaviour:
  - ainvoke() does NOT raise GraphInterrupt. It returns the partial state
    and saves the interrupt to the checkpointer.
  - graph.get_state(config).next is non-empty when the graph is paused.
  - Resume by calling ainvoke(None, config=config) after optionally injecting
    state via aupdate_state().
"""
import pytest
from langgraph.types import Command

from pod_brain.graph.pod_graph import build_graph
from pod_brain.graph.state import DesignPlan, HumanDecision, PodState, QAResult
from pod_brain.tools import make_mock_toolsets


def _initial_state(thread_id: str = "test-thread") -> PodState:
    return {
        "task": "Build a login form",
        "target_repo": "/tmp/fake-repo",
        "thread_id": thread_id,
        "current_node": "start",
        "next_node": "supervisor",
        "builder_iterations": 0,
        "architect_iterations": 0,
        "max_builder_loops": 3,
        "max_architect_loops": 2,
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


def _fake_plan() -> DesignPlan:
    return DesignPlan(
        summary="Login form plan",
        files_to_create=["src/LoginForm.tsx"],
        files_to_modify=[],
        branch_name="feat/login-form-a1b2c3d4",
    )


def _passing_qa() -> QAResult:
    return QAResult(
        passed=True,
        score=1.0,
        failures=[],
        feedback="All good.",
        failure_category="none",
    )


def _failing_qa() -> QAResult:
    return QAResult(
        passed=False,
        score=0.3,
        failures=["lint error"],
        feedback="Fix linting.",
        failure_category="implementation_error",
    )


# ── Static graph structure ────────────────────────────────────────────────────

def test_graph_builds_without_error():
    graph = build_graph(make_mock_toolsets(), checkpointer_db=":memory:")
    assert graph is not None
    nodes = graph.get_graph().nodes
    assert "supervisor" in nodes
    assert "architect" in nodes
    assert "builder" in nodes
    assert "qa" in nodes
    assert "human_review" in nodes


# ── Happy path: graph pauses at design-review interrupt ──────────────────────

@pytest.mark.asyncio
async def test_happy_path_pauses_at_design_review(mocker):
    """
    Graph should run supervisor → architect → supervisor → interrupt (design review).
    In LangGraph 0.3+, ainvoke() returns partial state instead of raising GraphInterrupt.
    The paused state is confirmed via graph.get_state(config).next being non-empty.

    Patch target must be pod_brain.graph.pod_graph.architect_node (the name used
    inside build_graph via partial()), NOT the source module reference.
    """
    mocker.patch(
        "pod_brain.graph.pod_graph.architect_node",
        new=mocker.AsyncMock(return_value={
            "design_plan": _fake_plan(),
            "current_node": "architect",
            "next_node": "supervisor",
            "architect_iterations": 1,
            "messages": [],
            "status": "running",
        }),
    )

    graph = build_graph(make_mock_toolsets(), checkpointer_db=":memory:")
    config = {"configurable": {"thread_id": "test-happy"}}

    # ainvoke() returns partial state when interrupted (does not raise in LG 0.3+)
    await graph.ainvoke(_initial_state("test-happy"), config=config)

    # Graph should be paused — next is the node waiting to resume
    snapshot = graph.get_state(config)
    assert snapshot.next, (
        "Expected graph to be paused at design-review interrupt, "
        f"but get_state().next is empty: {snapshot}"
    )


# ── QA loop-back: builder runs twice when QA fails once ──────────────────────

@pytest.mark.asyncio
async def test_qa_loop_back_to_builder(mocker):
    """
    Full flow with fakes:
      1. ainvoke() → architect runs → interrupt fires (design review)
      2. Inject human approval → resume
      3. builder runs → qa fails (impl error) → builder runs again → qa passes
      4. Graph pauses at human_review (PR gate)

    Asserts: architect ran once, builder ran at least twice.
    """
    architect_call_count = 0
    builder_call_count = 0
    qa_call_count = 0

    async def fake_architect(state, **_):
        nonlocal architect_call_count
        architect_call_count += 1
        return {
            "design_plan": _fake_plan(),
            "current_node": "architect",
            "next_node": "supervisor",
            "architect_iterations": state["architect_iterations"] + 1,
            "messages": [],
            "status": "running",
        }

    async def fake_builder(state, **_):
        nonlocal builder_call_count
        builder_call_count += 1
        return {
            "files_written": ["src/LoginForm.tsx"],
            "branch_name": "feat/x",
            "current_node": "builder",
            "next_node": "supervisor",
            "builder_iterations": state["builder_iterations"] + 1,
            "messages": [],
            "status": "running",
        }

    qa_results = [_failing_qa(), _passing_qa()]

    async def fake_qa(state, **_):
        nonlocal qa_call_count
        result = qa_results[min(qa_call_count, len(qa_results) - 1)]
        qa_call_count += 1
        return {
            "qa_result": result,
            "current_node": "qa",
            "next_node": "supervisor",
            "messages": [],
            "status": "running",
        }

    # Patch inside pod_graph module — where partial() resolves the names
    mocker.patch("pod_brain.graph.pod_graph.architect_node", fake_architect)
    mocker.patch("pod_brain.graph.pod_graph.builder_node", fake_builder)
    mocker.patch("pod_brain.graph.pod_graph.qa_node", fake_qa)

    graph = build_graph(make_mock_toolsets(), checkpointer_db=":memory:")
    config = {"configurable": {"thread_id": "test-qa-loop"}}

    # ── Pass 1: runs to design-review interrupt ───────────────────────────────
    await graph.ainvoke(_initial_state("test-qa-loop"), config=config)
    snapshot = graph.get_state(config)
    assert snapshot.next, "Graph should be paused at design-review interrupt after first invocation"

    # ── Resume: human approves the design plan ────────────────────────────────
    # Command(resume=...) passes a value back to the interrupt() call inside
    # supervisor_node, allowing it to return instead of pausing again.
    # Pre-inject HumanDecision so the final human_review gate auto-approves.
    await graph.aupdate_state(config, {"human_decision": HumanDecision(approved=True)})
    await graph.ainvoke(Command(resume=True), config=config)

    # ── Assertions ────────────────────────────────────────────────────────────
    assert architect_call_count == 1, f"Architect should run once, ran {architect_call_count}"
    assert builder_call_count >= 2, (
        f"Builder should run at least twice (QA fail → retry), ran {builder_call_count}"
    )
