from __future__ import annotations

import os
import re

from pod_mcp.mcp_instance import mcp
from pod_mcp.tools._security import _repo_root, _safe_path


@mcp.tool()
def read_file(path: str, repo_path: str) -> str:
    """Read the entire UTF-8 contents of a file inside the target repo. `path` is relative to repo_path."""
    return _safe_path(path, repo_path).read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str, repo_path: str) -> str:
    """Write `content` to a file inside the target repo, creating parent directories as needed. `path` is relative to repo_path."""
    safe = _safe_path(path, repo_path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return f"Written: {path}"


@mcp.tool()
def edit_file(path: str, old_string: str, new_string: str, repo_path: str) -> str:
    """Replace old_string with new_string in a file. Raises if old_string is not found or matches more than once (use a larger context to disambiguate)."""
    safe = _safe_path(path, repo_path)
    content = safe.read_text(encoding="utf-8")
    count = content.count(old_string)
    if count == 0:
        raise ValueError(f"old_string not found in {path!r}")
    if count > 1:
        raise ValueError(f"old_string matches {count} locations in {path!r} — add more surrounding context to make it unique")
    safe.write_text(content.replace(old_string, new_string, 1), encoding="utf-8")
    return f"Edited: {path}"


@mcp.tool()
def delete_file(path: str, repo_path: str) -> str:
    """Delete a file inside the target repo. `path` is relative to repo_path."""
    safe = _safe_path(path, repo_path)
    if not safe.exists():
        raise FileNotFoundError(f"File not found: {path!r}")
    if safe.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {path!r}")
    safe.unlink()
    return f"Deleted: {path}"


@mcp.tool()
def list_directory(repo_path: str, path: str = ".") -> list[str]:
    """List immediate children of a directory inside the target repo. Directories are suffixed with '/'."""
    safe = _safe_path(path, repo_path)
    if not safe.is_dir():
        raise NotADirectoryError(f"{path!r} is not a directory")
    return sorted(
        item.name + "/" if item.is_dir() else item.name
        for item in safe.iterdir()
    )


@mcp.tool()
def get_file_tree(repo_path: str, directory: str = ".", max_depth: int = 3) -> str:
    """Return a recursive directory tree as a formatted string, up to max_depth levels deep."""
    safe_dir = _safe_path(directory, repo_path)
    lines = [safe_dir.name + "/"]

    def _walk(path, prefix, depth):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(prefix + connector + (entry.name + "/" if entry.is_dir() else entry.name))
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)

    _walk(safe_dir, "", 1)
    return "\n".join(lines)


@mcp.tool()
def search_files(pattern: str, repo_path: str, directory: str = ".") -> list[str]:
    """Recursively glob for `pattern` inside `directory` within the target repo. Returns paths relative to repo_path."""
    safe_dir = _safe_path(directory, repo_path)
    root = _repo_root(repo_path)
    results = []
    for match in safe_dir.glob(pattern):
        resolved = match.resolve()
        if str(resolved).startswith(str(root) + os.sep) or resolved == root:
            results.append(str(resolved.relative_to(root)))
    return sorted(results)


@mcp.tool()
def find_in_files(pattern: str, repo_path: str, directory: str = ".") -> list[str]:
    """Search file contents for a regex pattern. Returns 'file:line:matched_line' strings. Skips binary files."""
    safe_dir = _safe_path(directory, repo_path)
    root = _repo_root(repo_path)
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc

    results = []
    for file_path in sorted(safe_dir.rglob("*")):
        if not file_path.is_file():
            continue
        resolved = file_path.resolve()
        if not (str(resolved).startswith(str(root) + os.sep) or resolved == root):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="strict")
        except (PermissionError, UnicodeDecodeError):
            continue  # skip binary or unreadable files
        for lineno, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                rel = str(resolved.relative_to(root))
                results.append(f"{rel}:{lineno}:{line.strip()}")
    return results
