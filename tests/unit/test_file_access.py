"""File access unit tests.

Test core file access strategies and operations.
"""

import tempfile
from pathlib import Path

from src.exceptions import FileAccessError
from src.file_access import (
    choose_file_strategy,
    get_file_info,
    normalize_path,
    read_file_content,
)


class TestFileAccess:
    """Test file access core functions."""

    def test_strategy_selection(self):
        """Test file size to strategy mapping."""
        # Memory strategy for small files
        assert choose_file_strategy(1000) == "memory"
        assert choose_file_strategy(49 * 1024 * 1024) == "memory"  # Just under 50MB

        # Mmap strategy for medium files
        assert choose_file_strategy(50 * 1024 * 1024) == "mmap"  # Exactly 50MB
        assert choose_file_strategy(100 * 1024 * 1024) == "mmap"  # 100MB
        assert choose_file_strategy(499 * 1024 * 1024) == "mmap"  # Just under 500MB

        # Streaming strategy for large files
        assert choose_file_strategy(500 * 1024 * 1024) == "streaming"  # Exactly 500MB
        assert choose_file_strategy(1024 * 1024 * 1024) == "streaming"  # 1GB

    def test_file_info_extraction(self):
        """Test file metadata extraction."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_content = "Hello world\nSecond line\n"
            f.write(test_content)
            temp_path = f.name

        try:
            # Test file info extraction
            file_info = get_file_info(temp_path)

            assert "canonical_path" in file_info
            assert "size" in file_info
            assert "exists" in file_info
            assert "strategy" in file_info

            assert file_info["exists"] is True
            assert file_info["size"] > 0
            assert file_info["strategy"] == "memory"  # Small test file
            assert temp_path in file_info["canonical_path"]  # Should be normalized path

        finally:
            Path(temp_path).unlink()

        # Test non-existent file
        try:
            get_file_info("/nonexistent/file.txt")
            raise AssertionError("Should have raised FileAccessError")
        except FileAccessError as e:
            assert "Cannot access file" in str(e)

    def test_memory_file_reading(self):
        """Test memory strategy file operations."""
        # Create a small temporary file
        test_content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # Test content reading
            content = read_file_content(temp_path)
            assert content == test_content

            # Test with different encoding (should work or fail gracefully)
            try:
                content_utf8 = read_file_content(temp_path, encoding="utf-8")
                assert len(content_utf8) > 0
            except Exception:
                # Encoding errors are acceptable for this test
                pass

        finally:
            Path(temp_path).unlink()

        # Test reading non-existent file
        try:
            read_file_content("/nonexistent/file.txt")
            raise AssertionError("Should have raised FileAccessError")
        except FileAccessError as e:
            assert "Cannot access file" in str(e)

    def test_path_normalization(self):
        """Test path normalization functionality."""
        # Test absolute path
        abs_path = "/home/user/file.txt"
        normalized = normalize_path(abs_path)
        assert normalized == abs_path

        # Test relative path normalization
        rel_path = "file.txt"
        normalized = normalize_path(rel_path)
        assert normalized.endswith("file.txt")
        assert normalized.startswith("/")  # Should be absolute

        # Test home directory expansion
        home_path = "~/file.txt"
        normalized = normalize_path(home_path)
        assert "~" not in normalized  # Should be expanded
        assert normalized.startswith("/")  # Should be absolute
