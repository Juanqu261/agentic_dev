from __future__ import annotations

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from pod_brain.config import settings
from pod_brain.graph.state import DesignPlan, PodState

ARCHITECT_SYSTEM_PROMPT = """
You are the Architect agent in Agentic DevStudio.

Your job:
1. Analyze the user's task.
2. Use the provided repository context to understand existing patterns and conventions.
3. Produce a precise design plan specifying:
   - Which files to create and which to modify (relative paths from repo root)
   - A git branch name in kebab-case prefixed with "feat/" and suffixed with a short UUID
   - Architectural constraints the Builder must respect (imports, naming, patterns)
   - A concise human-readable summary

Rules:
- Never generate actual code — that is the Builder's job.
- If the task is ambiguous, make the safest conservative assumption and note it in constraints.
- Respond ONLY with a valid JSON object matching the DesignPlan schema.
""".strip()


async def _query_pod_memory(
    task: str,
    target_repo: str,
    chroma_url: str,
    n_results: int = 5,
) -> list[str]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{chroma_url}/query",
                json={"repo_id": target_repo, "query": task, "n_results": n_results},
                timeout=10.0,
            )
            r.raise_for_status()
            return [c["content"] for c in r.json()["results"]]
    except Exception:
        return []


async def architect_node(
    state: PodState,
    *,
    tools: list[BaseTool],
    llm: ChatGoogleGenerativeAI | None = None,
    chroma_url: str | None = None,
) -> dict:
    """
    LangGraph node. Queries pod-memory for context then produces a DesignPlan.
    Bound into the graph via functools.partial to inject tools and llm.
    """
    _llm = llm or ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.gemini_api_key,
        temperature=0,
    )
    _chroma_url = chroma_url or settings.chroma_url

    tech_context = await _query_pod_memory(
        task=state["task"],
        target_repo=state["target_repo"],
        chroma_url=_chroma_url,
    )

    context_block = "\n---\n".join(tech_context) if tech_context else "No existing context found for this repo."

    conflict_warning = ""
    if state.get("conflicts"):
        names = [c["branch"] for c in state["conflicts"]]
        conflict_warning = (
            f"\n\nWARNING: Active branches touching overlapping files: {names}. "
            "Coordinate naming to avoid conflicts."
        )

    messages = [
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Task: {state['task']}\n\n"
                f"Target repo: {state['target_repo']}\n\n"
                f"Existing codebase context:\n{context_block}"
                f"{conflict_warning}"
            )
        ),
    ]

    structured_llm = _llm.with_structured_output(DesignPlan)
    design_plan: DesignPlan = await structured_llm.ainvoke(messages)

    return {
        "design_plan": design_plan,
        "current_node": "architect",
        "next_node": "supervisor",
        "architect_iterations": state["architect_iterations"] + 1,
        "messages": messages + [design_plan.model_dump()],
        "status": "running",
    }
