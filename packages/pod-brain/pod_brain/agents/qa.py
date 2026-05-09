from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from pod_brain.config import settings
from pod_brain.graph.state import PodState, QAResult

QA_TOOL_PHASE_PROMPT = """
You are the QA agent in Agentic DevStudio.

Phase 1 — Collect evidence: Use execute_command to verify files exist and run
any available linters or test suites for this tech stack. Use read_file if a
failure needs more context. Run all checks before stopping.
If a linter or tool is not installed, note it as an environment_error in your verdict — do NOT fail the build for a missing tool.
""".strip()

QA_EVAL_PHASE_PROMPT = """
You are the QA evaluator in Agentic DevStudio.

Phase 2 — Verdict: Given the collected lint/test output below, produce a
structured QAResult JSON object.

Failure categories:
- "implementation_error": wrong logic, syntax error, missing import → Builder should fix
- "design_error": wrong file structure, incorrect API shape, violated constraint → Architect should redesign
- "environment_error": missing dependency, broken tool, infra issue → escalate to human
- "none": all checks passed
""".strip()


async def qa_node(
    state: PodState,
    *,
    tools: list[BaseTool],
    llm: ChatAnthropic | None = None,
) -> dict:
    """
    LangGraph node. Two-phase execution:
      Phase 1: ReAct tool loop to collect lint/test output.
      Phase 2: Separate structured-output call to evaluate results as QAResult.
    Bound into the graph via functools.partial.
    """
    _llm = llm or ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
    )

    plan = state.get("design_plan")
    files = state.get("files_written", [])

    # ── Phase 1: tool execution loop ─────────────────────────────────────
    tool_messages: list[HumanMessage | AIMessage | ToolMessage] = [
        SystemMessage(content=QA_TOOL_PHASE_PROMPT),
        HumanMessage(
            content=(
                f"Target repo: {state['target_repo']}\n"
                f"Branch: {state.get('branch_name', 'unknown')}\n"
                f"Files written this iteration: {files}\n"
                f"Design constraints: {plan.constraints if plan else []}\n\n"
                "Run all QA checks now."
            )
        ),
    ]

    llm_with_tools = _llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}
    collected_output: list[str] = []

    # Simple tool loop — keep calling until no tool calls remain
    for _ in range(10):  # guard against runaway loops
        response: AIMessage = await llm_with_tools.ainvoke(tool_messages)
        tool_messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = await tool_fn.ainvoke(tc["args"])
                result_str = str(result)
                collected_output.append(f"[{tc['name']}]: {result_str}")
                tool_messages.append(
                    ToolMessage(content=result_str, tool_call_id=tc["id"])
                )

    raw_output = "\n".join(collected_output) if collected_output else "No tool output collected."

    # ── Phase 2: structured evaluation ───────────────────────────────────
    eval_messages = [
        SystemMessage(content=QA_EVAL_PHASE_PROMPT),
        HumanMessage(content=f"Lint/test output:\n\n{raw_output}"),
    ]

    structured_llm = _llm.with_structured_output(QAResult)
    qa_result: QAResult = await structured_llm.ainvoke(eval_messages)

    if qa_result.passed:
        await _trigger_embedding_stub(state)

    return {
        "qa_result": qa_result,
        "current_node": "qa",
        "next_node": "supervisor",
        "messages": list(tool_messages) + eval_messages,
        "status": "running",
    }


async def _trigger_embedding_stub(state: PodState) -> None:
    """Phase 3 hook: index newly written code into pod-memory after QA passes."""
    pass
