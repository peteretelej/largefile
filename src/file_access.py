import os
from pathlib import Path

from .config import config
from .exceptions import FileAccessError


def normalize_path(file_path: str) -> str:
    """Convert to absolute canonical path with home directory expansion."""
    expanded = os.path.expanduser(file_path)
    return os.path.abspath(expanded)


def choose_file_strategy(file_size: int) -> str:
    """Determine the best file access strategy based on size."""
    if file_size < config.memory_threshold:
        return "memory"
    elif file_size < config.mmap_threshold:
        return "mmap"
    else:
        return "streaming"


def get_file_info(file_path: str) -> dict:
    """Get basic file information."""
    try:
        canonical_path = normalize_path(file_path)
        stat = os.stat(canonical_path)

        return {
            "canonical_path": canonical_path,
            "size": stat.st_size,
            "exists": True,
            "strategy": choose_file_strategy(stat.st_size),
        }
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise FileAccessError(f"Cannot access file {file_path}: {e}") from e


def read_file_content(file_path: str, encoding: str = "utf-8") -> str:
    """Read file content with specified encoding."""
    try:
        canonical_path = normalize_path(file_path)

        with open(canonical_path, encoding=encoding) as f:
            return f.read()
    except (FileNotFoundError, PermissionError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def read_file_lines(file_path: str, encoding: str = "utf-8") -> list[str]:
    """Read file content as list of lines."""
    try:
        canonical_path = normalize_path(file_path)

        with open(canonical_path, encoding=encoding) as f:
            return f.readlines()
    except (FileNotFoundError, PermissionError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def write_file_content(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """Write content to file atomically using temp file + rename."""
    canonical_path = normalize_path(file_path)
    temp_path = f"{canonical_path}.tmp"

    try:
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)
        os.rename(temp_path, canonical_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise FileAccessError(f"Failed to write {file_path}: {e}") from e


def create_backup(file_path: str) -> str:
    """Create backup of file and return backup path."""
    canonical_path = normalize_path(file_path)

    os.makedirs(config.backup_dir, exist_ok=True)

    file_name = Path(canonical_path).name
    backup_path = os.path.join(config.backup_dir, f"{file_name}.backup")

    try:
        content = read_file_content(canonical_path)
        write_file_content(backup_path, content)
        return backup_path
    except Exception as e:
        raise FileAccessError(f"Failed to create backup: {e}") from e
