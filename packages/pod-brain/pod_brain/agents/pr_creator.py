from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

from pod_brain.graph.state import PodState

logger = logging.getLogger(__name__)


async def pr_creator_node(state: PodState, *, tools: list[BaseTool]) -> dict:
    """
    Opens a GitHub PR after human final approval. Non-fatal: logs and continues
    if open_pr fails (no GITHUB_TOKEN, no remote, etc.).
    """
    tool_map = {t.name: t for t in tools}
    open_pr = tool_map.get("open_pr")

    if open_pr is None:
        logger.warning("open_pr tool not available — skipping PR creation")
        return {"current_node": "pr_creator", "pr_url": None}

    design_plan = state.get("design_plan")
    files_written: list[str] = state.get("files_written", [])

    title = f"feat: {state['task'][:72]}"

    body_parts = []
    if design_plan:
        body_parts.append(f"## Summary\n{design_plan.summary}")
    if files_written:
        file_list = "\n".join(f"- `{f}`" for f in files_written)
        body_parts.append(f"## Files changed\n{file_list}")
    body_parts.append("_Opened automatically by Agentic DevStudio._")
    body = "\n\n".join(body_parts)

    try:
        result = await open_pr.ainvoke({"title": title, "body": body, "base": "main"})
        # open_pr returns "PR opened: <url>"
        pr_url = result.split("PR opened: ", 1)[-1].strip() if "PR opened: " in result else result.strip()
        return {"current_node": "pr_creator", "pr_url": pr_url}
    except Exception as exc:
        logger.warning("PR creation failed (non-fatal): %s", exc)
        return {"current_node": "pr_creator", "pr_url": None}
