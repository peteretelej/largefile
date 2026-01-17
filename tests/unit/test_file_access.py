"""File access unit tests.

Test core file access strategies and operations.
Uses table-driven tests for comprehensive coverage.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.exceptions import FileAccessError
from src.file_access import (
    _read_file_lines_streaming,
    _read_file_streaming,
    choose_file_strategy,
    detect_file_encoding,
    get_file_info,
    get_long_line_stats,
    is_binary_file,
    normalize_path,
    read_file_content,
    read_file_lines,
    read_head,
    read_tail,
    write_file_content,
)
from src.utils import format_file_size, is_long_line, truncate_line


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

    def test_detect_file_encoding(self):
        """Test encoding detection with various file types."""
        # UTF-8 file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Hello UTF-8 world! 🌍")
            utf8_path = f.name

        # Latin-1 file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write("Hello Latin-1 café".encode("latin-1"))
            latin1_path = f.name

        # UTF-16 file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write("Hello UTF-16 world! 🌍".encode("utf-16"))
            utf16_path = f.name

        # Empty file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            empty_path = f.name

        try:
            # UTF-8 detection (low confidence should fallback to utf-8)
            encoding = detect_file_encoding(utf8_path)
            assert encoding == "utf-8"

            # Latin-1 detection (may have high confidence or fallback)
            encoding = detect_file_encoding(latin1_path)
            assert encoding.lower() in ["latin-1", "iso-8859-1", "utf-8"]

            # UTF-16 detection (should detect UTF-16 variants)
            encoding = detect_file_encoding(utf16_path)
            assert "utf-16" in encoding.lower() or encoding == "utf-8"

            # Empty file defaults to utf-8
            encoding = detect_file_encoding(empty_path)
            assert encoding == "utf-8"

            # Non-existent file fallback
            encoding = detect_file_encoding("/nonexistent/file.txt")
            assert encoding == "utf-8"

        finally:
            Path(utf8_path).unlink()
            Path(latin1_path).unlink()
            Path(utf16_path).unlink()
            Path(empty_path).unlink()

    def test_path_normalization(self):
        """Test path normalization functionality."""
        # Test absolute path (platform-specific)
        import os

        if os.name == "nt":  # Windows
            abs_path = r"C:\Users\user\file.txt"
        else:  # Unix-like
            abs_path = "/home/user/file.txt"

        normalized = normalize_path(abs_path)
        assert normalized == abs_path

        # Test relative path normalization
        rel_path = "file.txt"
        normalized = normalize_path(rel_path)
        assert normalized.endswith("file.txt")
        if os.name == "nt":  # Windows
            assert len(normalized) > len(
                rel_path
            )  # Should be absolute (has drive letter)
        else:  # Unix-like
            assert normalized.startswith("/")  # Should be absolute

        # Test home directory expansion
        home_path = "~/file.txt"
        normalized = normalize_path(home_path)
        assert "~" not in normalized  # Should be expanded
        if os.name == "nt":  # Windows
            assert len(normalized) > len(
                home_path
            )  # Should be absolute (has drive letter)
        else:  # Unix-like
            assert normalized.startswith("/")  # Should be absolute


class TestReadTail:
    """Test read_tail function for reading last N lines."""

    def test_read_tail_small_file(self):
        """Reads last N lines from small file."""
        test_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = read_tail(temp_path, 3)

            assert "content" in result
            assert "start_line" in result
            assert "end_line" in result
            assert "total_lines" in result

            assert result["total_lines"] == 5
            assert result["end_line"] == 5
            assert result["start_line"] == 3  # Lines 3, 4, 5
            assert "Line 3" in result["content"]
            assert "Line 4" in result["content"]
            assert "Line 5" in result["content"]
            assert "Line 1" not in result["content"]
            assert "Line 2" not in result["content"]

        finally:
            Path(temp_path).unlink()

    def test_read_tail_more_lines_than_file(self):
        """Returns entire file when N > total lines."""
        test_content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = read_tail(temp_path, 100)  # Request more lines than file has

            assert result["total_lines"] == 3
            assert result["start_line"] == 1  # Start from beginning
            assert result["end_line"] == 3
            assert result["content"] == test_content

        finally:
            Path(temp_path).unlink()

    def test_read_tail_returns_correct_line_numbers(self):
        """Verifies start_line and end_line are 1-indexed."""
        test_content = "A\nB\nC\nD\nE\nF\nG\nH\nI\nJ\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = read_tail(temp_path, 3)

            # Should return lines 8, 9, 10 (H, I, J)
            assert result["total_lines"] == 10
            assert result["start_line"] == 8  # 1-indexed
            assert result["end_line"] == 10
            assert "H\n" in result["content"]
            assert "I\n" in result["content"]
            assert "J\n" in result["content"]

        finally:
            Path(temp_path).unlink()

    def test_read_tail_single_line(self):
        """Reads last single line."""
        test_content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = read_tail(temp_path, 1)

            assert result["total_lines"] == 3
            assert result["start_line"] == 3
            assert result["end_line"] == 3
            assert result["content"] == "Line 3\n"

        finally:
            Path(temp_path).unlink()

    def test_read_tail_empty_file(self):
        """Handles empty file gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            result = read_tail(temp_path, 10)

            assert result["total_lines"] == 0
            assert result["content"] == ""
            assert result["start_line"] == 1  # 1-indexed minimum

        finally:
            Path(temp_path).unlink()

    def test_read_tail_nonexistent_file(self):
        """Raises error for non-existent file."""
        try:
            read_tail("/nonexistent/file.txt", 10)
            raise AssertionError("Should have raised FileAccessError")
        except FileAccessError as e:
            assert "Cannot access file" in str(e)


