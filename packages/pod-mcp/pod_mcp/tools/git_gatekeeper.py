from __future__ import annotations

import re

import git

from pod_mcp.mcp_instance import mcp
from pod_mcp.tools._security import _repo_root

_SAFE_BRANCH_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._/\-]*$')


def _validate_branch_name(name: str) -> None:
    if not _SAFE_BRANCH_RE.match(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    if ".." in name:
        raise ValueError(f"Branch name contains '..': {name!r}")


@mcp.tool()
def create_branch(branch_name: str) -> str:
    """Create and checkout a new branch in TARGET_REPO_PATH. Uses GitPython — no shell execution."""
    _validate_branch_name(branch_name)
    repo = git.Repo(str(_repo_root()))

    existing = [b.name for b in repo.branches]
    if branch_name in existing:
        raise ValueError(f"Branch already exists: {branch_name!r}")

    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    return f"Created and checked out branch: {branch_name}"
