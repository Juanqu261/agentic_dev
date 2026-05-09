from __future__ import annotations

from typing import Literal

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

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

AXIOM_EXTRACT_PROMPT = """
You are an axiom extractor for a software development environment.

Given the raw output of a QA run, extract ONLY facts that would be useful to
remember in future runs to avoid wasted retries. Focus on:
- Tools that are available or NOT available in this environment (with versions if shown)
- Commands that worked successfully for this tech stack
- Environment facts (runtimes, paths, OS behaviour)
- Patterns that failed and should be avoided next time

Return an empty list if nothing useful was discovered.

DO NOT include:
- File contents or code snippets
- Design decisions or implementation details
- Vague observations like "the build succeeded"
- Duplicate facts already obvious from the task description
""".strip()


class _Axiom(BaseModel):
    id: str
    content: str
    type: Literal["environment", "tool", "command", "pattern"]


class _ExtractedAxioms(BaseModel):
    axioms: list[_Axiom]


async def qa_node(
    state: PodState,
    *,
    tools: list[BaseTool],
    llm: ChatGoogleGenerativeAI | None = None,
) -> dict:
    """
    LangGraph node. Two-phase execution:
      Phase 1: ReAct tool loop to collect lint/test output.
      Phase 2: Separate structured-output call to evaluate results as QAResult.
      Phase 3: Axiom extraction — curate environment facts and index to pod-memory.
    Bound into the graph via functools.partial.
    """
    _llm = llm or ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
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

    for _ in range(10):
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

    # ── Phase 3: axiom extraction (always runs, pass or fail) ────────────
    await _extract_and_index_axioms(
        llm=_llm,
        raw_output=raw_output,
        repo_id=state["target_repo"],
        chroma_url=settings.chroma_url,
    )

    return {
        "qa_result": qa_result,
        "current_node": "qa",
        "next_node": "supervisor",
        "messages": list(tool_messages) + eval_messages,
        "status": "running",
    }


async def _extract_and_index_axioms(
    llm: ChatGoogleGenerativeAI,
    raw_output: str,
    repo_id: str,
    chroma_url: str,
) -> None:
    """Ask the LLM to curate useful facts from QA output, then upsert to pod-memory."""
    if not raw_output or raw_output == "No tool output collected.":
        return

    try:
        extractor = llm.with_structured_output(_ExtractedAxioms)
        result: _ExtractedAxioms = await extractor.ainvoke([
            SystemMessage(content=AXIOM_EXTRACT_PROMPT),
            HumanMessage(content=f"QA output:\n\n{raw_output}"),
        ])

        if not result.axioms:
            return

        payload = {
            "repo_id": repo_id,
            "axioms": [a.model_dump() for a in result.axioms],
        }
        async with httpx.AsyncClient() as client:
            await client.post(f"{chroma_url}/axioms", json=payload, timeout=10.0)

    except Exception:
        # Axiom indexing is best-effort — never block the QA result
        pass
