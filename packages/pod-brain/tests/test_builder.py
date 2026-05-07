import pytest
from langchain_core.messages import AIMessage

from pod_brain.agents.builder import _extract_files_written, builder_node
from pod_brain.graph.state import DesignPlan, PodState, QAResult


def _base_state(**overrides) -> PodState:
    plan = DesignPlan(
        summary="Add a login form",
        files_to_create=["src/LoginForm.tsx"],
        files_to_modify=["src/App.tsx"],
        branch_name="feat/login-form-a1b2c3d4",
    )
    state: PodState = {
        "task": "Build a login form",
        "target_repo": "/tmp/fake-repo",
        "thread_id": "user1-req1",
        "current_node": "supervisor",
        "next_node": "builder",
        "builder_iterations": 0,
        "architect_iterations": 1,
        "max_builder_loops": 3,
        "max_architect_loops": 2,
        "messages": [],
        "design_plan": plan,
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


@pytest.mark.asyncio
async def test_builder_increments_iterations(mocker):
    response = AIMessage(content='{"files_written": ["src/LoginForm.tsx"], "branch_name": "feat/x"}')
    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value.ainvoke = mocker.AsyncMock(return_value=response)

    result = await builder_node(_base_state(), tools=[], llm=mock_llm)

    assert result["builder_iterations"] == 1
    assert result["current_node"] == "builder"


@pytest.mark.asyncio
async def test_builder_includes_qa_feedback_in_prompt(mocker):
    captured_messages = []

    async def capture_invoke(messages):
        captured_messages.extend(messages)
        return AIMessage(content="done")

    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value.ainvoke = capture_invoke

    qa = QAResult(
        passed=False,
        score=0.2,
        failures=["missing import"],
        feedback="Add the missing import for React",
        failure_category="implementation_error",
    )
    result = await builder_node(_base_state(qa_result=qa), tools=[], llm=mock_llm)

    prompt_text = " ".join(str(m.content) for m in captured_messages)
    assert "missing import" in prompt_text
    assert result["builder_iterations"] == 1


def test_extract_files_written_from_json_response():
    plan = DesignPlan(
        summary="x",
        files_to_create=["a.py"],
        files_to_modify=[],
        branch_name="feat/x",
    )
    msg = AIMessage(content='{"files_written": ["src/login.tsx"], "branch_name": "feat/x"}')
    result = _extract_files_written(msg, plan)
    assert result == ["src/login.tsx"]


def test_extract_files_written_falls_back_to_plan():
    plan = DesignPlan(
        summary="x",
        files_to_create=["a.py"],
        files_to_modify=["b.py"],
        branch_name="feat/x",
    )
    msg = AIMessage(content="I wrote the files.")
    result = _extract_files_written(msg, plan)
    assert set(result) == {"a.py", "b.py"}
