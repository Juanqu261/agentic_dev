from mcp.server.fastmcp import FastMCP

# Single source-of-truth for the FastMCP instance.
# Imported by tool modules (to register via @mcp.tool()) and by server.py (to build the ASGI app).
# Lives in its own module so tool modules can import it without creating a circular dependency with server.py.
mcp = FastMCP(name="pod-mcp")
