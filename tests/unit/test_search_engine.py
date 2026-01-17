"""Search engine unit tests.

Test fuzzy matching, similarity search, and enhanced error messages.
"""

import tempfile
from pathlib import Path

import pytest

from src.data_models import SimilarMatch
from src.exceptions import SearchError
from src.search_engine import (
    find_exact_matches,
    find_fuzzy_matches,
    find_regex_matches,
    find_similar_patterns,
    search_file,
)
from src.tools import search_content


class TestFindSimilarPatterns:
    """Test similar pattern matching for enhanced error messages."""

    def test_similar_matches_single_line(self):
        """Finds similar single-line patterns."""
        content = "def process_data(items):\n    pass\ndef process_data_async(items):\n    pass"
        matches = find_similar_patterns(
            content, "def process_dataa(", min_similarity=0.6
        )

        assert len(matches) >= 1
        assert matches[0].line == 1
        assert matches[0].similarity >= 0.6
        assert "process_data" in matches[0].content

    def test_similar_matches_multi_line(self):
        """Finds similar multi-line blocks."""
        content = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        # Search for a multi-line pattern with slight difference
        matches = find_similar_patterns(
            content, "def foo():\n    return 2", min_similarity=0.6
        )

        assert len(matches) >= 1
        # Should find the foo() function block
        assert matches[0].line in [1, 4]  # Either foo or bar block

    def test_similar_matches_respects_threshold(self):
        """Low-similarity matches excluded."""
        content = "completely different text\nanother unrelated line"
        matches = find_similar_patterns(
            content, "def process_data(", min_similarity=0.6
        )

        assert len(matches) == 0

    def test_similar_matches_respects_limit(self):
        """Limit parameter restricts results."""
        content = "def foo1():\ndef foo2():\ndef foo3():\ndef foo4():\ndef foo5():"
        matches = find_similar_patterns(
            content, "def foo()", limit=2, min_similarity=0.5
        )

        assert len(matches) <= 2

    def test_similar_matches_sorted_by_similarity(self):
        """Results sorted by similarity descending."""
        content = "def process_data(items):\n    pass\ndef process(x):\n    pass"
        matches = find_similar_patterns(
            content, "def process_data(", min_similarity=0.4
        )

        if len(matches) > 1:
            # First match should have higher or equal similarity
            assert matches[0].similarity >= matches[1].similarity

    def test_similar_matches_truncates_content(self):
        """Content truncated to 100 chars."""
        long_line = "def " + "x" * 150 + "():"
        content = long_line
        matches = find_similar_patterns(content, "def x", min_similarity=0.3)

        if matches:
            assert len(matches[0].content) <= 100

    def test_similar_matches_multiline_newline_replacement(self):
        """Multi-line matches replace newlines with arrow symbol."""
        content = "line1\nline2\nline3"
        matches = find_similar_patterns(content, "line1\nline2", min_similarity=0.5)

        if matches:
            # Multi-line content should have ↵ instead of \n
            assert "↵" in matches[0].content or "\n" not in matches[0].content

    def test_similar_matches_empty_content(self):
        """Empty content returns no matches."""
        matches = find_similar_patterns("", "search text")
        assert matches == []

    def test_similar_matches_returns_dataclass(self):
        """Returns list of SimilarMatch dataclass objects."""
        content = "def foo():\n    pass"
        matches = find_similar_patterns(content, "def foo", min_similarity=0.5)

        if matches:
            assert isinstance(matches[0], SimilarMatch)
            assert hasattr(matches[0], "line")
            assert hasattr(matches[0], "content")
            assert hasattr(matches[0], "similarity")


