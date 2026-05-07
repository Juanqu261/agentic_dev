import pytest

from pod_brain.agents.architect import _query_pod_memory, architect_node
from pod_brain.graph.state import DesignPlan, PodState


def _base_state(**overrides) -> PodState:
    state: PodState = {
        "task": "Build a login form",
        "target_repo": "/tmp/fake-repo",
        "thread_id": "user1-req1",
        "current_node": "start",
        "next_node": "architect",
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


def _fake_plan() -> DesignPlan:
    return DesignPlan(
        summary="Add a login form component",
        files_to_create=["src/LoginForm.tsx"],
        files_to_modify=["src/App.tsx"],
        branch_name="feat/login-form-a1b2c3d4",
    )


@pytest.mark.asyncio
async def test_architect_returns_design_plan(mocker):
    mocker.patch(
        "pod_brain.agents.architect._query_pod_memory",
        return_value=["existing AuthService.ts snippet"],
    )
    # with_structured_output() is a sync method on the LLM — use MagicMock, not AsyncMock.
    # Only .ainvoke() on its return value needs to be async.
    mock_llm = mocker.MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = mocker.AsyncMock(
        return_value=_fake_plan()
    )

    result = await architect_node(
        _base_state(),
        tools=[],
        llm=mock_llm,
        chroma_url="http://fake",
    )

    assert result["design_plan"] == _fake_plan()
    assert result["current_node"] == "architect"
    assert result["architect_iterations"] == 1
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_architect_gracefully_handles_empty_memory(mocker):
    mocker.patch(
        "pod_brain.agents.architect._query_pod_memory",
        return_value=[],
    )
    mock_llm = mocker.MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = mocker.AsyncMock(
        return_value=_fake_plan()
    )

    result = await architect_node(
        _base_state(),
        tools=[],
        llm=mock_llm,
        chroma_url="http://fake",
    )

    assert result["design_plan"] is not None


@pytest.mark.asyncio
async def test_query_pod_memory_returns_empty_on_error(mocker):
    mocker.patch("chromadb.AsyncHttpClient", side_effect=Exception("connection refused"))
    result = await _query_pod_memory("any task", "/any/repo", "http://fake")
    assert result == []
