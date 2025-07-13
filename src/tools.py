from pathlib import Path

from .config import config
from .data_models import FileOverview, OutlineItem, SearchResult
from .exceptions import EditError, FileAccessError, SearchError
from .file_access import (
    create_backup,
    get_file_info,
    normalize_path,
    read_file_content,
    read_file_lines,
    write_file_content,
)
from .search_engine import search_file


def handle_tool_errors(func):
    """Decorator to handle tool errors consistently."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileAccessError as e:
            return {
                "error": f"File access failed: {e}",
                "suggestion": "Check file path and permissions",
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
def get_overview(absolute_file_path: str, encoding: str = "utf-8") -> dict:
    """Get file structure with basic analysis.

    Provides file metadata, line count, and basic structure analysis.
    Detects long lines for truncation and returns search hints for efficient
    exploration.

    CRITICAL: You must use an absolute file path - relative paths will fail.
    DO NOT attempt to read large files directly as they exceed context limits.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - encoding: File encoding (utf-8, latin-1, etc.)

    Returns:
    - FileOverview with line count, file size, encoding info, and search hints
    """
    canonical_path = normalize_path(absolute_file_path)
    file_info = get_file_info(canonical_path)

    lines = read_file_lines(canonical_path, encoding)

    has_long_lines = any(len(line) > config.max_line_length for line in lines)

    outline = []
    search_hints = []

    file_ext = Path(canonical_path).suffix.lower()
    if file_ext == ".py":
        search_hints = ["def ", "class ", "import ", "from "]
    elif file_ext in [".js", ".ts"]:
        search_hints = ["function ", "class ", "const ", "import "]
    elif file_ext == ".go":
        search_hints = ["func ", "type ", "import ", "package "]
    elif file_ext == ".rs":
        search_hints = ["fn ", "struct ", "impl ", "use "]
    else:
        search_hints = ["TODO", "FIXME", "NOTE", "HACK"]

    for i, line in enumerate(lines[:50], 1):
        line_stripped = line.strip()
        if any(hint.strip() in line_stripped for hint in search_hints):
            outline.append(
                OutlineItem(
                    name=line_stripped[:50] + "..."
                    if len(line_stripped) > 50
                    else line_stripped,
                    type="definition",
                    line_number=i,
                    end_line=i,
                    children=[],
                    line_count=1,
                )
            )

    overview = FileOverview(
        line_count=len(lines),
        file_size=file_info["size"],
        encoding=encoding,
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
    encoding: str = "utf-8",
    max_results: int = 20,
    context_lines: int = 2,
    fuzzy: bool = True,
) -> dict:
    """Find patterns with fuzzy matching and context.

    Uses fuzzy matching via Levenshtein distance to handle real-world
    formatting variations. Returns context lines around matches for better
    understanding.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - pattern: Search pattern (exact or fuzzy matching)
    - encoding: File encoding
    - max_results: Maximum number of results to return
    - context_lines: Number of context lines before/after match
    - fuzzy: Enable fuzzy matching (default True)

    Returns:
    - List of search results with line numbers, matches, and context
    """
    canonical_path = normalize_path(absolute_file_path)

    matches = search_file(canonical_path, pattern, encoding, fuzzy)

    lines = read_file_lines(canonical_path, encoding)

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

        match_content = match.content
        truncated = len(match_content) > config.truncate_length
        if truncated:
            match_content = match_content[: config.truncate_length] + "..."

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
    encoding: str = "utf-8",
    mode: str = "lines",
) -> dict:
    """Read content from specific location in file.

    Read content starting from a line number or around a search pattern.
    Returns a reasonable chunk of content for LLM consumption.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - target: Line number or search pattern to locate content
    - encoding: File encoding
    - mode: "lines" for line-based reading (semantic mode future enhancement)

    Returns:
    - Content string with metadata about the read operation
    """
    canonical_path = normalize_path(absolute_file_path)

    lines = read_file_lines(canonical_path, encoding)

    if isinstance(target, int):
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
        matches = search_file(canonical_path, str(target), encoding, fuzzy=True)

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
    encoding: str = "utf-8",
    fuzzy: bool = True,
    preview: bool = True,
) -> dict:
    """PRIMARY EDITING METHOD using search/replace blocks.

    Fuzzy matching handles whitespace variations. Eliminates line number
    confusion that causes LLM errors. This replaces line-based editing.
    Creates automatic backups before changes.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - search_text: Text to find and replace
    - replace_text: Replacement text
    - encoding: File encoding
    - fuzzy: Enable fuzzy matching for search_text
    - preview: Show preview without making changes (default True)

    Returns:
    - EditResult with success status, preview, and change details
    """
    canonical_path = normalize_path(absolute_file_path)

    original_content = read_file_content(canonical_path, encoding)

    if search_text in original_content:
        modified_content = original_content.replace(search_text, replace_text, 1)
        match_type = "exact"
        similarity = 1.0
        line_number = (
            original_content[: original_content.find(search_text)].count("\n") + 1
        )
    elif fuzzy:
        lines = read_file_lines(canonical_path, encoding)
        matches = search_file(canonical_path, search_text, encoding, fuzzy=True)

        if not matches:
            return {
                "success": False,
                "preview": f"No matches found for: {search_text}",
                "changes_made": 0,
                "match_type": "none",
                "similarity_used": 0.0,
                "line_number": 0,
            }

        best_match = matches[0]
        actual_line = lines[best_match.line_number - 1].rstrip("\n\r")
        modified_content = original_content.replace(actual_line, replace_text, 1)
        match_type = "fuzzy"
        similarity = best_match.similarity_score
        line_number = best_match.line_number
    else:
        return {
            "success": False,
            "preview": f"No exact matches found for: {search_text}",
            "changes_made": 0,
            "match_type": "none",
            "similarity_used": 0.0,
            "line_number": 0,
        }

    preview_lines = []
    original_lines = original_content.split("\n")
    modified_lines = modified_content.split("\n")

    for i, (orig, mod) in enumerate(
        zip(original_lines, modified_lines, strict=False), 1
    ):
        if orig != mod:
            preview_lines.append(f"Line {i}:")
            preview_lines.append(f"- {orig}")
            preview_lines.append(f"+ {mod}")
            break

    preview_text = "\n".join(preview_lines)

    result = {
        "success": True,
        "preview": preview_text,
        "changes_made": 1,
        "match_type": match_type,
        "similarity_used": similarity,
        "line_number": line_number,
    }

    if preview:
        return result

    backup_path = create_backup(canonical_path)
    write_file_content(canonical_path, modified_content, encoding)

    result["backup_created"] = backup_path
    return result
