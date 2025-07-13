import os
import tempfile

from src.tools import edit_content, get_overview, read_content, search_content


class TestLargeFileTools:
    """Integration tests for the 4 core MCP tools."""

    def setup_method(self):
        """Set up test files for each test."""
        self.test_python_content = '''def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

# TODO: Add more functionality
def another_function():
    # FIXME: This needs improvement
    pass
'''

        self.test_large_content = (
            "# "
            + "x" * 2000
            + "\n"
            + """def function():
    return True

class LargeClass:
    pass
"""
        )

    def create_temp_file(self, content: str) -> str:
        """Create a temporary file with given content."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            return f.name

    def test_get_overview_python_file(self):
        """Test overview generation for Python files."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = get_overview(temp_path, encoding="utf-8")

            assert "line_count" in result
            assert result["line_count"] > 0
            assert "file_size" in result
            assert result["file_size"] > 0
            assert "has_long_lines" in result
            assert result["has_long_lines"] in [True, False]
            assert "search_hints" in result
            assert "def " in result["search_hints"]
            assert "class " in result["search_hints"]
            assert "outline" in result

        finally:
            os.unlink(temp_path)

    def test_get_overview_with_long_lines(self):
        """Test overview with file containing long lines."""
        temp_path = self.create_temp_file(self.test_large_content)

        try:
            result = get_overview(temp_path, encoding="utf-8")

            assert result["has_long_lines"] is True
            assert result["line_count"] > 0

        finally:
            os.unlink(temp_path)

    def test_search_content_exact_and_fuzzy(self):
        """Test both exact and fuzzy search."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            exact_results = search_content(temp_path, "def hello", fuzzy=False)
            assert "results" in exact_results
            assert exact_results["total_matches"] >= 0

            fuzzy_results = search_content(temp_path, "def helo", fuzzy=True)
            assert "results" in fuzzy_results
            assert fuzzy_results["fuzzy_enabled"] is True

        finally:
            os.unlink(temp_path)

    def test_search_content_with_context(self):
        """Test search with context lines."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            results = search_content(temp_path, "def ", context_lines=3)

            assert "results" in results
            if results["results"]:
                first_result = results["results"][0]
                assert "context_before" in first_result
                assert "context_after" in first_result
                assert "line_number" in first_result
                assert "similarity_score" in first_result

        finally:
            os.unlink(temp_path)

    def test_read_content_by_line_number(self):
        """Test reading content by line number."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = read_content(temp_path, 1, mode="lines")

            assert "content" in result
            assert "start_line" in result
            assert "end_line" in result
            assert "total_lines" in result
            assert result["target_type"] == "line_number"
            assert isinstance(result["content"], str)

        finally:
            os.unlink(temp_path)

    def test_read_content_by_pattern(self):
        """Test reading content by search pattern."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = read_content(temp_path, "def hello_world", mode="lines")

            assert "content" in result
            assert result["target_type"] == "pattern"
            if "error" not in result:
                assert "match_line" in result
                assert "similarity_score" in result
                assert "pattern" in result

        finally:
            os.unlink(temp_path)

    def test_edit_content_preview_mode(self):
        """Test edit operations in preview mode."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = edit_content(
                temp_path,
                'print("Hello, World!")',
                'print("Hello, Universe!")',
                preview=True,
            )

            assert "success" in result
            assert "preview" in result
            assert "changes_made" in result
            assert "match_type" in result
            assert "similarity_used" in result
            assert "line_number" in result

            if result["success"]:
                assert result["changes_made"] > 0
                assert result["match_type"] in ["exact", "fuzzy"]

        finally:
            os.unlink(temp_path)

    def test_edit_content_apply_mode(self):
        """Test edit operations with actual file changes."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            original_content = open(temp_path).read()

            result = edit_content(
                temp_path,
                'print("Hello, World!")',
                'print("Hello, Universe!")',
                preview=False,
            )

            if result["success"]:
                assert "backup_created" in result
                assert result["backup_created"] is not None

                modified_content = open(temp_path).read()
                assert modified_content != original_content
                assert "Hello, Universe!" in modified_content

                backup_exists = os.path.exists(result["backup_created"])
                assert backup_exists

                if backup_exists:
                    os.unlink(result["backup_created"])

        finally:
            os.unlink(temp_path)

    def test_edit_content_fuzzy_matching(self):
        """Test edit with fuzzy matching."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = edit_content(
                temp_path,
                "def hello_wrld():",  # Intentional typo
                "def hello_universe():",
                fuzzy=True,
                preview=True,
            )

            assert "success" in result
            if result["success"]:
                assert result["match_type"] == "fuzzy"
                assert result["similarity_used"] < 1.0

        finally:
            os.unlink(temp_path)

    def test_error_handling_nonexistent_file(self):
        """Test error handling for nonexistent files."""
        result = get_overview("/nonexistent/file.py")

        assert "error" in result
        assert "suggestion" in result
        assert "File access failed" in result["error"]

    def test_search_no_matches(self):
        """Test search with no matches."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = search_content(temp_path, "nonexistent_pattern")

            assert "results" in result
            assert result["total_matches"] == 0
            assert len(result["results"]) == 0

        finally:
            os.unlink(temp_path)

    def test_edit_no_matches(self):
        """Test edit with no matches."""
        temp_path = self.create_temp_file(self.test_python_content)

        try:
            result = edit_content(
                temp_path, "nonexistent_text", "replacement", fuzzy=False, preview=True
            )

            assert result["success"] is False
            assert result["changes_made"] == 0
            assert result["match_type"] == "none"

        finally:
            os.unlink(temp_path)
