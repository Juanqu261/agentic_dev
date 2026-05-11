from __future__ import annotations

import os
from pathlib import Path


def _repo_root(repo_path: str) -> Path:
    if not repo_path:
        raise RuntimeError("repo_path must be provided")
    return Path(repo_path).resolve()


def _safe_path(relative: str, repo_path: str) -> Path:
    """
    Resolve `relative` against repo_path and raise ValueError if the
    result escapes the sandbox. Uses os.sep suffix to prevent false positives
    where a sibling directory shares a prefix (e.g. /tmp/repo vs /tmp/repo-evil).
    """
    root = _repo_root(repo_path)
    resolved = (root / relative).resolve()
    inside = str(resolved).startswith(str(root) + os.sep) or resolved == root
    if not inside:
        raise ValueError(f"Path traversal attempt blocked: {relative!r}")
    return resolved
