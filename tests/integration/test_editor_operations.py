"""Real editor operations integration tests.

Test actual file modification, backup creation, and restoration workflows.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

from src.editor import atomic_edit_file
from src.file_access import create_backup


class TestEditorOperations:
    """Test real editor operations with temporary files."""

    def setup_method(self):
        """Create isolated temporary directory for each test."""
        timestamp = int(time.time() * 1000)
        pid = os.getpid()
        self.temp_dir = tempfile.mkdtemp(prefix=f"largefile_test_{pid}_{timestamp}_")
        self.test_files = {}

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, name: str, content: str) -> str:
        """Create test file in temporary directory."""
        file_path = os.path.join(self.temp_dir, name)
        Path(file_path).write_text(content)
        self.test_files[name] = file_path
        return file_path

    def test_actual_file_editing(self):
        """Test real file modification with backup."""
        # Create test file
        original = "Hello world\nSecond line\nThird line"
        test_file = self.create_test_file("edit_test.txt", original)

        # Perform actual edit (not preview)
        result = atomic_edit_file(
            test_file,
            "Hello world",
            "Hi universe",
            preview=False,  # ACTUAL EDIT
        )

        # Verify edit succeeded
        assert result.success is True
        assert result.changes_made == 1
        assert result.backup_created is not None

        # Verify file contents changed
        modified = Path(test_file).read_text()
        assert "Hi universe" in modified
        assert "Hello world" not in modified
        assert "Second line\nThird line" in modified

        # Verify backup exists and has original content
        backup_file = result.backup_created
        assert Path(backup_file).exists()
        assert Path(backup_file).read_text() == original

    def test_multiple_occurrence_edits(self):
        """Test editing when search text appears multiple times."""
        original = "test line\nanother test line\nfinal test"
        test_file = self.create_test_file("multi_edit.txt", original)

        # Edit first occurrence (default behavior)
        result = atomic_edit_file(test_file, "test", "demo", preview=False)

        assert result.success is True
        assert result.changes_made == 1  # Only first occurrence

        # Verify first change
        modified = Path(test_file).read_text()
        assert "demo line\nanother test line\nfinal test" == modified

    def test_fuzzy_matching_edits(self):
        """Test fuzzy matching with real file changes."""
        original = "def calculate_sum():\n    return a + b\n\nprint('done')"
        test_file = self.create_test_file("fuzzy_edit.py", original)

        # Fuzzy match with extra whitespace
        result = atomic_edit_file(
            test_file,
            "def  calculate_sum( ):",  # Extra spaces
            "def calculate_total():",
            preview=False,
            fuzzy=True,
        )

        assert result.success is True
        assert result.changes_made == 1

        modified = Path(test_file).read_text()
        assert "def calculate_total():" in modified
        assert "calculate_sum" not in modified

    def test_backup_and_restore(self):
        """Test backup creation and restoration workflow."""
        original = "Important data\nCritical information\nValuable content"
        test_file = self.create_test_file("backup_test.txt", original)

        # Create manual backup first
        backup_info = create_backup(test_file)
        assert Path(backup_info.path).exists()

        # Make edit that creates another backup
        result = atomic_edit_file(
            test_file, "Important data", "Modified data", preview=False
        )

        assert result.success is True
        assert result.backup_created is not None

        # Verify we can restore from backup
        restored_content = Path(backup_info.path).read_text()
        assert restored_content == original

        # Write backup content back to test restoration
        Path(test_file).write_text(restored_content)
        final_content = Path(test_file).read_text()
        assert final_content == original

    def test_edit_failure_cleanup(self):
        """Test cleanup when edits fail."""
        original = "Some content"
        test_file = self.create_test_file("fail_test.txt", original)

        # Try to edit with non-existent search text
        result = atomic_edit_file(
            test_file, "non_existent_text", "replacement", preview=False
        )

        # Edit should fail gracefully
        assert result.success is False
        assert result.changes_made == 0

        # Original file should be unchanged
        content = Path(test_file).read_text()
        assert content == original

    def test_concurrent_edit_safety(self):
        """Test edit safety with file locking."""
        original = "Concurrent test content"
        test_file = self.create_test_file("concurrent_test.txt", original)

        # First edit
        result1 = atomic_edit_file(test_file, "Concurrent", "Parallel", preview=False)

        assert result1.success is True

        # Second edit on modified file
        result2 = atomic_edit_file(test_file, "test", "safety", preview=False)

        assert result2.success is True

        # Final content should have both changes
        final_content = Path(test_file).read_text()
        assert "Parallel" in final_content
        assert "safety" in final_content
        assert "Concurrent" not in final_content
        assert "test" not in final_content

    def test_large_file_editing(self):
        """Test editing operations on larger files."""
        # Create a larger test file
        lines = [f"Line {i}: Some content here" for i in range(1000)]
        original = "\n".join(lines)
        test_file = self.create_test_file("large_edit.txt", original)

        # Edit a line in the middle
        result = atomic_edit_file(
            test_file,
            "Line 500: Some content here",
            "Line 500: Modified content here",
            preview=False,
        )

        assert result.success is True
        assert result.changes_made == 1

        # Verify only the target line changed
        modified = Path(test_file).read_text()
        assert "Line 500: Modified content here" in modified
        assert "Line 499: Some content here" in modified  # Before unchanged
        assert "Line 501: Some content here" in modified  # After unchanged

    def test_empty_file_editing(self):
        """Test editing operations on empty files."""
        test_file = self.create_test_file("empty.txt", "")

        # Try to edit empty file
        result = atomic_edit_file(test_file, "nothing", "something", preview=False)

        # Should fail gracefully
        assert result.success is False
        assert result.changes_made == 0

        # File should remain empty
        content = Path(test_file).read_text()
        assert content == ""
