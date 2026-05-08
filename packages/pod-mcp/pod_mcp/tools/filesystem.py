from __future__ import annotations

import os

from pod_mcp.mcp_instance import mcp
from pod_mcp.tools._security import _repo_root, _safe_path


@mcp.tool()
def read_file(path: str) -> str:
    """Read the entire UTF-8 contents of a file inside the target repo. `path` is relative to TARGET_REPO_PATH."""
    return _safe_path(path).read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write `content` to a file inside the target repo, creating parent directories as needed. `path` is relative to TARGET_REPO_PATH."""
    safe = _safe_path(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return f"Written: {path}"


@mcp.tool()
def list_directory(path: str = ".") -> list[str]:
    """List immediate children of a directory inside the target repo. Directories are suffixed with '/'."""
    safe = _safe_path(path)
    if not safe.is_dir():
        raise NotADirectoryError(f"{path!r} is not a directory")
    return sorted(
        item.name + "/" if item.is_dir() else item.name
        for item in safe.iterdir()
    )


@mcp.tool()
def search_files(pattern: str, directory: str = ".") -> list[str]:
    """Recursively glob for `pattern` inside `directory` within the target repo. Returns paths relative to TARGET_REPO_PATH."""
    safe_dir = _safe_path(directory)
    root = _repo_root()
    results = []
    for match in safe_dir.glob(pattern):
        resolved = match.resolve()
        if str(resolved).startswith(str(root) + os.sep) or resolved == root:
            results.append(str(resolved.relative_to(root)))
    return sorted(results)
