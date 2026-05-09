from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pod_brain.graph.state import PodState

_IS_WINDOWS = sys.platform == "win32"


def _run_git(args: list[str], cwd: str) -> str:
    cmd = ["git"] + args
    with tempfile.TemporaryFile() as out_file:
        with subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=out_file,
            stderr=subprocess.STDOUT,
        ) as proc:
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return ""
        out_file.seek(0)
        output = out_file.read().decode("utf-8", errors="replace")
    return output if proc.returncode == 0 else ""


async def conflict_checker_node(state: PodState) -> dict:
    """
    Detects overlapping active branches in the target repo after the Architect
    produces a DesignPlan. Non-blocking: failures return empty conflicts.
    """
    design_plan = state.get("design_plan")
    if design_plan is None:
        return {"conflicts": [], "current_node": "conflict_check", "next_node": "supervisor"}

    target_files = set(design_plan.files_to_create) | set(design_plan.files_to_modify)
    if not target_files:
        return {"conflicts": [], "current_node": "conflict_check", "next_node": "supervisor"}

    repo_path = os.environ.get("TARGET_REPO_PATH", "")
    if not repo_path or not Path(repo_path).is_dir():
        return {"conflicts": [], "current_node": "conflict_check", "next_node": "supervisor"}

    def _detect() -> list[dict]:
        all_branches_raw = _run_git(["branch", "-a", "--format=%(refname:short)"], repo_path)
        if not all_branches_raw:
            return []

        merged_raw = _run_git(["branch", "--merged", "main", "--format=%(refname:short)"], repo_path)
        merged = set(merged_raw.splitlines())

        conflicts: list[dict] = []
        for branch in all_branches_raw.splitlines():
            branch = branch.strip().removeprefix("origin/")
            if not branch or branch in ("main", "master", "HEAD") or branch in merged:
                continue
            # Skip the current task's own branch
            current_branch = design_plan.branch_name if design_plan else ""
            if current_branch and branch == current_branch:
                continue

            diff_raw = _run_git(["diff", "--name-only", f"main...{branch}"], repo_path)
            if not diff_raw:
                continue

            branch_files = set(diff_raw.splitlines())
            overlap = list(target_files & branch_files)
            if overlap:
                conflicts.append({"branch": branch, "files": overlap})

        return conflicts

    try:
        conflicts = await asyncio.get_event_loop().run_in_executor(None, _detect)
    except Exception:
        conflicts = []

    return {"conflicts": conflicts, "current_node": "conflict_check", "next_node": "supervisor"}
