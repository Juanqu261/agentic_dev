from __future__ import annotations

import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from pod_brain.config import settings
from pod_brain.graph.state import PodState

BUILDER_SYSTEM_PROMPT = """
You are the Builder agent in Agentic DevStudio.

You receive a DesignPlan and must implement it by calling the provided tools.

Tool use protocol:
1. Call create_branch with the branch_name from the plan.
2. For each file in files_to_create: call write_file with a complete, production-ready implementation.
3. For each file in files_to_modify: call read_file first, then write_file with the full modified content.

Rules:
- Follow every constraint in the design plan exactly.
- Write complete, production-quality code. No placeholders, no TODOs.
- If you have QA feedback, address every listed failure before writing files.
- After all writes are complete, respond with a JSON summary:
  {"files_written": [...list of relative paths...], "branch_name": "feat/..."}
""".strip()


async def builder_node(
    state: PodState,
    *,
    tools: list[BaseTool],
    llm: ChatGoogleGenerativeAI | None = None,
) -> dict:
    """
    LangGraph node. Emits an AIMessage that may contain tool calls.
    The graph's tool_executor node handles the ReAct loop:
      builder → tool_executor → builder (until no tool calls remain) → qa
    Bound into the graph via functools.partial.
    """
    _llm = llm or ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
        temperature=0,
    )

    plan = state.get("design_plan")
    qa = state.get("qa_result")

    plan_text = plan.model_dump_json(indent=2) if plan else "No design plan available."
    feedback_text = ""
    if qa and not qa.passed:
        failure_lines = "\n".join(f"- {f}" for f in qa.failures)
        feedback_text = f"\n\nPrevious QA feedback to address:\n{qa.feedback}\nFailures:\n{failure_lines}"
    instructions = state.get("human_instructions", "")
    if instructions:
        feedback_text += f"\n\nHuman instructions:\n{instructions}"

    # Include prior tool calls + results so the LLM knows what it already executed.
    # Filter to AIMessage/ToolMessage only — excludes architect planning messages.
    prior = [
        m for m in state.get("messages", [])
        if isinstance(m, (AIMessage, ToolMessage))
    ]

    messages = [
        SystemMessage(content=BUILDER_SYSTEM_PROMPT),
        HumanMessage(content=f"Design Plan:\n{plan_text}{feedback_text}"),
        *prior,
    ]

    llm_with_tools = _llm.bind_tools(tools)
    response: AIMessage = await llm_with_tools.ainvoke(messages)

    files_written = _extract_files_written(response, plan)

    return {
        "files_written": files_written,
        "branch_name": plan.branch_name if plan else None,
        "current_node": "builder",
        "next_node": "supervisor",
        "builder_iterations": state["builder_iterations"] + 1,
        "messages": [response],
        "status": "running",
    }


def _extract_files_written(response: AIMessage, plan) -> list[str]:
    """Best-effort extraction of written file paths from the LLM's final message."""
    try:
        match = re.search(r'\{"files_written"[^}]*\}', response.content or "")
        if match:
            return json.loads(match.group()).get("files_written", [])
    except Exception:
        pass
    if plan:
        return plan.files_to_create + plan.files_to_modify
    return []