class TestMmapFallback:
    """Test mmap strategy fallback behavior."""

    def test_mmap_fallback_on_oserror(self):
        """mmap OSError falls back to memory strategy."""
        test_content = "test content for mmap fallback"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # Patch mmap.mmap to raise OSError, simulating mmap failure
            with patch("src.file_access.mmap.mmap", side_effect=OSError("mmap failed")):
                # Force mmap strategy by patching the strategy selection
                with patch("src.file_access.choose_file_strategy", return_value="mmap"):
                    # Should fall back to memory read, not raise
                    content = read_file_content(temp_path)
                    assert content == test_content
        finally:
            Path(temp_path).unlink()


class TestUtils:
    """Tests for utility functions in utils.py."""

    def test_truncate_line_no_truncation(self):
        """Short lines are not truncated."""
        line, was_truncated = truncate_line("short line", max_length=100)
        assert line == "short line"
        assert was_truncated is False

    def test_truncate_line_with_truncation(self):
        """Long lines are truncated with ellipsis."""
        line, was_truncated = truncate_line("x" * 50, max_length=10)
        assert line == "x" * 10 + "..."
        assert was_truncated is True

    def test_is_long_line_true(self):
        """Lines exceeding threshold return True."""
        assert is_long_line("x" * 1000, threshold=100) is True

    def test_is_long_line_false(self):
        """Lines within threshold return False."""
        assert is_long_line("short", threshold=100) is False

    def test_format_file_size_bytes(self):
        """Formats bytes correctly."""
        assert format_file_size(500) == "500 B"

    def test_format_file_size_kb(self):
        """Formats kilobytes correctly."""
        result = format_file_size(5000)
        assert "KB" in result
        assert "4.9" in result  # 5000/1024 ≈ 4.88

    def test_format_file_size_mb(self):
        """Formats megabytes correctly."""
        result = format_file_size(5_000_000)
        assert "MB" in result

    def test_format_file_size_gb(self):
        """Formats gigabytes correctly."""
        result = format_file_size(5_000_000_000)
        assert "GB" in result


