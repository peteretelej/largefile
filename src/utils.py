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
