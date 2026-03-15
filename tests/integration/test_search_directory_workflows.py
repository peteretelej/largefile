"""Integration tests for search_directory tool workflows.

Uses the real src/ and test_data/ directory structures. No mocks.
"""

from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.tools import search_directory


class TestSearchDirectoryWorkflows:
    """Real-world directory search scenarios using the project's own source tree."""

    @property
    def test_data_dir(self) -> Path:
        return Path(__file__).parent.parent / "test_data"

    @property
    def src_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "src"

    # ------------------------------------------------------------------
    # Basic search on real source tree
    # ------------------------------------------------------------------

    def test_search_python_files_in_src(self) -> None:
        """Finds 'def ' across all .py files in src/."""
        result = search_directory(str(self.src_dir), "def ", include_pattern="*.py")
        assert result["total_matches"] > 0
        assert result["files_with_matches"] > 1
        files = [g["file"] for g in result["results"]]
        assert any("tools.py" in f for f in files)

    def test_search_finds_handle_tool_errors_in_tools(self) -> None:
        """handle_tool_errors is used in tools.py."""
        result = search_directory(
            str(self.src_dir), "handle_tool_errors", include_pattern="*.py", fuzzy=False
        )
        files = [g["file"] for g in result["results"]]
        assert any("tools.py" in f for f in files)

    def test_include_pattern_restricts_to_extension(self) -> None:
        """*.py only searches Python files — no matches in non-py files."""
        result = search_directory(
            str(self.src_dir), "def ", include_pattern="*.py", fuzzy=False
        )
        files = [g["file"] for g in result["results"]]
        assert all(f.endswith(".py") for f in files)

    def test_nonexistent_pattern_returns_empty(self) -> None:
        result = search_directory(
            str(self.src_dir), "XYZZY_DOES_NOT_EXIST_42", include_pattern="*.py"
        )
        assert result["total_matches"] == 0
        assert result["files_with_matches"] == 0
        assert result["results"] == []
        assert result["truncated"] is False

    # ------------------------------------------------------------------
    # Truncation
    # ------------------------------------------------------------------

    def test_truncation_with_low_max_results(self) -> None:
        result = search_directory(str(self.src_dir), "def", max_results=3, fuzzy=False)
        assert result["total_matches"] == 3
        assert result["truncated"] is True
        assert result["truncated_at"] is not None

    # ------------------------------------------------------------------
    # Ignored dirs
    # ------------------------------------------------------------------

    def test_ignored_dirs_not_searched(self) -> None:
        """__pycache__ dirs are not traversed."""
        result = search_directory(str(self.src_dir), "cpython", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert not any("__pycache__" in f for f in files)

    # ------------------------------------------------------------------
    # Case sensitivity
    # ------------------------------------------------------------------

    def test_case_insensitive_by_default(self) -> None:
        """Default case_sensitive=False: both cases find same matches."""
        result_lower = search_directory(
            str(self.src_dir), "def ", include_pattern="*.py", fuzzy=False
        )
        result_upper = search_directory(
            str(self.src_dir), "DEF ", include_pattern="*.py", fuzzy=False
        )
        assert result_lower["total_matches"] == result_upper["total_matches"]

    def test_case_insensitive_search(self) -> None:
        """Explicit case_sensitive=False finds both upper and lower case."""
        result_lower = search_directory(
            str(self.src_dir),
            "def ",
            include_pattern="*.py",
            fuzzy=False,
            case_sensitive=False,
        )
        result_upper = search_directory(
            str(self.src_dir),
            "DEF ",
            include_pattern="*.py",
            fuzzy=False,
            case_sensitive=False,
        )
        assert result_lower["total_matches"] == result_upper["total_matches"]

    # ------------------------------------------------------------------
    # test_data multi-language search
    # ------------------------------------------------------------------

    def test_search_java_test_data(self) -> None:
        """Finds 'interface' in the java test data fixture."""
        java_dir = self.test_data_dir / "java"
        result = search_directory(
            str(java_dir), "interface", include_pattern="*.java", fuzzy=False
        )
        assert result["total_matches"] > 0
        assert result["files_with_matches"] >= 1

    def test_search_python_test_data(self) -> None:
        """Finds 'def' in the python test data fixture."""
        python_dir = self.test_data_dir / "python"
        result = search_directory(
            str(python_dir), "def", include_pattern="*.py", fuzzy=False
        )
        assert result["total_matches"] > 0

    def test_result_paths_relative_to_search_root(self) -> None:
        """File paths in results are relative to the search root, not absolute."""
        result = search_directory(
            str(self.src_dir), "import", include_pattern="*.py", fuzzy=False
        )
        for group in result["results"]:
            assert not Path(group["file"]).is_absolute()

    def test_result_paths_use_forward_slashes(self) -> None:
        """Paths use '/' separator even on Windows."""
        result = search_directory(
            str(self.src_dir), "def", include_pattern="*.py", fuzzy=False
        )
        for group in result["results"]:
            assert "\\" not in group["file"]

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_nonexistent_directory_returns_error(self) -> None:
        with pytest.raises(ToolError):
            search_directory(str(self.test_data_dir / "does_not_exist"), "x")

    def test_file_path_returns_error(self) -> None:
        with pytest.raises(ToolError, match="Not a directory"):
            search_directory(str(self.src_dir / "tools.py"), "def")