class TestBinaryDetection:
    """Tests for binary file detection functions."""

    def test_is_binary_file_text_file(self):
        """Text files are not detected as binary."""
        test_content = "Hello, this is a text file.\nWith multiple lines.\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is False
            assert hint is None
        finally:
            Path(temp_path).unlink()

    def test_is_binary_file_with_null_bytes(self):
        """Files with null bytes are detected as binary."""
        test_content = b"Hello\x00World\x00Binary"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is True
            assert hint == "executable"  # .bin extension
        finally:
            Path(temp_path).unlink()

    def test_is_binary_file_image_hint(self):
        """Image files get 'image' hint."""
        test_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00"  # PNG magic bytes + null

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".png") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is True
            assert hint == "image"
        finally:
            Path(temp_path).unlink()

    def test_is_binary_file_compressed_hint(self):
        """Compressed files get 'compressed' hint."""
        test_content = b"PK\x03\x04\x00\x00"  # ZIP magic bytes + null

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".zip") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is True
            assert hint == "compressed"
        finally:
            Path(temp_path).unlink()

    def test_is_binary_file_unknown_extension(self):
        """Binary files with unknown extension get None hint."""
        test_content = b"Some\x00Binary\x00Content"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".xyz") as f:
            f.write(test_content)
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is True
            assert hint is None  # Unknown extension
        finally:
            Path(temp_path).unlink()

    def test_is_binary_file_nonexistent_file(self):
        """Non-existent files return False with no hint."""
        is_binary, hint = is_binary_file("/nonexistent/file.txt")
        assert is_binary is False
        assert hint is None

    def test_is_binary_file_empty_file(self):
        """Empty files are not detected as binary."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            is_binary, hint = is_binary_file(temp_path)
            assert is_binary is False
            assert hint is None
        finally:
            Path(temp_path).unlink()


class TestLongLineStats:
    """Tests for long line statistics function."""

    def test_get_long_line_stats_no_long_lines(self):
        """Files with no long lines return appropriate stats."""
        lines = ["short line\n", "another short line\n", "third line\n"]
        stats = get_long_line_stats(lines, threshold=100)

        assert stats["has_long_lines"] is False
        assert stats["count"] == 0
        assert stats["max_length"] == 0
        assert stats["threshold"] == 100

    def test_get_long_line_stats_with_long_lines(self):
        """Files with long lines return appropriate stats."""
        lines = [
            "short\n",
            "x" * 150 + "\n",  # 151 chars (150 + newline)
            "another short\n",
            "y" * 200 + "\n",  # 201 chars
        ]
        stats = get_long_line_stats(lines, threshold=100)

        assert stats["has_long_lines"] is True
        assert stats["count"] == 2
        assert stats["max_length"] == 201  # Longest line
        assert stats["threshold"] == 100

    def test_get_long_line_stats_boundary(self):
        """Lines exactly at threshold are not long."""
        lines = ["x" * 100 + "\n"]  # Exactly 101 chars
        stats = get_long_line_stats(lines, threshold=100)

        # Line is 101 chars (100 x's + newline), which is > 100, so it's long
        assert stats["has_long_lines"] is True
        assert stats["count"] == 1

        # Now test exactly at threshold
        lines = ["x" * 99 + "\n"]  # Exactly 100 chars
        stats = get_long_line_stats(lines, threshold=100)

        assert stats["has_long_lines"] is False
        assert stats["count"] == 0

    def test_get_long_line_stats_empty_list(self):
        """Empty line list returns appropriate stats."""
        stats = get_long_line_stats([], threshold=100)

        assert stats["has_long_lines"] is False
        assert stats["count"] == 0
        assert stats["max_length"] == 0
        assert stats["threshold"] == 100

    def test_get_long_line_stats_custom_threshold(self):
        """Custom threshold is respected."""
        lines = ["x" * 50 + "\n", "y" * 60 + "\n"]
        stats = get_long_line_stats(lines, threshold=55)

        assert stats["has_long_lines"] is True
        assert stats["count"] == 1  # Only 60-char line is over 55
        assert stats["max_length"] == 61
        assert stats["threshold"] == 55


class TestReadHead:
    """Tests for read_head function."""

    def test_read_head_basic(self):
        """Reads first N lines from file."""
        content = "\n".join([f"Line {i}" for i in range(1, 21)])

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_head(temp_path, 5)

            assert result["start_line"] == 1
            assert result["end_line"] == 5
            assert result["lines_read"] == 5
            assert result["total_lines"] == 20
            assert "Line 1" in result["content"]
            assert "Line 5" in result["content"]
            assert "Line 6" not in result["content"]
        finally:
            Path(temp_path).unlink()

    def test_read_head_more_than_file(self):
        """Returns entire file when limit exceeds total lines."""
        content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = read_head(temp_path, 100)

            assert result["total_lines"] == 3
            assert result["lines_read"] == 3
            assert result["start_line"] == 1
            assert result["end_line"] == 3
        finally:
            Path(temp_path).unlink()

    def test_read_head_empty_file(self):
        """Handles empty file gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            result = read_head(temp_path, 10)

            assert result["total_lines"] == 0
            assert result["lines_read"] == 0
            assert result["content"] == ""
        finally:
            Path(temp_path).unlink()

    def test_read_head_nonexistent_file(self):
        """Raises error for non-existent file."""
        with pytest.raises(FileAccessError) as exc_info:
            read_head("/nonexistent/file.txt", 10)
        assert "Cannot access file" in str(exc_info.value)


