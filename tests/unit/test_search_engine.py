"""Search engine unit tests.

Test fuzzy matching, similarity search, and enhanced error messages.
"""

from src.data_models import SimilarMatch
from src.search_engine import find_similar_patterns


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