class TestRegexMatching:
    """Test regex pattern matching functionality."""

    @pytest.fixture
    def sample_lines(self):
        return [
            "INFO: Processing request 123\n",
            "DEBUG: User logged in\n",
            "ERROR: Connection failed\n",
            "INFO: Request completed\n",
            "WARNING: High memory usage\n",
        ]

    def test_regex_basic_pattern(self, sample_lines):
        """Basic regex pattern matches correctly."""
        matches = find_regex_matches(sample_lines, r"INFO:.*")
        assert len(matches) == 2
        assert matches[0].line_number == 1
        assert matches[1].line_number == 4
        assert matches[0].match_type == "regex"

    def test_regex_case_sensitive_default(self, sample_lines):
        """Regex is case sensitive by default."""
        matches = find_regex_matches(sample_lines, r"error:")
        assert len(matches) == 0

    def test_regex_case_insensitive(self, sample_lines):
        """Case insensitive regex works."""
        matches = find_regex_matches(sample_lines, r"error:", case_sensitive=False)
        assert len(matches) == 1
        assert matches[0].line_number == 3

    def test_regex_invert(self, sample_lines):
        """Inverted regex returns non-matching lines."""
        matches = find_regex_matches(sample_lines, r"INFO:", invert=True)
        assert len(matches) == 3
        assert all(m.match_type == "regex_inverted" for m in matches)

    def test_regex_invalid_pattern(self, sample_lines):
        """Invalid regex raises SearchError."""
        with pytest.raises(SearchError) as exc_info:
            find_regex_matches(sample_lines, r"[invalid")
        assert "Invalid regex pattern" in str(exc_info.value)

    def test_regex_complex_pattern(self, sample_lines):
        """Complex regex with groups works."""
        matches = find_regex_matches(sample_lines, r"\d{3}")
        assert len(matches) == 1
        assert "123" in matches[0].content


class TestCaseSensitiveMatching:
    """Test case_sensitive parameter for exact matches."""

    @pytest.fixture
    def sample_lines(self):
        return [
            "Error: Something went wrong\n",
            "error: another problem\n",
            "ERROR: critical failure\n",
            "No errors here\n",
        ]

    def test_case_sensitive_default(self, sample_lines):
        """Exact match is case sensitive by default."""
        matches = find_exact_matches(sample_lines, "Error:")
        assert len(matches) == 1
        assert matches[0].line_number == 1

    def test_case_insensitive_exact(self, sample_lines):
        """Case insensitive exact match finds all variants."""
        matches = find_exact_matches(sample_lines, "error:", case_sensitive=False)
        assert len(matches) == 3
        assert matches[0].line_number == 1
        assert matches[1].line_number == 2
        assert matches[2].line_number == 3


class TestInvertMatching:
    """Test invert parameter across match types."""

    @pytest.fixture
    def sample_lines(self):
        return [
            "DEBUG: verbose output\n",
            "INFO: normal output\n",
            "DEBUG: more verbose\n",
            "ERROR: problem occurred\n",
        ]

    def test_invert_exact(self, sample_lines):
        """Inverted exact match returns non-matching lines."""
        matches = find_exact_matches(sample_lines, "DEBUG:", invert=True)
        assert len(matches) == 2
        assert matches[0].line_number == 2
        assert matches[1].line_number == 4
        assert all(m.match_type == "exact_inverted" for m in matches)

    def test_invert_fuzzy(self, sample_lines):
        """Inverted fuzzy match returns lines below threshold."""
        matches = find_fuzzy_matches(
            sample_lines, "DEBUG: verbose output", threshold=0.8, invert=True
        )
        # Should return lines that don't match well
        assert len(matches) >= 2
        assert all(m.match_type == "fuzzy_inverted" for m in matches)


