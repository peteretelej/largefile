"""Integration tests for list_directory tool workflows.

Uses the real test_data directory structure. No mocks.
"""

from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.tools import list_directory


class TestDirectoryWorkflows:
    """Real-world directory scanning scenarios using the project's own test data."""

    @property
    def test_data_dir(self) -> Path:
        return Path(__file__).parent.parent / "test_data"

    @property
    def src_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "src"

    # ------------------------------------------------------------------
    # Basic listing of real directories
    # ------------------------------------------------------------------

    def test_list_test_data_root(self) -> None:
        """test_data/ has several known language subdirectories."""
        result = list_directory(str(self.test_data_dir))

        assert result["total_dirs"] >= 5  # python, java, go, rust, js, ...
        names = [e["name"] for e in result["entries"]]
        for lang in ("python", "java", "go"):
            assert lang in names, f"Expected '{lang}' subdir in test_data"

    def test_list_python_test_data(self) -> None:
        """python/ contains exactly one .py fixture file."""
        python_dir = self.test_data_dir / "python"
        result = list_directory(str(python_dir))

        assert result["total_files"] >= 1
        py_files = [e for e in result["entries"] if e["name"].endswith(".py")]
        assert len(py_files) >= 1
        # Sizes should be positive — real source file
        for e in py_files:
            assert e["size_bytes"] > 0

    def test_list_java_test_data(self) -> None:
        """java/ directory contains the spring-application.java file."""
        java_dir = self.test_data_dir / "java"
        result = list_directory(str(java_dir))

        names = [e["name"] for e in result["entries"]]
        assert "spring-application.java" in names
        java_entry = next(
            e for e in result["entries"] if e["name"] == "spring-application.java"
        )
        assert java_entry["type"] == "file"
        assert java_entry["size_bytes"] > 0

    # ------------------------------------------------------------------
    # Recursive scan
    # ------------------------------------------------------------------

    def test_recursive_scan_finds_nested_files(self) -> None:
        """Depth-2 scan of test_data/ picks up files inside language subdirs."""
        result = list_directory(str(self.test_data_dir), max_depth=2)

        # At depth 2 we expect to see actual source files (not just dirs)
        assert result["total_files"] > 0
        file_names = [e["name"] for e in result["entries"] if e["type"] == "file"]
        assert len(file_names) > 0

    # ------------------------------------------------------------------
    # src/ directory scan
    # ------------------------------------------------------------------

    def test_list_src_directory(self) -> None:
        """Scanning src/ returns all .py module files."""
        result = list_directory(str(self.src_dir))

        names = [e["name"] for e in result["entries"]]
        for module in ("tools.py", "config.py", "data_models.py"):
            assert module in names, f"Expected '{module}' in src/"
        assert result["total_files"] >= 10

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_nonexistent_path_raises(self) -> None:
        """Passing a non-existent path raises ToolError."""
        with pytest.raises(ToolError):
            list_directory(str(self.test_data_dir / "does_not_exist"))
