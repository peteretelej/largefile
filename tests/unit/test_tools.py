"""Tools unit tests.

Test MCP tool functions, error handling, and edge cases.
Uses table-driven tests for comprehensive coverage.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.exceptions import TreeSitterError
from src.tools import (
    edit_content,
    get_overview,
    read_content,
    search_content,
)


class TestGetOverviewBinaryFile:
    """Test get_overview with binary files."""

    def test_binary_file_detected(self):
        """Binary files are detected and return appropriate response."""
        binary_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00"  # PNG-like with nulls

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".png") as f:
            f.write(binary_content)
            temp_path = f.name

        try:
            result = get_overview(temp_path)

            assert result["is_binary"] is True
            assert result["binary_hint"] == "image"
            assert "warning" in result
            assert "Binary file" in result["warning"]
            assert result["line_count"] == 0
            assert result["outline"] == []
            assert result["search_hints"] == []
        finally:
            Path(temp_path).unlink()

    def test_binary_file_no_encoding(self):
        """Binary files have no encoding."""
        binary_content = b"Binary\x00content\x00here"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
            f.write(binary_content)
            temp_path = f.name

        try:
            result = get_overview(temp_path)

            assert result["is_binary"] is True
            assert result["encoding"] is None
        finally:
            Path(temp_path).unlink()


class TestGetOverviewSearchHints:
    """Test search hint generation for different file types."""

    @pytest.mark.parametrize(
        "extension,expected_hints",
        [
            (".py", ["def ", "class ", "import ", "from "]),
            (".js", ["function ", "class ", "const ", "import "]),
            (".ts", ["function ", "class ", "const ", "import "]),
            (".jsx", ["function ", "class ", "const ", "import "]),
            (".tsx", ["function ", "class ", "const ", "import "]),
            (".go", ["func ", "type ", "import ", "package "]),
            (".rs", ["fn ", "struct ", "impl ", "use "]),
            (".txt", ["TODO", "FIXME", "NOTE", "HACK"]),
            (".md", ["TODO", "FIXME", "NOTE", "HACK"]),
        ],
    )
    def test_search_hints_by_extension(self, extension, expected_hints):
        """Correct search hints generated for each file type."""
        content = "test content\nline 2\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=extension) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = get_overview(temp_path)
            assert result["search_hints"] == expected_hints
        finally:
            Path(temp_path).unlink()


class TestToolErrorHandlers:
    """Test error handler decorator for various exception types."""

    def test_file_access_error_handler(self):
        """FileAccessError is handled correctly."""
        result = get_overview("/nonexistent/path/to/file.txt")

        assert "error" in result
        assert "File access failed" in result["error"]
        assert "suggestion" in result
        assert "Check file path" in result["suggestion"]

    def test_search_error_handler(self):
        """SearchError is handled correctly."""
        content = "test content\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            # Trigger SearchError by using regex + fuzzy together
            result = search_content(temp_path, "pattern", fuzzy=True, regex=True)

            assert "error" in result
            assert "Search failed" in result["error"]
            assert "suggestion" in result
        finally:
            Path(temp_path).unlink()

    def test_edit_error_handler(self):
        """EditError is handled correctly."""
        # Empty changes array triggers edit error
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("content\n")
            temp_path = f.name

        try:
            result = edit_content(temp_path, changes=[])

            assert "error" in result
            assert "Empty changes array" in result["error"]
        finally:
            Path(temp_path).unlink()

    def test_tree_sitter_error_handler(self):
        """TreeSitterError is handled gracefully."""
        # TreeSitterError in tools is handled gracefully (falls back)
        # We can test by mocking generate_outline to raise TreeSitterError
        content = "def foo():\n    pass\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            # Even if tree-sitter fails, get_overview should work
            with patch(
                "src.tools.generate_outline",
                side_effect=TreeSitterError("Test error"),
            ):
                result = get_overview(temp_path)

                # Should still return valid result with empty outline (fallback)
                assert "line_count" in result
                assert result["outline"] == []
        finally:
            Path(temp_path).unlink()

    def test_general_exception_handler(self):
        """Unexpected exceptions are handled."""
        # Mock to raise unexpected exception
        with patch(
            "src.tools.normalize_path",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = get_overview("/some/path.txt")

            assert "error" in result
            assert "Unexpected error" in result["error"]
            assert "suggestion" in result


class TestReadContentModes:
    """Test read_content with various modes and parameters."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file for testing."""
        content = "\n".join([f"Line {i}: content here" for i in range(1, 101)])
        file = tmp_path / "sample.txt"
        file.write_text(content)
        return str(file)

    @pytest.mark.parametrize(
        "kwargs,check",
        [
            # Basic offset/limit
            (
                {"offset": 10, "limit": 5},
                lambda r: r["start_line"] == 10 and r["lines_returned"] == 5,
            ),
            # Head mode
            (
                {"limit": 10, "mode": "head"},
                lambda r: r["start_line"] == 1 and r["mode"] == "head",
            ),
            # Tail mode
            ({"limit": 10, "mode": "tail"}, lambda r: r["mode"] == "tail"),
            # Default offset
            ({"limit": 50}, lambda r: r["start_line"] == 1),
        ],
    )
    def test_read_modes(self, sample_file, kwargs, check):
        """Table-driven tests for read_content modes."""
        result = read_content(sample_file, **kwargs)
        assert check(result), f"Check failed for kwargs={kwargs}, result={result}"

    @pytest.mark.parametrize(
        "kwargs,error_msg",
        [
            ({"offset": 0}, "offset must be >= 1"),
            ({"limit": 0}, "limit must be >= 1"),
            ({"mode": "invalid"}, "Invalid mode"),
        ],
    )
    def test_read_content_validation(self, sample_file, kwargs, error_msg):
        """Parameter validation returns appropriate errors."""
        result = read_content(sample_file, **kwargs)
        assert "error" in result
        assert error_msg in result["error"]

    def test_read_content_offset_ignored_in_tail(self, sample_file):
        """Offset ignored warning in tail mode."""
        result = read_content(sample_file, offset=50, limit=10, mode="tail")
        assert "warnings" in result
        assert any("offset ignored" in w for w in result["warnings"])

    def test_read_content_offset_ignored_with_pattern(self, sample_file):
        """Offset ignored warning when pattern is set."""
        result = read_content(sample_file, offset=50, pattern="Line 25")
        assert "warnings" in result
        assert any("offset ignored" in w for w in result["warnings"])

    def test_read_content_pattern_not_found(self, sample_file):
        """Pattern not found returns error."""
        result = read_content(sample_file, pattern="NONEXISTENT_PATTERN_XYZ")
        assert "error" in result
        assert "not found" in result["error"]

    def test_read_content_semantic_mode_fallback(self, sample_file):
        """Semantic mode falls back to line mode on error."""
        # Mock get_semantic_chunk to raise exception
        with patch("src.tools.get_semantic_chunk", side_effect=Exception("Test")):
            result = read_content(sample_file, mode="semantic", limit=10)
            # Should fall back and still return content
            assert "content" in result
            assert result["mode"] == "lines" or "error" not in result


