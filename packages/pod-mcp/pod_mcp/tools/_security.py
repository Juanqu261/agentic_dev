from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    raw = os.environ.get("TARGET_REPO_PATH", "")
    if not raw:
        raise RuntimeError("TARGET_REPO_PATH env var is not set")
    return Path(raw).resolve()


def _safe_path(relative: str) -> Path:
    """
    Resolve `relative` against TARGET_REPO_PATH and raise ValueError if the
    result escapes the sandbox. Uses os.sep suffix to prevent false positives
    where a sibling directory shares a prefix (e.g. /tmp/repo vs /tmp/repo-evil).
    """
    root = _repo_root()
    resolved = (root / relative).resolve()
    inside = str(resolved).startswith(str(root) + os.sep) or resolved == root
    if not inside:
        raise ValueError(f"Path traversal attempt blocked: {relative!r}")
    return resolved
