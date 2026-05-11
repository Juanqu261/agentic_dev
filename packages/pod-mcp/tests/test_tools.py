"""
Integration tests for pod-mcp tools.

Each test group spins up a real temp directory as the repo root and
exercises the tools against actual filesystem/git state — no mocks.
"""
from __future__ import annotations

import asyncio
import shutil
import stat
import sys

import git
import pytest


def _force_remove(path) -> None:
    """Remove a directory tree, clearing read-only flags first (required for .git on Windows)."""
    def _on_error(func, fpath, _exc):
        # Clear the read-only bit and retry
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)

    import os
    shutil.rmtree(path, onerror=_on_error)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _init_git_repo(path) -> git.Repo:
    """Create a real git repo with an initial commit so HEAD exists."""
    repo = git.Repo.init(str(path))
    repo.config_writer().set_value("user", "name", "Test Bot").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (path / "README.md").write_text("init")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo


# ── Security (_safe_path) ─────────────────────────────────────────────────────


class TestSafePath:
    def test_allows_valid_relative_path(self, tmp_path):
        from pod_mcp.tools._security import _safe_path

        result = _safe_path("src/main.py", str(tmp_path))
        assert result == (tmp_path / "src" / "main.py").resolve()

    def test_allows_repo_root_itself(self, tmp_path):
        from pod_mcp.tools._security import _safe_path

        assert _safe_path(".", str(tmp_path)) == tmp_path.resolve()

    def test_blocks_path_traversal(self, tmp_path):
        from pod_mcp.tools._security import _safe_path

        with pytest.raises(ValueError, match="Path traversal"):
            _safe_path("../../etc/passwd", str(tmp_path))

    def test_blocks_sibling_directory(self, tmp_path):
        """Prevents false-negative where sibling dir shares a prefix with the root."""
        sibling = tmp_path.parent / (tmp_path.name + "-evil")
        sibling.mkdir()
        from pod_mcp.tools._security import _safe_path

        with pytest.raises(ValueError, match="Path traversal"):
            _safe_path(f"../{tmp_path.name}-evil/secret.txt", str(tmp_path))

    def test_raises_when_repo_path_empty(self):
        from pod_mcp.tools._security import _repo_root

        with pytest.raises(RuntimeError, match="repo_path must be provided"):
            _repo_root("")


# ── Filesystem tools ──────────────────────────────────────────────────────────


class TestFilesystemTools:
    @pytest.fixture(autouse=True)
    def set_repo(self, tmp_path):
        self.root = tmp_path
        self.rp = str(tmp_path)

    def test_write_and_read_file(self):
        from pod_mcp.tools.filesystem import read_file, write_file

        result = write_file("src/hello.py", "print('hello')", self.rp)
        assert result == "Written: src/hello.py"
        assert read_file("src/hello.py", self.rp) == "print('hello')"

    def test_write_creates_parent_dirs(self):
        from pod_mcp.tools.filesystem import write_file

        write_file("deep/nested/dir/file.txt", "content", self.rp)
        assert (self.root / "deep" / "nested" / "dir" / "file.txt").exists()

    def test_read_missing_file_raises(self):
        from pod_mcp.tools.filesystem import read_file

        with pytest.raises(FileNotFoundError):
            read_file("nonexistent.txt", self.rp)

    def test_list_directory(self):
        from pod_mcp.tools.filesystem import list_directory, write_file

        write_file("a.txt", "", self.rp)
        write_file("b.txt", "", self.rp)
        (self.root / "subdir").mkdir()

        entries = list_directory(self.rp, ".")
        assert "a.txt" in entries
        assert "b.txt" in entries
        assert "subdir/" in entries  # dirs get trailing slash

    def test_list_directory_not_a_dir_raises(self):
        from pod_mcp.tools.filesystem import list_directory, write_file

        write_file("file.txt", "", self.rp)
        with pytest.raises(NotADirectoryError):
            list_directory(self.rp, "file.txt")

    def test_search_files(self):
        from pod_mcp.tools.filesystem import search_files, write_file

        write_file("src/main.py", "", self.rp)
        write_file("src/utils.py", "", self.rp)
        write_file("tests/test_main.py", "", self.rp)

        results = search_files("**/*.py", self.rp)
        assert any("main.py" in r for r in results)
        assert any("utils.py" in r for r in results)
        assert any("test_main.py" in r for r in results)

    def test_write_blocks_traversal(self):
        from pod_mcp.tools.filesystem import write_file

        with pytest.raises(ValueError, match="Path traversal"):
            write_file("../../evil.sh", "rm -rf /", self.rp)


