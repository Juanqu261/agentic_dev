"""
Pure unit tests for supervisor_node routing logic.
No LLM calls, no async, no external services.
"""
import pytest

from pod_brain.graph.pod_graph import supervisor_node
from pod_brain.graph.state import HumanDecision, PodState, QAResult


def _base_state(**overrides) -> PodState:
    state: PodState = {
        "task": "Build a login form",
        "target_repo": "/tmp/fake-repo",
        "thread_id": "user1-req1",
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
    state.update(overrides)
    return state


def _qa(passed: bool, category: str, score: float = 0.9) -> QAResult:
    return QAResult(
        passed=passed,
        score=score,
        failures=[] if passed else ["some failure"],
        feedback="ok" if passed else "fix this",
        failure_category="none" if passed else category,
    )


# ── start → architect ────────────────────────────────────────────────────────

def test_start_routes_to_architect():
    result = supervisor_node(_base_state(current_node="start"))
    assert result["next_node"] == "architect"


# ── architect → builder (with interrupt on first build) ──────────────────────

def test_architect_first_build_triggers_interrupt(mocker):
    mock_interrupt = mocker.patch("pod_brain.graph.pod_graph.interrupt")
    state = _base_state(current_node="architect", builder_iterations=0)
    result = supervisor_node(state)
    mock_interrupt.assert_called_once()
    assert result["next_node"] == "builder"


def test_architect_subsequent_build_no_interrupt(mocker):
    mock_interrupt = mocker.patch("pod_brain.graph.pod_graph.interrupt")
    state = _base_state(current_node="architect", builder_iterations=1)
    result = supervisor_node(state)
    mock_interrupt.assert_not_called()
    assert result["next_node"] == "builder"


# ── qa routing ────────────────────────────────────────────────────────────────

def test_qa_passed_routes_to_human_review():
    state = _base_state(current_node="qa", qa_result=_qa(passed=True, category="none"))
    result = supervisor_node(state)
    assert result["next_node"] == "human_review"
    assert result["awaiting_human"] is True


def test_qa_impl_error_under_limit_routes_to_builder():
    state = _base_state(
        current_node="qa",
        qa_result=_qa(passed=False, category="implementation_error"),
        builder_iterations=1,
        max_builder_loops=3,
    )
    result = supervisor_node(state)
    assert result["next_node"] == "builder"


def test_qa_impl_error_at_limit_escalates_to_human():
    state = _base_state(
        current_node="qa",
        qa_result=_qa(passed=False, category="implementation_error"),
        builder_iterations=3,
        max_builder_loops=3,
    )
    result = supervisor_node(state)
    assert result["next_node"] == "human_review"


def test_qa_design_error_under_limit_routes_to_architect():
    state = _base_state(
        current_node="qa",
        qa_result=_qa(passed=False, category="design_error"),
        architect_iterations=1,
        max_architect_loops=2,
    )
    result = supervisor_node(state)
    assert result["next_node"] == "architect"


def test_qa_design_error_at_limit_escalates_to_human():
    state = _base_state(
        current_node="qa",
        qa_result=_qa(passed=False, category="design_error"),
        architect_iterations=2,
        max_architect_loops=2,
    )
    result = supervisor_node(state)
    assert result["next_node"] == "human_review"


def test_qa_environment_error_always_escalates():
    state = _base_state(
        current_node="qa",
        qa_result=_qa(passed=False, category="environment_error"),
    )
    result = supervisor_node(state)
    assert result["next_node"] == "human_review"


# ── human_review routing ─────────────────────────────────────────────────────

def test_human_review_approved_routes_to_done():
    state = _base_state(
        current_node="human_review",
        human_decision=HumanDecision(approved=True),
    )
    result = supervisor_node(state)
    assert result["next_node"] == "done"
    assert result["status"] == "done"


def test_human_review_rejected_no_override_routes_to_done_failed():
    state = _base_state(
        current_node="human_review",
        human_decision=HumanDecision(approved=False),
    )
    result = supervisor_node(state)
    assert result["next_node"] == "done"
    assert result["status"] == "failed"


def test_human_review_with_override_routes_to_override_target():
    state = _base_state(
        current_node="human_review",
        human_decision=HumanDecision(approved=False, override_target="builder"),
    )
    result = supervisor_node(state)
    assert result["next_node"] == "builder"