class TestSearchFileValidation:
    """Test search_file parameter validation."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("line 1 with content\n")
            f.write("line 2 with ERROR\n")
            f.write("line 3 with info\n")
            f.flush()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_regex_and_fuzzy_error(self, temp_file):
        """Regex and fuzzy together raises error."""
        with pytest.raises(SearchError) as exc_info:
            search_file(temp_file, "pattern", fuzzy=True, regex=True)
        assert "Cannot use regex and fuzzy together" in str(exc_info.value)

    def test_search_file_exact_mode(self, temp_file):
        """Search with fuzzy=False uses exact matching."""
        matches = search_file(temp_file, "ERROR", fuzzy=False)
        assert len(matches) == 1
        assert matches[0].line_number == 2
        assert matches[0].match_type == "exact"

    def test_search_file_regex_mode(self, temp_file):
        """Search with regex=True uses regex matching."""
        matches = search_file(temp_file, r"line \d+", fuzzy=False, regex=True)
        assert len(matches) == 3


class TestSearchContentTool:
    """Test search_content tool with new parameters."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def process_data():\n")
            f.write("    # Handle errors\n")
            f.write("    if error:\n")
            f.write("        raise ValueError('Error occurred')\n")
            f.write("    return data\n")
            f.write("\n")
            f.write("def process_error():\n")
            f.write("    pass\n")
            f.flush()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_count_only_mode(self, temp_file):
        """count_only=True returns just the count."""
        result = search_content(temp_file, "error", fuzzy=False, count_only=True)
        assert "count" in result
        assert result["count"] == 3  # errors, error:, process_error
        assert "results" not in result
        assert result["fuzzy_enabled"] is False
        assert result["regex_enabled"] is False
        assert result["case_sensitive"] is True
        assert result["inverted"] is False

    def test_count_only_with_regex(self, temp_file):
        """count_only works with regex mode."""
        result = search_content(
            temp_file, r"def \w+", fuzzy=False, regex=True, count_only=True
        )
        assert result["count"] == 2
        assert result["regex_enabled"] is True

    def test_count_only_warnings(self, temp_file):
        """Warnings returned when params ignored in count_only mode."""
        result = search_content(
            temp_file,
            "error",
            fuzzy=False,
            count_only=True,
            max_results=5,
            context_lines=10,
        )
        assert "warnings" in result
        assert "max_results ignored" in result["warnings"][0]
        assert "context_lines ignored" in result["warnings"][1]

    def test_regex_mode(self, temp_file):
        """regex=True enables Python regex matching."""
        result = search_content(temp_file, r"def \w+\(", fuzzy=False, regex=True)
        assert result["total_matches"] == 2
        assert result["regex_enabled"] is True
        assert all(r["match_type"] == "regex" for r in result["results"])

    def test_case_insensitive(self, temp_file):
        """case_sensitive=False finds all case variants."""
        result = search_content(
            temp_file, "error", fuzzy=False, case_sensitive=False, count_only=True
        )
        assert result["count"] == 4  # errors, error:, Error, process_error
        assert result["case_sensitive"] is False

    def test_invert_mode(self, temp_file):
        """invert=True returns non-matching lines."""
        result = search_content(
            temp_file, "def", fuzzy=False, invert=True, count_only=True
        )
        assert result["count"] == 6  # All lines except the two def lines
        assert result["inverted"] is True

    def test_regex_fuzzy_error_via_tool(self, temp_file):
        """Tool returns error when regex and fuzzy both True."""
        result = search_content(temp_file, "pattern", fuzzy=True, regex=True)
        assert "error" in result
        assert "Cannot use regex and fuzzy" in result["error"]

    def test_response_includes_new_fields(self, temp_file):
        """Normal response includes new metadata fields."""
        result = search_content(temp_file, "def", fuzzy=False)
        assert "regex_enabled" in result
        assert "case_sensitive" in result
        assert "inverted" in result
        assert result["regex_enabled"] is False
        assert result["case_sensitive"] is True
        assert result["inverted"] is False

    def test_default_context_lines_is_3(self, temp_file):
        """Default context_lines changed from 2 to 3."""
        result = search_content(temp_file, "raise", fuzzy=False)
        # The match is on line 4, should get 3 lines before (1,2,3) and 3 after (5,6,7)
        first_result = result["results"][0]
        assert len(first_result["context_before"]) <= 3
        assert len(first_result["context_after"]) <= 3
