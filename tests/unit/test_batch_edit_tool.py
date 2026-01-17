"""Tests for batch edit functionality via the tools API."""

import tempfile
from pathlib import Path

from src.tools import edit_content


class TestBatchEditTool:
    """Test edit_content tool with batch mode."""

    def test_batch_edit_via_tool(self):
        """Test batch edit through the edit_content tool."""
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

    def test_batch_edit_empty_changes(self):
        """Empty array returns error."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("test")
            temp_path = f.name

        try:
            result = edit_content(temp_path, changes=[])

            assert "error" in result
            assert "Empty" in result["error"]

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_missing_search_field(self):
        """Error when change missing required 'search' field."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("test")
            temp_path = f.name

        try:
            result = edit_content(temp_path, changes=[{"replace": "new"}])

            assert "error" in result
            assert "missing required 'search'" in result["error"]

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_missing_replace_field(self):
        """Error when change missing required 'replace' field."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("test")
            temp_path = f.name

        try:
            result = edit_content(temp_path, changes=[{"search": "old"}])

            assert "error" in result
            assert "missing required 'replace'" in result["error"]

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_invalid_change_format(self):
        """Error when change missing required fields."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("test")
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[{"search": "foo"}],  # Missing replace
            )

            assert "error" in result
            assert "missing" in result["error"].lower()

        finally:
            Path(temp_path).unlink()

    def test_single_change_in_array(self):
        """Single edit via changes array works."""
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
            assert result["changes_failed"] == 0
            assert len(result["results"]) == 1
            assert result["results"][0]["match_type"] == "exact"

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_partial_success_response(self):
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
            # First change succeeded
            assert result["results"][0]["success"] is True
            assert result["results"][0]["index"] == 0
            # Second change failed
            assert result["results"][1]["success"] is False
            assert result["results"][1]["index"] == 1
            assert "error" in result["results"][1]

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_with_per_change_fuzzy(self):
        """Per-change fuzzy setting works through tool API."""
        content = "def foo():\n    pass\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = edit_content(
                temp_path,
                changes=[
                    # This has a typo - fuzzy=False should make it fail
                    {"search": "def fooo():", "replace": "def bar():", "fuzzy": False},
                    # This should succeed
                    {"search": "def foo():", "replace": "def baz():"},
                ],
                fuzzy=True,  # Default fuzzy
                preview=True,
            )

            assert result["success"] is True
            # First change should fail (exact match required)
            assert result["results"][0]["success"] is False
            # Second change should succeed
            assert result["results"][1]["success"] is True

        finally:
            Path(temp_path).unlink()
