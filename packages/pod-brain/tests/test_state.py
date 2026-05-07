import operator

import pytest
from pydantic import ValidationError

from pod_brain.graph.state import DesignPlan, HumanDecision, PodState, QAResult


def _base_state() -> PodState:
    return {
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


def test_pod_state_instantiates():
    state = _base_state()
    assert state["task"] == "Build a login form"
    assert state["status"] == "running"
    assert state["messages"] == []


def test_design_plan_validates():
    plan = DesignPlan(
        summary="Add a login form",
        files_to_create=["src/LoginForm.tsx"],
        files_to_modify=["src/App.tsx"],
        branch_name="feat/login-form-a1b2c3d4",
    )
    assert plan.branch_name == "feat/login-form-a1b2c3d4"
    assert plan.constraints == []


def test_qa_result_validates():
    result = QAResult(
        passed=False,
        score=0.3,
        failures=["ruff: E501 line too long"],
        feedback="Fix linting errors.",
        failure_category="implementation_error",
    )
    assert not result.passed
    assert result.failure_category == "implementation_error"


def test_qa_result_score_bounds():
    with pytest.raises(ValidationError):
        QAResult(
            passed=False,
            score=1.5,
            failures=[],
            feedback="bad",
            failure_category="implementation_error",
        )


def test_human_decision_validates():
    d = HumanDecision(approved=True, comment="Looks good")
    assert d.approved
    assert d.override_target is None


def test_messages_reducer_accumulates():
    # Simulate how LangGraph applies operator.add across two state updates
    initial: list = []
    update1 = ["msg1"]
    update2 = ["msg2", "msg3"]
    result = operator.add(operator.add(initial, update1), update2)
    assert result == ["msg1", "msg2", "msg3"]


def test_files_written_reducer_accumulates():
    initial: list[str] = []
    after_first_build = operator.add(initial, ["src/LoginForm.tsx"])
    after_second_build = operator.add(after_first_build, ["src/LoginForm.test.tsx"])
    assert after_second_build == ["src/LoginForm.tsx", "src/LoginForm.test.tsx"]