# ── Shell tool ────────────────────────────────────────────────────────────────


class TestExecuteCommand:
    @pytest.fixture(autouse=True)
    def set_repo(self, tmp_path):
        self.root = tmp_path
        self.rp = str(tmp_path)

    def test_happy_path(self):
        from pod_mcp.tools.shell import execute_command

        # Use python to stay cross-platform (Windows + Linux/Mac)
        output = asyncio.run(execute_command('python -c "print(\'hello\')"', self.rp))
        assert "hello" in output

    def test_cwd_is_target_repo(self):
        from pod_mcp.tools.shell import execute_command

        if sys.platform == "win32":
            output = asyncio.run(execute_command("cd", self.rp))
        else:
            output = asyncio.run(execute_command("pwd", self.rp))

        assert str(self.root).lower() in output.lower()

    def test_nonzero_exit_returns_exit_code(self):
        from pod_mcp.tools.shell import execute_command

        output = asyncio.run(execute_command('python -c "import sys; sys.exit(1)"', self.rp))
        assert "[exit code 1]" in output

    def test_timeout_raises(self):
        from pod_mcp.tools.shell import execute_command

        with pytest.raises(RuntimeError, match="timed out"):
            asyncio.run(execute_command('python -c "import time; time.sleep(999)"', self.rp, timeout=1))

    def test_timeout_is_capped(self):
        """Timeout values outside [1, 300] are clamped, not rejected."""
        from pod_mcp.tools.shell import execute_command

        # timeout=0 → clamped to 1; command finishes well within 1s
        output = asyncio.run(execute_command('python -c "print(1)"', self.rp, timeout=0))
        assert "1" in output


# ── Git gatekeeper ────────────────────────────────────────────────────────────


class TestCreateBranch:
    @pytest.fixture(autouse=True)
    def set_repo(self, tmp_path, request):
        self.rp = str(tmp_path)
        self.repo = _init_git_repo(tmp_path)
        # Explicit finalizer: tmp_path cleanup fails on Windows when .git has read-only files
        def _cleanup():
            self.repo.close()   # release .git file handles before rmtree
            _force_remove(tmp_path)

        request.addfinalizer(_cleanup)

    def test_creates_and_checks_out_branch(self):
        from pod_mcp.tools.git_gatekeeper import create_branch

        result = create_branch("feat/login-form", self.rp)
        assert "feat/login-form" in result
        assert self.repo.active_branch.name == "feat/login-form"

    def test_existing_branch_checks_out(self):
        from pod_mcp.tools.git_gatekeeper import create_branch

        create_branch("feat/duplicate", self.rp)
        result = create_branch("feat/duplicate", self.rp)
        assert "already exists" in result

    def test_invalid_name_raises(self):
        from pod_mcp.tools.git_gatekeeper import create_branch

        with pytest.raises(ValueError, match="Invalid branch name"):
            create_branch("feat branch with spaces", self.rp)

    def test_dotdot_in_name_raises(self):
        from pod_mcp.tools.git_gatekeeper import create_branch

        with pytest.raises(ValueError, match="contains '..'"):
            create_branch("feat/../evil", self.rp)

    def test_leading_hyphen_raises(self):
        from pod_mcp.tools.git_gatekeeper import create_branch

        with pytest.raises(ValueError, match="Invalid branch name"):
            create_branch("-bad-flag", self.rp)
