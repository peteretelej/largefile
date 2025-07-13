"""Utility functions for file processing and display formatting."""

from .config import config


def truncate_line(line: str, max_length: int | None = None) -> tuple[str, bool]:
    """Truncate a line if it exceeds the maximum length.

    Args:
        line: The line to potentially truncate
        max_length: Maximum length (defaults to config.truncate_length)

    Returns:
        Tuple of (truncated_line, was_truncated)
    """
    if max_length is None:
        max_length = config.truncate_length

    if len(line) <= max_length:
        return line, False

    return line[:max_length] + "...", True


def is_long_line(line: str, threshold: int | None = None) -> bool:
    """Check if a line exceeds the long line threshold.

    Args:
        line: The line to check
        threshold: Length threshold (defaults to config.max_line_length)

    Returns:
        True if line exceeds threshold
    """
    if threshold is None:
        threshold = config.max_line_length

    return len(line) > threshold


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB", "342 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def detect_file_strategy(file_size: int) -> str:
    """Detect the best file access strategy based on size.

    This is a convenience function that matches the logic in file_access.py

    Args:
        file_size: File size in bytes

    Returns:
        Strategy name: "memory", "mmap", or "streaming"
    """
    if file_size < config.memory_threshold:
        return "memory"
    elif file_size < config.mmap_threshold:
        return "mmap"
    else:
        return "streaming"


def split_long_lines(content: str, max_length: int | None = None) -> str:
    """Split long lines in content for better display.

    Args:
        content: Text content to process
        max_length: Maximum line length (defaults to config.max_line_length)

    Returns:
        Content with long lines split
    """
    if max_length is None:
        max_length = config.max_line_length

    lines = content.splitlines()
    result_lines = []

    for line in lines:
        if len(line) <= max_length:
            result_lines.append(line)
        else:
            # Split long line into chunks
            for i in range(0, len(line), max_length):
                chunk = line[i : i + max_length]
                if i + max_length < len(line):
                    chunk += " \\"  # Continuation indicator
                result_lines.append(chunk)

    return "\n".join(result_lines)


def count_file_stats(content: str) -> dict[str, int]:
    """Count basic statistics about file content.

    Args:
        content: File content to analyze

    Returns:
        Dictionary with line_count, char_count, long_lines_count
    """
    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)
    long_lines_count = sum(1 for line in lines if is_long_line(line))

    return {
        "line_count": line_count,
        "char_count": char_count,
        "long_lines_count": long_lines_count,
    }
