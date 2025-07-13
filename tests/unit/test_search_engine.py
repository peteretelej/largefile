import os
import tempfile

import pytest

from src.exceptions import SearchError
from src.search_engine import (
    find_exact_matches,
    find_fuzzy_matches,
    search_file,
)


class TestSearchEngine:
    def test_find_exact_matches(self):
        """Test exact string matching."""
        lines = ["def hello():", "    print('world')", "def goodbye():"]

        matches = find_exact_matches(lines, "def ")
        assert len(matches) == 2
        assert matches[0].line_number == 1
        assert matches[1].line_number == 3
        assert all(m.similarity_score == 1.0 for m in matches)
        assert all(m.match_type == "exact" for m in matches)

    def test_find_exact_matches_no_results(self):
        """Test exact matching with no results."""
        lines = ["def hello():", "    print('world')"]

        matches = find_exact_matches(lines, "class ")
        assert len(matches) == 0

    def test_find_fuzzy_matches(self):
        """Test fuzzy matching."""
        lines = ["def hello():", "deff goodbye():", "define something"]

        matches = find_fuzzy_matches(lines, "hello", 0.5)
        assert len(matches) >= 1
        assert all(m.similarity_score >= 0.5 for m in matches)
        assert all(m.match_type == "fuzzy" for m in matches)

    def test_search_file_exact_only(self):
        """Test file search with exact matching only."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("def function1():\n    pass\ndef function2():\n    pass")
            temp_path = f.name

        try:
            matches = search_file(temp_path, "def ", fuzzy=False)
            assert len(matches) == 2
            assert all(m.match_type == "exact" for m in matches)
        finally:
            os.unlink(temp_path)

    def test_search_file_with_fuzzy(self):
        """Test file search with fuzzy matching enabled."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("def function():\n    pass\ndeff typo():\n    pass")
            temp_path = f.name

        try:
            matches = search_file(temp_path, "def ", fuzzy=True)
            assert len(matches) >= 1
            exact_matches = [m for m in matches if m.match_type == "exact"]
            assert len(exact_matches) >= 1
        finally:
            os.unlink(temp_path)

    def test_search_file_nonexistent(self):
        """Test search on nonexistent file."""
        with pytest.raises(SearchError):
            search_file("/nonexistent/file.txt", "pattern")