class TestEditContentValidation:
    """Test edit_content parameter validation."""

    @pytest.fixture
    def editable_file(self, tmp_path):
        """Create editable file."""
        content = "old_value = 1\nold_name = 'test'\n"
        file = tmp_path / "edit_test.py"
        file.write_text(content)
        return str(file)

    @pytest.mark.parametrize(
        "changes,error_fragment",
        [
            ([], "Empty changes array"),
            ([{"replace": "new"}], "missing required 'search' field"),
            ([{"search": "old"}], "missing required 'replace' field"),
        ],
    )
    def test_edit_content_validation_errors(
        self, editable_file, changes, error_fragment
    ):
        """Table-driven validation error tests."""
        result = edit_content(editable_file, changes=changes)
        assert "error" in result
        assert error_fragment in result["error"]

    def test_edit_content_too_many_changes(self, editable_file):
        """Too many changes returns error."""
        # Create more changes than max allowed (default 100)
        changes = [{"search": f"pattern{i}", "replace": f"new{i}"} for i in range(200)]
        result = edit_content(editable_file, changes=changes)
        assert "error" in result
        assert "Too many changes" in result["error"]

    def test_edit_content_preview_mode(self, editable_file):
        """Preview mode shows diff without modifying file."""
        original = Path(editable_file).read_text()

        result = edit_content(
            editable_file,
            changes=[{"search": "old_value", "replace": "new_value"}],
            preview=True,
        )

        assert result["success"] is True
        assert result["preview"] is not None  # Contains diff text
        assert result["backup_created"] is None  # No backup in preview
        # File unchanged
        assert Path(editable_file).read_text() == original

    def test_edit_content_actual_edit(self, editable_file):
        """Non-preview mode modifies file."""
        result = edit_content(
            editable_file,
            changes=[{"search": "old_value", "replace": "new_value"}],
            preview=False,
        )

        assert result["success"] is True
        assert result["backup_created"] is not None  # Backup path
        assert "new_value" in Path(editable_file).read_text()

    def test_multiple_changes(self):
        """Multiple changes applied in single call."""
        content = "def foo():\n    pass\n\ndef bar():\n    pass\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[
                    {"search": "def foo():", "replace": "def foo(x):"},
                    {"search": "def bar():", "replace": "def bar(y):"},
                ],
                preview=True,
            )

            assert result["success"] is True
            assert result["changes_applied"] == 2
            assert result["changes_failed"] == 0
            assert len(result["results"]) == 2
        finally:
            Path(temp_path).unlink()

    def test_single_change_match_type(self):
        """Single change returns match_type in result."""
        content = "hello world\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[{"search": "hello", "replace": "hi"}],
                preview=True,
            )

            assert result["success"] is True
            assert result["changes_applied"] == 1
            assert result["results"][0]["match_type"] == "exact"
        finally:
            Path(temp_path).unlink()

    def test_partial_success_response(self):
        """Partial success includes per-change results."""
        content = "def foo():\n    pass\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[
                    {"search": "def foo():", "replace": "def foo(x):"},
                    {"search": "NONEXISTENT", "replace": "..."},
                ],
                preview=True,
            )

            assert result["success"] is True  # At least one succeeded
            assert result["changes_applied"] == 1
            assert result["changes_failed"] == 1
            assert len(result["results"]) == 2
            assert result["results"][0]["success"] is True
            assert result["results"][1]["success"] is False
            assert "error" in result["results"][1]
        finally:
            Path(temp_path).unlink()

    def test_per_change_fuzzy_override(self):
        """Per-change fuzzy setting overrides default."""
        content = "def foo():\n    pass\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[
                    {"search": "def fooo():", "replace": "def bar():", "fuzzy": False},
                    {"search": "def foo():", "replace": "def baz():"},
                ],
                fuzzy=True,
                preview=True,
            )

            assert result["success"] is True
            assert result["results"][0]["success"] is False  # Exact match failed
            assert result["results"][1]["success"] is True
        finally:
            Path(temp_path).unlink()