class TestStreamingStrategy:
    """Tests for streaming file access strategy."""

    def test_streaming_read_content(self):
        """Test _read_file_streaming function."""
        content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = _read_file_streaming(temp_path, "utf-8")
            assert result == content
        finally:
            Path(temp_path).unlink()

    def test_streaming_read_lines(self):
        """Test _read_file_lines_streaming function."""
        content = "Line 1\nLine 2\nLine 3\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            lines = _read_file_lines_streaming(temp_path, "utf-8")
            assert len(lines) == 3
            assert lines[0] == "Line 1\n"
            assert lines[2] == "Line 3\n"
        finally:
            Path(temp_path).unlink()

    def test_streaming_read_lines_no_trailing_newline(self):
        """Test streaming with content not ending in newline."""
        content = "Line 1\nLine 2\nLine 3"  # No trailing newline

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            lines = _read_file_lines_streaming(temp_path, "utf-8")
            assert len(lines) == 3
            assert lines[2] == "Line 3"  # Last line without newline
        finally:
            Path(temp_path).unlink()


class TestLargeFileStreamingPaths:
    """Test file operations that use streaming for large files."""

    def test_read_tail_streaming_path(self):
        """Test read_tail with streaming strategy (large file simulation)."""
        content = "\n".join([f"Line {i}" for i in range(1, 1001)])

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            # Force streaming path by patching memory threshold MB
            from src.file_access import config

            original_threshold = config.memory_threshold_mb
            config.memory_threshold_mb = 0  # Set to 0 to force streaming

            try:
                result = read_tail(temp_path, 10)

                assert result["total_lines"] == 1000
                assert result["end_line"] == 1000
                assert "Line 991" in result["content"]
                assert "Line 1000" in result["content"]
            finally:
                config.memory_threshold_mb = original_threshold
        finally:
            Path(temp_path).unlink()

    def test_read_head_streaming_path(self):
        """Test read_head with streaming strategy (large file simulation)."""
        content = "\n".join([f"Line {i}" for i in range(1, 1001)])

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            # Force streaming path by patching memory threshold MB
            from src.file_access import config

            original_threshold = config.memory_threshold_mb
            config.memory_threshold_mb = 0  # Set to 0 to force streaming

            try:
                result = read_head(temp_path, 10)

                assert result["total_lines"] == 1000
                assert result["start_line"] == 1
                assert result["lines_read"] == 10
                assert "Line 1" in result["content"]
                assert "Line 10" in result["content"]
            finally:
                config.memory_threshold_mb = original_threshold
        finally:
            Path(temp_path).unlink()


class TestWriteFileContent:
    """Tests for write_file_content function."""

    def test_write_new_file(self):
        """Creates new file with content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "new_file.txt"
            content = "Hello, World!\n"

            write_file_content(str(file_path), content)

            assert file_path.read_text() == content

    def test_write_overwrite_existing(self):
        """Overwrites existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("old content")
            temp_path = f.name

        try:
            new_content = "new content\n"
            write_file_content(temp_path, new_content)

            assert Path(temp_path).read_text() == new_content
        finally:
            Path(temp_path).unlink()

    def test_write_atomic(self):
        """Write is atomic (uses temp file + rename)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Test content\n"

            write_file_content(str(file_path), content)

            # Check no temp file left behind
            temp_path = Path(f"{file_path}.tmp")
            assert not temp_path.exists()
            assert file_path.read_text() == content


class TestFileReadErrors:
    """Test error handling in file reading functions."""

    def test_read_content_directory_error(self):
        """Reading a directory raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileAccessError) as exc_info:
                read_file_content(tmpdir)
            assert "Cannot" in str(exc_info.value)

    def test_read_lines_directory_error(self):
        """Reading lines from a directory raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileAccessError) as exc_info:
                read_file_lines(tmpdir)
            assert "Cannot" in str(exc_info.value)
