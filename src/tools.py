from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import config
from .data_models import FileOverview, SearchResult
from .editor import atomic_edit_file
from .exceptions import EditError, FileAccessError, SearchError, TreeSitterError
from .file_access import (
    detect_file_encoding,
    get_file_info,
    normalize_path,
    read_file_content,
    read_file_lines,
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
    Detects long lines for truncation and returns search hints for efficient
    exploration.

    CRITICAL: You must use an absolute file path - relative paths will fail.
    DO NOT attempt to read large files directly as they exceed context limits.

    Parameters:
    - absolute_file_path: Absolute path to the file

    Returns:
    - FileOverview with line count, file size, detected encoding, and search hints
    """
    canonical_path = normalize_path(absolute_file_path)
    file_info = get_file_info(canonical_path)

    lines = read_file_lines(canonical_path)
    content = read_file_content(canonical_path)
    detected_encoding = detect_file_encoding(canonical_path)

    has_long_lines = any(len(line) > config.max_line_length for line in lines)

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
        has_long_lines=has_long_lines,
        outline=outline,
        search_hints=search_hints,
    )

    return {
        "line_count": overview.line_count,
        "file_size": overview.file_size,
        "encoding": overview.encoding,
        "has_long_lines": overview.has_long_lines,
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
    context_lines: int = 2,
    fuzzy: bool = True,
) -> dict:
    """Find patterns with fuzzy matching and context using auto-detected encoding.

    Uses fuzzy matching via Levenshtein distance to handle real-world
    formatting variations. Returns context lines around matches for better
    understanding.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - pattern: Search pattern (exact or fuzzy matching)
    - max_results: Maximum number of results to return
    - context_lines: Number of context lines before/after match
    - fuzzy: Enable fuzzy matching (default True)

    Returns:
    - List of search results with line numbers, matches, and context
    """
    canonical_path = normalize_path(absolute_file_path)

    matches = search_file(canonical_path, pattern, fuzzy)

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
    }


@handle_tool_errors
def read_content(
    absolute_file_path: str,
    target: int | str,
    mode: str = "lines",
) -> dict:
    """Read content from specific location in file using auto-detected encoding.

    Read content starting from a line number or around a search pattern.
    Returns a reasonable chunk of content for LLM consumption.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - target: Line number or search pattern to locate content
    - mode: "lines" for line-based reading (semantic mode future enhancement)

    Returns:
    - Content string with metadata about the read operation
    """
    canonical_path = normalize_path(absolute_file_path)

    lines = read_file_lines(canonical_path)
    file_content = read_file_content(canonical_path)

    if isinstance(target, int):
        # Use semantic chunking if mode is "semantic" and tree-sitter is available
        if mode == "semantic":
            try:
                chunk_content, start_line, end_line = get_semantic_chunk(
                    canonical_path, file_content, target
                )
                return {
                    "content": chunk_content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "total_lines": len(lines),
                    "mode": mode,
                    "target_type": "line_number",
                }
            except Exception:
                # Fall back to line-based reading
                pass

        # Default line-based reading
        start_line = max(1, target)
        end_line = min(len(lines), start_line + 20)

        content_lines = lines[start_line - 1 : end_line]
        content = "".join(content_lines)

        return {
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": len(lines),
            "mode": mode,
            "target_type": "line_number",
        }

    else:
        matches = search_file(canonical_path, str(target), fuzzy=True)

        if not matches:
            return {
                "content": "",
                "error": f"Pattern '{target}' not found in file",
                "total_lines": len(lines),
                "mode": mode,
                "target_type": "pattern",
            }

        first_match = matches[0]
        start_line = max(1, first_match.line_number - 5)
        end_line = min(len(lines), first_match.line_number + 15)

        content_lines = lines[start_line - 1 : end_line]
        content = "".join(content_lines)

        return {
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "match_line": first_match.line_number,
            "similarity_score": first_match.similarity_score,
            "total_lines": len(lines),
            "mode": mode,
            "target_type": "pattern",
            "pattern": str(target),
        }


@handle_tool_errors
def edit_content(
    absolute_file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy: bool = True,
    preview: bool = True,
) -> dict:
    """PRIMARY EDITING METHOD using search/replace blocks with auto-detected encoding.

    Fuzzy matching handles whitespace variations. Eliminates line number
    confusion that causes LLM errors. This replaces line-based editing.
    Creates automatic backups before changes.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - search_text: Text to find and replace
    - replace_text: Replacement text
    - fuzzy: Enable fuzzy matching for search_text
    - preview: Show preview without making changes (default True)

    Returns:
    - EditResult with success status, preview, and change details
    """
    result = atomic_edit_file(
        absolute_file_path, search_text, replace_text, fuzzy, preview
    )

    return {
        "success": result.success,
        "preview": result.preview,
        "changes_made": result.changes_made,
        "match_type": result.match_type,
        "similarity_used": result.similarity_used,
        "line_number": result.line_number,
        "backup_created": result.backup_created,
    }
