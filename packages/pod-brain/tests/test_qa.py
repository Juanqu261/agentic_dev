import pytest
from langchain_core.messages import AIMessage

from pod_brain.agents.qa import qa_node
from pod_brain.graph.state import DesignPlan, PodState, QAResult


def _base_state(**overrides) -> PodState:
    plan = DesignPlan(
        summary="Add a login form",
        files_to_create=["src/LoginForm.tsx"],
        files_to_modify=[],
        branch_name="feat/login-form-a1b2c3d4",
        constraints=["must use AuthService"],
    )
    state: PodState = {
        "task": "Build a login form",
        "target_repo": "/tmp/fake-repo",
        "thread_id": "user1-req1",
        "current_node": "builder",
        "next_node": "qa",
        "builder_iterations": 1,
        "architect_iterations": 1,
        "max_builder_loops": 3,
        "max_architect_loops": 2,
        "messages": [],
        "design_plan": plan,
        "qa_result": None,
        "human_decision": None,
        "awaiting_human": False,
        "files_written": ["src/LoginForm.tsx"],
        "branch_name": "feat/login-form-a1b2c3d4",
        "pr_url": None,
        "error": None,
        "status": "running",
    }
    state.update(overrides)
    return state


def _passing_qa() -> QAResult:
    return QAResult(
        passed=True,
        score=1.0,
        failures=[],
        feedback="All checks passed.",
        failure_category="none",
    )


def _failing_qa(category: str) -> QAResult:
    return QAResult(
        passed=False,
        score=0.2,
        failures=["E501 line too long"],
        feedback="Fix linting errors.",
        failure_category=category,
    )


@pytest.mark.asyncio
async def test_qa_returns_passing_result(mocker):
    # Phase 1: tool loop — returns immediately (no tool calls)
    tool_response = AIMessage(content="lint output: all clean")
    # Phase 2: evaluator returns passing QAResult
    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value.ainvoke = mocker.AsyncMock(return_value=tool_response)
    mock_llm.with_structured_output.return_value.ainvoke = mocker.AsyncMock(
        return_value=_passing_qa()
    )

    result = await qa_node(_base_state(), tools=[], llm=mock_llm)

    assert result["qa_result"].passed is True
    assert result["current_node"] == "qa"
    assert result["next_node"] == "supervisor"


@pytest.mark.asyncio
async def test_qa_returns_implementation_error(mocker):
    tool_response = AIMessage(content="ruff: E501 line too long")
    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value.ainvoke = mocker.AsyncMock(return_value=tool_response)
    mock_llm.with_structured_output.return_value.ainvoke = mocker.AsyncMock(
        return_value=_failing_qa("implementation_error")
    )

    result = await qa_node(_base_state(), tools=[], llm=mock_llm)

    assert result["qa_result"].passed is False
    assert result["qa_result"].failure_category == "implementation_error"


@pytest.mark.asyncio
async def test_qa_triggers_embedding_stub_on_pass(mocker):
    tool_response = AIMessage(content="all clean")
    stub_spy = mocker.patch("pod_brain.agents.qa._trigger_embedding_stub", return_value=None)
    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value.ainvoke = mocker.AsyncMock(return_value=tool_response)
    mock_llm.with_structured_output.return_value.ainvoke = mocker.AsyncMock(
        return_value=_passing_qa()
    )

    await qa_node(_base_state(), tools=[], llm=mock_llm)

    stub_spy.assert_called_once()
