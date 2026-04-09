"""Integration tests for read_enclosing tool.

End-to-end tests exercising the full tool path for enclosing definition
lookup and fallback context window.
"""

from pathlib import Path

from src.tools import read_enclosing


class TestReadEnclosingIntegration:
    """Integration tests for the read_enclosing tool."""

    @property
    def test_data_dir(self) -> Path:
        return Path(__file__).parent.parent / "test_data"

    def test_enclosing_read_on_python_file(self):
        """Enclosing read returns correct dict shape for a Python function."""
        python_file = self.test_data_dir / "python" / "django-models.py"
        # Line 62 is inside __repr__ of the Deferred class
        result = read_enclosing(str(python_file), line=62)

        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        assert isinstance(result["start_line"], int)
        assert isinstance(result["end_line"], int)
        assert result["start_line"] <= result["end_line"]
        assert result["mode"] == "enclosing"
        assert isinstance(result["enclosing_symbol"], str)
        assert len(result["enclosing_symbol"]) > 0
        assert result["lines_returned"] == result["end_line"] - result["start_line"] + 1
        assert result["total_lines"] > 0

    def test_fallback_on_non_code_file(self):
        """Fallback returns context_window mode for non-code files."""
        md_file = self.test_data_dir / "markdown" / "fastapi-docs.md"
        result = read_enclosing(str(md_file), line=5, context_lines=20)

        assert result["mode"] == "context_window"
        assert result["enclosing_symbol"] is None
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        assert result["lines_returned"] <= 20