class TestSearchContentEdgeCases:
    """Test search_content edge cases."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create sample file."""
        content = "class MyClass:\n    def method(self):\n        pass\n"
        file = tmp_path / "sample.py"
        file.write_text(content)
        return str(file)

    def test_search_no_matches(self, sample_file):
        """Search with no matches returns zero results."""
        result = search_content(sample_file, "NONEXISTENT_PATTERN", fuzzy=False)
        assert result["total_matches"] == 0
        assert result["results"] == []

    def test_search_truncated_line(self, tmp_path):
        """Long matching lines are truncated."""
        long_content = "x" * 2000 + "PATTERN" + "y" * 2000
        file = tmp_path / "long.txt"
        file.write_text(long_content)

        result = search_content(str(file), "PATTERN", fuzzy=False)

        if result["total_matches"] > 0:
            # Match should be truncated
            assert result["results"][0]["truncated"] is True

    def test_search_semantic_context_fallback(self, sample_file):
        """Semantic context extraction falls back on error."""
        with patch(
            "src.tools.extract_semantic_context",
            side_effect=Exception("Test"),
        ):
            result = search_content(sample_file, "class", fuzzy=False)
            # Should still return results
            assert result["total_matches"] > 0
            # Context should fall back to line number
            assert "Line" in result["results"][0]["semantic_context"]
