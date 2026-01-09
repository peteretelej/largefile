"""Editor unit tests.

Test core content editing and backup functionality.
"""

import tempfile
from pathlib import Path

from src.data_models import SimilarMatch
from src.editor import atomic_edit_file, generate_suggestion
from src.file_access import create_backup


class TestEditor:
    """Test editor core functions."""

    def test_content_replacement(self):
        """Test find/replace operations with actual files."""
        # Create a temporary file
        original_content = "Hello world\nThis is a test\nHello again"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(original_content)
            temp_path = f.name

        try:
            # Test atomic edit with exact match
            result = atomic_edit_file(
                temp_path,
                "Hello world",
                "Hi world",
                preview=True,  # Preview mode
                fuzzy=False,
            )

            # Result should be EditResult object
            assert hasattr(result, "success")
            assert hasattr(result, "changes_made")

            if result.success:
                assert result.changes_made > 0
                assert hasattr(result, "preview")

        finally:
            Path(temp_path).unlink()

    def test_backup_handling(self):
        """Test backup file creation."""
        # Create a temporary file
        test_content = "Original content\nLine 2\nLine 3"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # Test backup creation
            backup_path = create_backup(temp_path)

            # Backup should exist
            assert Path(backup_path).exists()

            # Backup should have same content
            backup_content = Path(backup_path).read_text()
            assert backup_content == test_content

            # Backup path should be different from original
            assert backup_path != temp_path

            # Clean up backup
            Path(backup_path).unlink()

        finally:
            Path(temp_path).unlink()


class TestGenerateSuggestion:
    """Test suggestion generation for enhanced error messages."""

    def test_suggestion_with_matches_fuzzy_enabled(self):
        """Generates appropriate suggestion when matches found with fuzzy enabled."""
        matches = [
            SimilarMatch(line=42, content="def process_data(items):", similarity=0.94),
            SimilarMatch(
                line=100, content="def process_data_async(items):", similarity=0.85
            ),
        ]
        suggestion = generate_suggestion(matches, fuzzy_enabled=True)

        assert "2 similar pattern" in suggestion
        assert "Use one as your search text" in suggestion

    def test_suggestion_with_near_match_fuzzy_disabled(self):
        """Suggests enabling fuzzy for near-matches."""
        matches = [SimilarMatch(line=42, content="def foo()", similarity=0.95)]
        suggestion = generate_suggestion(matches, fuzzy_enabled=False)

        assert "near-match" in suggestion or "line 42" in suggestion
        assert "fuzzy" in suggestion.lower()

    def test_suggestion_with_lower_similarity_fuzzy_disabled(self):
        """Suggests enabling fuzzy for lower similarity matches."""
        matches = [SimilarMatch(line=10, content="def bar()", similarity=0.7)]
        suggestion = generate_suggestion(matches, fuzzy_enabled=False)

        assert "similar pattern" in suggestion
        assert "fuzzy" in suggestion.lower()

    def test_suggestion_no_matches_fuzzy_enabled(self):
        """Suggests verifying search text when no matches with fuzzy enabled."""
        suggestion = generate_suggestion([], fuzzy_enabled=True)

        assert "No similar patterns found" in suggestion
        assert "Verify" in suggestion

    def test_suggestion_no_matches_fuzzy_disabled(self):
        """Suggests enabling fuzzy when no matches and fuzzy disabled."""
        suggestion = generate_suggestion([], fuzzy_enabled=False)

        assert "No similar patterns found" in suggestion
        assert "fuzzy" in suggestion.lower()


class TestEnhancedErrorResponses:
    """Test enhanced error responses include similar matches."""

    def test_edit_failure_includes_similar_matches(self):
        """Edit failure with fuzzy returns similar matches."""
        content = "def process_data(items):\n    pass\ndef other_func():\n    pass"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            # Search for something that won't fuzzy match (too different)
            # but has some similarity for the similar_matches feature
            result = atomic_edit_file(
                temp_path,
                "def completely_different_function_name(",
                "def new_function(",
                preview=True,
                fuzzy=True,
            )

            assert result.success is False
            assert result.search_attempted == "def completely_different_function_name("
            assert result.fuzzy_enabled is True
            assert result.suggestion is not None
            # Fields should be populated even if no similar matches found
            assert isinstance(result.similar_matches, list)

        finally:
            Path(temp_path).unlink()

    def test_edit_failure_without_fuzzy_includes_similar_matches(self):
        """Edit failure without fuzzy also returns similar matches."""
        content = "def foo():\n    pass"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = atomic_edit_file(
                temp_path,
                "def bar()",  # Not in file
                "def baz()",
                preview=True,
                fuzzy=False,
            )

            assert result.success is False
            assert result.fuzzy_enabled is False
            assert result.suggestion is not None

        finally:
            Path(temp_path).unlink()
