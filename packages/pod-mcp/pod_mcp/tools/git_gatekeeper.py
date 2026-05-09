from __future__ import annotations

import os
import re

import git
import httpx

from pod_mcp.mcp_instance import mcp
from pod_mcp.tools._security import _repo_root, _safe_path

_SAFE_BRANCH_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._/\-]*$')


def _validate_branch_name(name: str) -> None:
    if not _SAFE_BRANCH_RE.match(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    if ".." in name:
        raise ValueError(f"Branch name contains '..': {name!r}")


def _get_repo() -> git.Repo:
    return git.Repo(str(_repo_root()))


def _parse_github_owner_repo(remote_url: str) -> str:
    """Extract 'owner/repo' from SSH or HTTPS GitHub remote URLs."""
    match = re.search(r'[:/]([^/]+/[^/]+?)(?:\.git)?$', remote_url)
    if not match:
        raise ValueError(f"Cannot parse GitHub owner/repo from remote URL: {remote_url!r}")
    return match.group(1)


@mcp.tool()
def create_branch(branch_name: str) -> str:
    """Create and checkout a new branch in TARGET_REPO_PATH. Uses GitPython — no shell execution."""
    _validate_branch_name(branch_name)
    repo = _get_repo()

    # Empty repo (no commits yet) — HEAD can't resolve, so create an initial commit first.
    if not repo.head.is_valid():
        repo.index.commit("chore: initial commit")

    existing = {b.name: b for b in repo.branches}
    if branch_name in existing:
        existing[branch_name].checkout()
        return f"Branch already exists, checked out: {branch_name}"

    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    return f"Created and checked out branch: {branch_name}"


@mcp.tool()
def git_add(paths: list[str]) -> str:
    """Stage files for the next commit. Paths are relative to TARGET_REPO_PATH."""
    repo = _get_repo()
    for path in paths:
        _safe_path(path)  # validate each path stays inside the repo
    repo.index.add(paths)
    return f"Staged: {', '.join(paths)}"


@mcp.tool()
def git_commit(message: str) -> str:
    """Commit staged changes. Raises if nothing is staged."""
    if not message.strip():
        raise ValueError("Commit message cannot be empty")
    repo = _get_repo()
    if not repo.is_dirty(index=True):
        raise RuntimeError("Nothing staged to commit — run git_add first")
    commit = repo.index.commit(message)
    return f"Committed {commit.hexsha[:8]}: {message}"


@mcp.tool()
def git_diff(staged: bool = False) -> str:
    """Show git diff. staged=True shows staged changes (vs HEAD), False shows unstaged working-tree changes."""
    repo = _get_repo()
    return repo.git.diff("--staged") if staged else repo.git.diff()


@mcp.tool()
def open_pr(title: str, body: str, base: str = "main") -> str:
    """Push the current branch and open a GitHub Pull Request. Requires GITHUB_TOKEN env var."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN env var is not set")

    repo = _get_repo()
    head_branch = repo.active_branch.name
    remote_url = repo.remotes.origin.url
    owner_repo = _parse_github_owner_repo(remote_url)

    # Push using an authenticated URL so the token is used in headless environments
    # where no git credential helper is configured.
    auth_url = f"https://{token}@github.com/{owner_repo}.git"
    repo.git.push(auth_url, f"{head_branch}:{head_branch}", "--set-upstream")

    response = httpx.post(
        f"https://api.github.com/repos/{owner_repo}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"title": title, "body": body, "head": head_branch, "base": base},
        timeout=30,
    )
    response.raise_for_status()
    pr_url = response.json()["html_url"]
    return f"PR opened: {pr_url}"
