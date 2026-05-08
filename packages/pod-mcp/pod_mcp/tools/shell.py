from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile

from pod_mcp.mcp_instance import mcp
from pod_mcp.tools._security import _repo_root

_MAX_TIMEOUT = 300
_MIN_TIMEOUT = 1


@mcp.tool()
async def execute_command(command: str, timeout: int = 30) -> str:
    """Execute `command` inside TARGET_REPO_PATH. stdout and stderr are merged. Raises RuntimeError on non-zero exit or timeout."""
    cwd = str(_repo_root())
    timeout = min(max(_MIN_TIMEOUT, timeout), _MAX_TIMEOUT)

    def _run() -> tuple[str, int]:
        # Redirect to a temp file instead of PIPE to avoid the Windows deadlock where
        # subprocess.run()/communicate() re-drains pipes after kill() without a timeout.
        with tempfile.TemporaryFile() as out_file:
            with subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=out_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            ) as proc:
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()  # safe: no pipes, just waits for OS process exit
                    raise RuntimeError(f"Command timed out after {timeout}s: {command!r}")

            out_file.seek(0)
            return out_file.read().decode("utf-8", errors="replace"), proc.returncode

    output, returncode = await asyncio.get_event_loop().run_in_executor(None, _run)

    if returncode != 0:
        raise RuntimeError(f"Command exited with code {returncode}:\n{output}")
    return output
