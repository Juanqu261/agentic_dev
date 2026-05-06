# Agentic DevStudio — Dockerfile
# ─────────────────────────────────────────────────────────────
# Packages the entire studio (API + MCP server) as a container.
# Point it at any external repo to start orchestrating agents.
#
# Usage:
#   docker build -t agentic-devstudio .
#   docker run -p 8000:8000 agentic-devstudio
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy workspace config and all packages
COPY pyproject.toml .
COPY packages/ packages/
COPY apps/ apps/

# Install all packages in the workspace
RUN uv sync --all-packages

# Expose the FastAPI studio-api port
EXPOSE 8000

# Run the studio API
CMD ["uv", "run", "uvicorn", "apps.studio-api.main:app", "--host", "0.0.0.0", "--port", "8000"]
