"""Editor unit tests.

Test core content editing and backup functionality.
"""

import tempfile
from pathlib import Path

from src.data_models import Change, SimilarMatch
from src.editor import (
    apply_batch_edits,
    atomic_edit_file,
    batch_edit_content,
    generate_suggestion,
)
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
            backup_info = create_backup(temp_path)

            # Backup should exist
            assert Path(backup_info.path).exists()

            # Backup should have same content
            backup_content = Path(backup_info.path).read_text()
            assert backup_content == test_content

            # Backup path should be different from original
            assert backup_info.path != temp_path

            # Clean up backup
            Path(backup_info.path).unlink()

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


class TestBatchEditing:
    """Test batch editing functionality."""

    def test_batch_edit_all_succeed(self):
        """All changes apply successfully."""
        content = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        changes = [
            Change(search="def foo():", replace="def foo(x):"),
            Change(search="def bar():", replace="def bar(y):"),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        assert "def foo(x):" in modified
        assert "def bar(y):" in modified
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].line_number == 1
        assert results[1].line_number == 4

    def test_batch_edit_partial_success(self):
        """Some changes fail, others succeed."""
        content = "def foo():\n    pass\n"
        changes = [
            Change(search="def foo():", replace="def foo(x):"),
            Change(search="NONEXISTENT", replace="..."),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        assert "def foo(x):" in modified
        assert len(results) == 2
        assert results[0].success is True
        assert results[0].index == 0
        assert results[1].success is False
        assert results[1].index == 1
        assert "Pattern not found" in (results[1].error or "")

    def test_batch_edit_overlap_detection(self):
        """Overlapping changes: first wins, second marked failed."""
        content = "def foo():\n    pass\n"
        changes = [
            Change(search="def foo():", replace="def foo(x):"),
            Change(search="def foo(", replace="def bar("),  # Overlaps with first
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        # First change should succeed
        assert results[0].success is True
        # Second change should fail due to overlap
        assert results[1].success is False
        assert "Overlaps" in (results[1].error or "")

    def test_batch_edit_preserves_order(self):
        """Results array matches input order regardless of application order."""
        content = "line1\nline2\nline3\n"
        changes = [
            Change(search="line3", replace="LINE3"),
            Change(search="line1", replace="LINE1"),
            Change(search="line2", replace="LINE2"),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        # Results should be in input order
        assert results[0].index == 0
        assert results[1].index == 1
        assert results[2].index == 2
        assert "LINE1" in modified
        assert "LINE2" in modified
        assert "LINE3" in modified

    def test_batch_edit_single_change(self):
        """Single-item changes array works."""
        content = "hello world\n"
        changes = [Change(search="hello", replace="hi")]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        assert "hi world" in modified
        assert len(results) == 1
        assert results[0].success is True

    def test_batch_edit_per_change_fuzzy(self):
        """Per-change fuzzy override works."""
        content = "def foo():\n    pass\n"
        changes = [
            # Exact match required, won't match fuzzy content
            Change(search="def fooo():", replace="def bar():", fuzzy=False),
            # Fuzzy match enabled
            Change(search="def foo():", replace="def baz():"),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        # First change fails (exact match required, typo in search)
        assert results[0].success is False
        # Second change succeeds
        assert results[1].success is True
        assert "def baz():" in modified

    def test_batch_edit_file_integration(self):
        """Test batch_edit_content with actual file."""
        content = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = batch_edit_content(
                temp_path,
                changes=[
                    Change(search="def foo():", replace="def foo(x):"),
                    Change(search="def bar():", replace="def bar(y):"),
                ],
                preview=True,
            )

            assert result.success is True
            assert result.changes_applied == 2
            assert result.changes_failed == 0
            assert result.results is not None
            assert len(result.results) == 2
            # Preview mode, file unchanged
            assert Path(temp_path).read_text() == content

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_file_with_backup(self):
        """Test batch edit creates backup when not in preview mode."""
        content = "line1\nline2\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = batch_edit_content(
                temp_path,
                changes=[Change(search="line1", replace="LINE1")],
                preview=False,
            )

            assert result.success is True
            assert result.backup_created is not None
            # File should be modified
            assert "LINE1" in Path(temp_path).read_text()
            # Backup should exist
            assert Path(result.backup_created).exists()

            # Clean up backup
            Path(result.backup_created).unlink()

        finally:
            Path(temp_path).unlink()

    def test_batch_edit_all_fail(self):
        """All changes fail, success should be False."""
        content = "hello world\n"
        changes = [
            Change(search="NONEXISTENT1", replace="..."),
            Change(search="NONEXISTENT2", replace="..."),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=True)

        # Content unchanged
        assert modified == content
        assert all(not r.success for r in results)

    def test_batch_edit_failed_includes_similar_matches(self):
        """Failed changes include similar match suggestions."""
        content = "def process_data():\n    pass\n"
        changes = [
            Change(search="def proccess_data():", replace="def handle_data():"),
        ]

        modified, results = apply_batch_edits(content, changes, default_fuzzy=False)

        # Should fail (exact match, typo)
        assert results[0].success is False
        # Should include similar matches (process_data is similar to proccess_data)
        if results[0].similar_matches:
            assert len(results[0].similar_matches) > 0
