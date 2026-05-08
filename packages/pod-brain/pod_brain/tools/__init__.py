from __future__ import annotations

from typing import NamedTuple

from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from pod_brain.config import settings


class AgentToolsets(NamedTuple):
    architect: list[BaseTool]
    builder: list[BaseTool]
    qa: list[BaseTool]


async def load_mcp_tools(url: str | None = None) -> AgentToolsets:
    """
    Connect to pod-mcp via SSE transport and return per-agent tool subsets.
    Tool names must match the @tool decorator names in pod-mcp/pod_mcp/tools/.
    """
    mcp_url = url or settings.pod_mcp_url

    client = MultiServerMCPClient(
        {
            "pod-mcp": {
                "url": f"{mcp_url}/mcp",
                "transport": "sse",
            }
        }
    )
    all_tools: list[BaseTool] = await client.get_tools()
    tool_map = {t.name: t for t in all_tools}

    def pick(*names: str) -> list[BaseTool]:
        return [tool_map[n] for n in names if n in tool_map]

    return AgentToolsets(
        architect=pick("read_file", "list_directory", "get_file_tree", "search_files", "find_in_files"),
        builder=pick("read_file", "write_file", "edit_file", "delete_file", "create_branch",
                     "git_add", "git_commit", "list_directory", "execute_command"),
        qa=pick("execute_command", "read_file", "find_in_files", "git_diff", "list_directory"),
    )


def make_mock_toolsets() -> AgentToolsets:
    """No-op tool stubs for unit tests where pod-mcp is not running."""

    @tool
    def noop(input: str) -> str:  # noqa: A002
        """No-op tool for testing."""
        return ""

    stub: list[BaseTool] = [noop]
    return AgentToolsets(architect=stub, builder=stub, qa=stub)
