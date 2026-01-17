import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import config
from .data_models import (
    BackupInfo,
    Change,
    ChangeResult,
    FileOverview,
    LongLineStats,
    SearchResult,
)
from .editor import batch_edit_content
from .exceptions import EditError, FileAccessError, SearchError, TreeSitterError
from .file_access import (
    create_backup,
    detect_file_encoding,
    get_file_info,
    get_long_line_stats,
    is_binary_file,
    list_backups,
    normalize_path,
    read_file_content,
    read_file_lines,
    read_head,
    read_tail,
)
from .search_engine import search_file
from .tree_parser import (
    extract_semantic_context,
    generate_outline,
    get_semantic_chunk,
    parse_file_content,
)
from .utils import truncate_line


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to handle tool errors consistently."""

    def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            return func(*args, **kwargs)  # type: ignore
        except FileAccessError as e:
            return {
                "error": f"File access failed: {e}",
                "suggestion": "Check file path and permissions",
            }
        except TreeSitterError as e:
            return {
                "error": f"Semantic parsing failed: {e}",
                "suggestion": "File will use text-based analysis",
            }
        except SearchError as e:
            return {
                "error": f"Search failed: {e}",
                "suggestion": "Try different search terms or disable fuzzy matching",
            }
        except EditError as e:
            return {
                "error": f"Edit failed: {e}",
                "suggestion": "Check search text matches exactly or enable fuzzy matching",
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {e}",
                "suggestion": "Report this issue with file details",
            }

    return wrapper


@handle_tool_errors
def get_overview(absolute_file_path: str) -> dict:
    """Get file structure with basic analysis using auto-detected encoding.

    Provides file metadata, line count, and basic structure analysis.
    Detects binary files and long lines, returns search hints for efficient
    exploration.

    CRITICAL: You must use an absolute file path - relative paths will fail.
    DO NOT attempt to read large files directly as they exceed context limits.

    Parameters:
    - absolute_file_path: Absolute path to the file

    Returns:
    - FileOverview with line count, file size, detected encoding, binary detection,
      long line statistics, and search hints
    """
    canonical_path = normalize_path(absolute_file_path)
    file_info = get_file_info(canonical_path)

    # Check for binary file first
    is_binary, binary_hint = is_binary_file(canonical_path)

    if is_binary:
        # Return early for binary files
        long_lines_stats = LongLineStats(
            has_long_lines=False,
            count=0,
            max_length=0,
            threshold=config.max_line_length,
        )
        overview = FileOverview(
            line_count=0,
            file_size=file_info["size"],
            encoding=None,
            long_lines=long_lines_stats,
            is_binary=True,
            binary_hint=binary_hint,
            outline=[],
            search_hints=[],
        )
        return {
            "line_count": overview.line_count,
            "file_size": overview.file_size,
            "encoding": overview.encoding,
            "is_binary": overview.is_binary,
            "binary_hint": overview.binary_hint,
            "long_lines": {
                "has_long_lines": overview.long_lines.has_long_lines,
                "count": overview.long_lines.count,
                "max_length": overview.long_lines.max_length,
                "threshold": overview.long_lines.threshold,
            },
            "outline": [],
            "search_hints": [],
            "warning": "Binary file detected. Text operations may not work correctly.",
        }

    lines = read_file_lines(canonical_path)
    content = read_file_content(canonical_path)
    detected_encoding = detect_file_encoding(canonical_path)

    # Get long line stats
    long_line_stats_dict = get_long_line_stats(lines, config.max_line_length)
    long_lines_stats = LongLineStats(
        has_long_lines=long_line_stats_dict["has_long_lines"],
        count=long_line_stats_dict["count"],
        max_length=long_line_stats_dict["max_length"],
        threshold=long_line_stats_dict["threshold"],
    )

    # Use tree-sitter for outline generation if available
    try:
        outline = generate_outline(canonical_path, content)
    except Exception:
        # Fall back to simple outline
        outline = []

    # Generate search hints based on file type
    file_ext = Path(canonical_path).suffix.lower()
    if file_ext == ".py":
        search_hints = ["def ", "class ", "import ", "from "]
    elif file_ext in [".js", ".ts", ".jsx", ".tsx"]:
        search_hints = ["function ", "class ", "const ", "import "]
    elif file_ext == ".go":
        search_hints = ["func ", "type ", "import ", "package "]
    elif file_ext == ".rs":
        search_hints = ["fn ", "struct ", "impl ", "use "]
    else:
        search_hints = ["TODO", "FIXME", "NOTE", "HACK"]

    overview = FileOverview(
        line_count=len(lines),
        file_size=file_info["size"],
        encoding=detected_encoding,
        long_lines=long_lines_stats,
        is_binary=False,
        binary_hint=None,
        outline=outline,
        search_hints=search_hints,
    )

    return {
        "line_count": overview.line_count,
        "file_size": overview.file_size,
        "encoding": overview.encoding,
        "is_binary": overview.is_binary,
        "binary_hint": overview.binary_hint,
        "long_lines": {
            "has_long_lines": overview.long_lines.has_long_lines,
            "count": overview.long_lines.count,
            "max_length": overview.long_lines.max_length,
            "threshold": overview.long_lines.threshold,
        },
        "outline": [
            {
                "name": item.name,
                "type": item.type,
                "line_number": item.line_number,
                "end_line": item.end_line,
                "line_count": item.line_count,
            }
            for item in overview.outline
        ],
        "search_hints": overview.search_hints,
    }


@handle_tool_errors
def search_content(
    absolute_file_path: str,
    pattern: str,
    max_results: int = 20,
    context_lines: int = 3,
    fuzzy: bool = True,
    regex: bool = False,
    case_sensitive: bool = True,
    invert: bool = False,
    count_only: bool = False,
) -> dict:
    """Find patterns with fuzzy matching and context using auto-detected encoding.

    Uses fuzzy matching via Levenshtein distance to handle real-world
    formatting variations. Returns context lines around matches for better
    understanding.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - pattern: Search pattern (exact, fuzzy, or regex matching)
    - max_results: Maximum number of results to return
    - context_lines: Number of context lines before/after match
    - fuzzy: Enable fuzzy matching (default True)
    - regex: Enable Python regex matching (default False)
    - case_sensitive: Case sensitive search (default True, ignored for fuzzy)
    - invert: Return non-matching lines (default False)
    - count_only: Return just match count, not content (default False)

    Returns:
    - List of search results with line numbers, matches, and context
    - Or count object if count_only=True
    """
    canonical_path = normalize_path(absolute_file_path)

    # Build warnings for ignored params in count_only mode
    warnings: list[str] = []
    if count_only:
        if max_results != 20:
            warnings.append("max_results ignored in count_only mode")
        if context_lines != 3:
            warnings.append("context_lines ignored in count_only mode")

    # Perform search (no limit for count_only mode to get accurate count)
    matches = search_file(canonical_path, pattern, fuzzy, regex, case_sensitive, invert)

    # Count-only mode: return early with just the count
    if count_only:
        count_result: dict = {
            "count": len(matches),
            "pattern": pattern,
            "fuzzy_enabled": fuzzy,
            "regex_enabled": regex,
            "case_sensitive": case_sensitive,
            "inverted": invert,
        }
        if warnings:
            count_result["warnings"] = warnings
        return count_result

    lines = read_file_lines(canonical_path)
    content = read_file_content(canonical_path)

    # Try to parse with tree-sitter for semantic context
    tree = None
    try:
        tree = parse_file_content(canonical_path, content)
    except Exception:
        # Tree-sitter not available or failed, use simple context
        pass

    results = []
    for match in matches[:max_results]:
        line_num = match.line_number

        context_before = []
        for i in range(max(1, line_num - context_lines), line_num):
            if i <= len(lines):
                context_before.append(lines[i - 1].rstrip("\n\r"))

        context_after = []
        for i in range(line_num + 1, min(len(lines) + 1, line_num + context_lines + 1)):
            if i <= len(lines):
                context_after.append(lines[i - 1].rstrip("\n\r"))

        match_content, truncated = truncate_line(match.content)

        # Get semantic context using tree-sitter if available
        if tree:
            try:
                semantic_context = extract_semantic_context(tree, line_num)
            except Exception:
                semantic_context = f"Line {line_num}"
        else:
            semantic_context = f"Line {line_num}"

        result = SearchResult(
            line_number=line_num,
            match=match_content,
            context_before=context_before,
            context_after=context_after,
            semantic_context=semantic_context,
            similarity_score=match.similarity_score,
            truncated=truncated,
            submatches=[],
        )

        results.append(
            {
                "line_number": result.line_number,
                "match": result.match,
                "context_before": result.context_before,
                "context_after": result.context_after,
                "semantic_context": result.semantic_context,
                "similarity_score": result.similarity_score,
                "truncated": result.truncated,
                "match_type": match.match_type,
            }
        )

    return {
        "results": results,
        "total_matches": len(matches),
        "pattern": pattern,
        "fuzzy_enabled": fuzzy,
        "regex_enabled": regex,
        "case_sensitive": case_sensitive,
        "inverted": invert,
    }


@handle_tool_errors
def read_content(
    absolute_file_path: str,
    offset: int = 1,
    limit: int = 100,
    pattern: str | None = None,
    mode: str = "lines",
) -> dict:
    """Read content from file with explicit offset/limit control.

    Read content starting from a line number or around a search pattern.
    Returns a reasonable chunk of content for LLM consumption.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - offset: Starting line number, 1-indexed (default: 1)
    - limit: Maximum lines to return (default: 100)
    - pattern: Optional search pattern to locate content
    - mode: "lines", "semantic", "tail", or "head"

    Returns:
    - Content with metadata about the read operation
    """
    canonical_path = normalize_path(absolute_file_path)
    warnings: list[str] = []

    # Validate parameters
    if offset < 1:
        return {"error": "offset must be >= 1", "suggestion": "Use 1 for first line"}
    if limit < 1:
        return {"error": "limit must be >= 1", "suggestion": "Use positive limit"}
    if mode not in ("lines", "semantic", "tail", "head"):
        return {
            "error": f"Invalid mode: {mode}",
            "suggestion": "Use 'lines', 'semantic', 'tail', or 'head'",
        }

    # Check for ignored params
    if mode in ("tail", "head") and offset != 1:
        warnings.append(f"offset ignored in {mode} mode")
    if pattern is not None and offset != 1:
        warnings.append("offset ignored when pattern is set")

    # Handle tail mode - read last N lines efficiently
    if mode == "tail":
        result = read_tail(canonical_path, limit)
        result["mode"] = "tail"
        result["lines_returned"] = result.pop(
            "lines_read", result["end_line"] - result["start_line"] + 1
        )
        if warnings:
            result["warnings"] = warnings
        return result

    # Handle head mode - read first N lines efficiently
    if mode == "head":
        result = read_head(canonical_path, limit)
        result["mode"] = "head"
        result["lines_returned"] = result.pop("lines_read", result["end_line"])
        if warnings:
            result["warnings"] = warnings
        return result

    # Read file for lines/semantic modes
    lines = read_file_lines(canonical_path)
    file_content = read_file_content(canonical_path)
    total_lines = len(lines)

    # Determine starting position
    start_line = offset
    match_info: dict = {}

    if pattern is not None:
        # Search for pattern
        matches = search_file(canonical_path, pattern, fuzzy=True)
        if not matches:
            return {
                "content": "",
                "error": f"Pattern '{pattern}' not found in file",
                "total_lines": total_lines,
                "mode": mode,
            }
        first_match = matches[0]
        start_line = max(1, first_match.line_number - 5)  # Context before match
        match_info = {
            "pattern": pattern,
            "match_line": first_match.line_number,
            "similarity_score": first_match.similarity_score,
        }

    # Handle semantic mode
    if mode == "semantic":
        try:
            chunk_content, sem_start, sem_end = get_semantic_chunk(
                canonical_path, file_content, start_line
            )
            result = {
                "content": chunk_content,
                "start_line": sem_start,
                "end_line": sem_end,
                "lines_returned": sem_end - sem_start + 1,
                "total_lines": total_lines,
                "mode": "semantic",
                **match_info,
            }
            if warnings:
                result["warnings"] = warnings
            return result
        except Exception:
            # Fall back to line-based reading
            pass

    # Line-based reading
    end_line = min(total_lines, start_line + limit - 1)
    content_lines = lines[start_line - 1 : end_line]
    content = "".join(content_lines)

    result = {
        "content": content,
        "start_line": start_line,
        "end_line": end_line,
        "lines_returned": len(content_lines),
        "total_lines": total_lines,
        "mode": mode,
        "truncated": end_line < total_lines,
        **match_info,
    }
    if warnings:
        result["warnings"] = warnings
    return result


def _change_result_to_dict(r: ChangeResult) -> dict:
    """Convert ChangeResult to dictionary."""
    d: dict[str, Any] = {
        "index": r.index,
        "success": r.success,
    }
    if r.line_number is not None:
        d["line_number"] = r.line_number
    if r.match_type is not None:
        d["match_type"] = r.match_type
    if r.similarity is not None:
        d["similarity"] = r.similarity
    if r.error is not None:
        d["error"] = r.error
    if r.similar_matches:
        d["similar_matches"] = [
            {"line": m.line, "content": m.content, "similarity": m.similarity}
            for m in r.similar_matches
        ]
    return d


@handle_tool_errors
def edit_content(
    absolute_file_path: str,
    changes: list[dict[str, Any]],
    fuzzy: bool = True,
    preview: bool = True,
) -> dict:
    """PRIMARY EDITING METHOD using search/replace blocks with auto-detected encoding.

    Fuzzy matching handles whitespace variations. Eliminates line number
    confusion that causes LLM errors. Creates automatic backups before changes.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - changes: Array of {search, replace, fuzzy?} objects (required)
    - fuzzy: Enable fuzzy matching (default True, can be overridden per-change)
    - preview: Show preview without making changes (default True)

    Returns:
    - EditResult with success status, preview, and change details
    """
    # Validate changes array
    if not changes:
        return {
            "error": "Empty changes array",
            "suggestion": "Provide at least one change in the changes array",
        }

    if len(changes) > config.max_batch_changes:
        return {
            "error": f"Too many changes: {len(changes)} exceeds limit of {config.max_batch_changes}",
            "suggestion": f"Split into multiple calls with at most {config.max_batch_changes} changes each",
        }

    # Convert dict changes to Change objects
    change_objects: list[Change] = []
    for i, c in enumerate(changes):
        if "search" not in c:
            return {
                "error": f"Change at index {i} missing required 'search' field",
                "suggestion": "Each change must have 'search' and 'replace' fields",
            }
        if "replace" not in c:
            return {
                "error": f"Change at index {i} missing required 'replace' field",
                "suggestion": "Each change must have 'search' and 'replace' fields",
            }
        change_objects.append(
            Change(
                search=c["search"],
                replace=c["replace"],
                fuzzy=c.get("fuzzy"),
            )
        )

    result = batch_edit_content(absolute_file_path, change_objects, fuzzy, preview)

    response: dict[str, Any] = {
        "success": result.success,
        "changes_applied": result.changes_applied,
        "changes_failed": result.changes_failed,
        "results": [_change_result_to_dict(r) for r in result.results]
        if result.results
        else [],
        "preview": result.preview,
        "backup_created": result.backup_created,
    }
    return response


def _backup_to_dict(backup: BackupInfo) -> dict:
    """Convert BackupInfo to dictionary."""
    return {
        "id": backup.id,
        "timestamp": backup.timestamp,
        "size": backup.size,
        "path": backup.path,
    }


@handle_tool_errors
def revert_edit(
    absolute_file_path: str,
    backup_id: str | None = None,
) -> dict:
    """Revert file to a previous backup state.

    Creates a backup of the current state before reverting to ensure
    no work is lost. Use this to recover from bad edits.

    Parameters:
    - absolute_file_path: Absolute path to the file to revert
    - backup_id: Backup timestamp ID to revert to. If omitted, uses most recent.

    Returns:
    - RevertResult with success status, backup info, and available backups
    """
    file_path = normalize_path(absolute_file_path)

    if not os.path.exists(file_path):
        return {
            "success": False,
            "reverted_to": None,
            "current_saved_as": None,
            "available_backups": [],
            "error": f"File does not exist: {file_path}",
        }

    backups = list_backups(file_path)

    if not backups:
        return {
            "success": False,
            "reverted_to": None,
            "current_saved_as": None,
            "available_backups": [],
            "error": "No backups found for this file",
        }

    # Select backup
    target_backup: BackupInfo | None = None
    if backup_id is None:
        target_backup = backups[0]  # Most recent
    else:
        for b in backups:
            if b.id == backup_id:
                target_backup = b
                break
        if target_backup is None:
            return {
                "success": False,
                "reverted_to": None,
                "current_saved_as": None,
                "available_backups": [_backup_to_dict(b) for b in backups],
                "error": f"Backup {backup_id} not found. See available_backups.",
            }

    # At this point target_backup is guaranteed to be set
    assert target_backup is not None

    # Save current state before revert
    current_backup = create_backup(file_path)

    # Perform revert
    shutil.copy2(target_backup.path, file_path)

    # Get updated backup list
    updated_backups = list_backups(file_path)

    return {
        "success": True,
        "reverted_to": _backup_to_dict(target_backup),
        "current_saved_as": _backup_to_dict(current_backup),
        "available_backups": [_backup_to_dict(b) for b in updated_backups],
    }
