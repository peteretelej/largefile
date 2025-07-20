import mmap
import os
from pathlib import Path

import chardet

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


def detect_file_encoding(file_path: str) -> str:
    """Detect file encoding using chardet with utf-8 fallback."""
    try:
        with open(file_path, "rb") as f:
            sample = f.read(65536)  # 64KB sample

        if not sample:
            return "utf-8"

        result = chardet.detect(sample)

        # If chardet detects ASCII, try UTF-8 first since ASCII is subset of UTF-8
        # and UTF-8 is more robust for files that might have non-ASCII later
        encoding = result.get("encoding") if result else None
        if encoding and encoding.lower() == "ascii":
            return "utf-8"

        # Use detection only if confidence is reasonable (>= 0.7)
        if result and result.get("confidence", 0) >= 0.7:
            return result["encoding"] or "utf-8"
        else:
            return "utf-8"

    except Exception:
        return "utf-8"


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


def read_file_content(file_path: str) -> str:
    """Read file content using auto-detected encoding and optimal strategy."""
    canonical_path = normalize_path(file_path)
    file_info = get_file_info(canonical_path)
    strategy = file_info["strategy"]
    encoding = detect_file_encoding(canonical_path)

    if strategy == "memory":
        return _read_file_memory(canonical_path, encoding)
    elif strategy == "mmap":
        return _read_file_mmap(canonical_path, encoding)
    else:  # streaming
        return _read_file_streaming(canonical_path, encoding)


def _read_file_memory(file_path: str, encoding: str = "utf-8") -> str:
    """Read file content into memory (for small files)."""
    try:
        with open(file_path, encoding=encoding) as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def _read_file_mmap(file_path: str, encoding: str = "utf-8") -> str:
    """Read file content using memory mapping (for medium files)."""
    try:
        with open(file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                return mm.read().decode(encoding)
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e
    except OSError:
        # Fall back to regular reading if mmap fails
        return _read_file_memory(file_path, encoding)


def _read_file_streaming(file_path: str, encoding: str = "utf-8") -> str:
    """Read file content in chunks (for very large files)."""
    try:
        chunks = []
        with open(file_path, encoding=encoding) as f:
            while True:
                chunk = f.read(config.streaming_chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
        return "".join(chunks)
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def read_file_lines(file_path: str) -> list[str]:
    """Read file content as list of lines using auto-detected encoding and optimal strategy."""
    canonical_path = normalize_path(file_path)
    file_info = get_file_info(canonical_path)
    strategy = file_info["strategy"]
    encoding = detect_file_encoding(canonical_path)

    if strategy == "memory":
        return _read_file_lines_memory(canonical_path, encoding)
    elif strategy == "mmap":
        return _read_file_lines_mmap(canonical_path, encoding)
    else:  # streaming
        return _read_file_lines_streaming(canonical_path, encoding)


def _read_file_lines_memory(file_path: str, encoding: str = "utf-8") -> list[str]:
    """Read file lines into memory (for small files)."""
    try:
        with open(file_path, encoding=encoding) as f:
            return f.readlines()
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def _read_file_lines_mmap(file_path: str, encoding: str = "utf-8") -> list[str]:
    """Read file lines using memory mapping (for medium files)."""
    try:
        with open(file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                content = mm.read().decode(encoding)
                return content.splitlines(keepends=True)
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e
    except OSError:
        # Fall back to regular reading if mmap fails
        return _read_file_lines_memory(file_path, encoding)


def _read_file_lines_streaming(file_path: str, encoding: str = "utf-8") -> list[str]:
    """Read file lines in chunks (for very large files)."""
    try:
        lines = []
        buffer = ""

        with open(file_path, encoding=encoding) as f:
            while True:
                chunk = f.read(config.streaming_chunk_size)
                if not chunk:
                    # Handle remaining buffer
                    if buffer:
                        lines.append(buffer)
                    break

                buffer += chunk
                # Split on newlines but keep the last incomplete line
                chunk_lines = buffer.split("\n")
                buffer = chunk_lines[-1]  # Keep incomplete line

                # Add complete lines (with newlines restored)
                for line in chunk_lines[:-1]:
                    lines.append(line + "\n")

        return lines
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        raise FileAccessError(f"Cannot read file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileAccessError(
            f"Cannot decode file {file_path} with encoding {encoding}: {e}"
        ) from e


def write_file_content(file_path: str, content: str) -> None:
    """Write content to file atomically using temp file + rename with auto-detected encoding."""
    canonical_path = normalize_path(file_path)
    temp_path = f"{canonical_path}.tmp"

    # Detect encoding from existing file, or default to utf-8 for new files
    if os.path.exists(canonical_path):
        encoding = detect_file_encoding(canonical_path)
    else:
        encoding = "utf-8"

    try:
        # Clean up any existing temp file first
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)

        # Windows requires removing the target file before rename
        if os.name == "nt" and os.path.exists(canonical_path):
            os.unlink(canonical_path)

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
