from __future__ import annotations

import os

from fastapi import FastAPI

from pod_mcp.mcp_instance import mcp

# Import tool modules to trigger @mcp.tool() registration before the ASGI app is built.
# Order matters: mcp_instance must be imported first (done above), then tool modules.
from pod_mcp.tools import filesystem, shell, git_gatekeeper  # noqa: F401, E402

# Mount the MCP SSE transport at /mcp.
# langchain_mcp_adapters connects to {POD_MCP_URL}/mcp and appends /sse + /messages,
# so the full paths served here are /mcp/sse and /mcp/messages.
# mcp.sse_app() is the SSE transport; mcp.streamable_http_app() is an alternative for HTTP streaming.
api = FastAPI(title="pod-mcp")
api.mount("/mcp", mcp.sse_app())

app = api


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("POD_MCP_PORT", "8001")))
