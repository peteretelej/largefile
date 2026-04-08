"""MCP server implementation using FastMCP."""

import logging
import sys
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from . import tools
from .config import config

logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logging.getLogger().setLevel(getattr(logging, config.log_level, logging.WARNING))

mcp = FastMCP("largefile")


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def get_overview(
    absolute_file_path: Annotated[
        str,
        Field(
            description="Absolute path to target file (e.g., /path/to/large_module.py)"
        ),
    ],
    changed_lines: Annotated[
        list[list[int | str]] | None,
        Field(
            description="Optional list of changed line ranges from a diff. "
            "Each entry is [start, end] or [start, end, type] where type is "
            '"added", "modified", or "removed". '
            'Example: [[10, 15, "added"], [45, 52]]. '
            "Available from diffchunk list_chunks file_details output."
        ),
    ] = None,
) -> dict:
    """Get file structure, size, and semantic outline for large files (code, logs, data).

    Use FIRST when working with any file over 1000 lines or when you need to
    understand file structure. Returns: line count, byte size, binary detection,
    long line stats, section headings, and suggested search patterns. For code
    files, uses Tree-sitter to extract functions, classes, and structure. Does
    NOT return file content - use read_content or search_content for that.
    """
    return tools.get_overview(absolute_file_path, changed_lines=changed_lines)  # type: ignore[no-any-return]


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def search_content(
    absolute_file_path: Annotated[
        str, Field(description="Absolute path to target file")
    ],
    pattern: Annotated[
        str,
        Field(
            description="Text pattern to find (e.g., 'class User', 'ERROR', or regex like r'\\d{3}-\\d{4}')"
        ),
    ],
    max_results: Annotated[
        int, Field(description="Maximum results to return (1-100)", ge=1, le=100)
    ] = 20,
    context_lines: Annotated[
        int, Field(description="Lines of context before/after each match")
    ] = 2,
    fuzzy: Annotated[
        bool,
        Field(
            description="Enable fuzzy matching to handle typos and whitespace differences (default: true)"
        ),
    ] = True,
    regex: Annotated[
        bool,
        Field(
            description="Enable regex pattern matching (e.g., r'error.*timeout'). Disables fuzzy matching."
        ),
    ] = False,
    case_sensitive: Annotated[
        bool,
        Field(
            description="Match exact case when true (default: false for case-insensitive)"
        ),
    ] = False,
    invert: Annotated[
        bool,
        Field(description="Return lines that do NOT match the pattern (like grep -v)"),
    ] = False,
    count_only: Annotated[
        bool,
        Field(
            description="Return only the match count, not content. Efficient for large files."
        ),
    ] = False,
) -> dict:
    """Search large files for text patterns without loading entire content into memory.

    Use when finding functions, classes, errors, log entries, or counting
    occurrences. Supports: fuzzy matching (handles typos/whitespace), regex
    patterns, case-insensitive search, inverted matching (like grep -v), and
    count-only mode. Returns ranked matches with line numbers and context
    (lines truncated to 500 chars). When count_only=True, returns
    {count, pattern, fuzzy_enabled, regex_enabled, case_sensitive, inverted}
    instead of the full results structure.
    """
    return tools.search_content(  # type: ignore[no-any-return]
        absolute_file_path,
        pattern,
        max_results=max_results,
        context_lines=context_lines,
        fuzzy=fuzzy,
        regex=regex,
        case_sensitive=case_sensitive,
        invert=invert,
        count_only=count_only,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def read_content(
    absolute_file_path: Annotated[
        str, Field(description="Absolute path to target file")
    ],
    offset: Annotated[
        int,
        Field(
            description="Starting line number, 1-indexed (default: 1). Ignored in tail/head modes.",
            ge=1,
        ),
    ] = 1,
    limit: Annotated[
        int,
        Field(
            description="Lines to return (default 100). Reduce for files with long lines (check get_overview)."
        ),
    ] = 100,
    pattern: Annotated[
        str | None,
        Field(
            description="Pattern to position read (finds match, then reads around it). Overrides offset."
        ),
    ] = None,
    mode: Annotated[
        str,
        Field(
            description="Reading mode: 'lines' (by range), 'semantic' (tree-sitter chunks), 'tail' (last N), 'head' (first N)"
        ),
    ] = "lines",
) -> dict:
    """Read specific portions of large files efficiently.

    Use after search_content locates content, or directly with tail/head modes
    for logs. Modes: 'lines' (read by offset/limit), 'semantic' (complete
    functions/classes via Tree-sitter), 'tail' (last N lines - ideal for logs),
    'head' (first N lines). Does NOT search - use search_content first to find
    line numbers, then read_content to examine. For files over 500MB, tail/head
    modes are most efficient.
    """
    return tools.read_content(  # type: ignore[no-any-return]
        absolute_file_path,
        offset=offset,
        limit=limit,
        pattern=pattern,
        mode=mode,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def read_enclosing(
    absolute_file_path: Annotated[
        str,
        Field(description="Absolute path to target file"),
    ],
    line: Annotated[
        int,
        Field(description="Line number to find the enclosing function/class for", ge=1),
    ],
    depth: Annotated[
        int,
        Field(
            description="Nesting depth: 1 = innermost definition, 2 = parent (e.g., class containing a method)",
            ge=1,
        ),
    ] = 1,
    context_lines: Annotated[
        int,
        Field(
            description="Lines of context for fallback window when no enclosing definition is found",
            ge=1,
        ),
    ] = 40,
) -> dict:
    """Find the enclosing function or class for a specific line number.

    Given a file and line number, returns the complete enclosing definition
    (function, method, class, struct, etc.) containing that line. Use depth=2
    to get the parent definition (e.g., the class containing a method).
    Falls back to a centered context window for unsupported languages or
    top-level code.
    """
    return tools.read_enclosing(  # type: ignore[no-any-return]
        absolute_file_path,
        line=line,
        depth=depth,
        context_lines=context_lines,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    structured_output=False,
)
def edit_content(
    absolute_file_path: Annotated[
        str, Field(description="Absolute path to target file")
    ],
    changes: Annotated[
        list[dict[str, Any]],
        Field(
            description="Array of {search, replace, fuzzy?} objects. Applied in order."
        ),
    ],
    fuzzy: Annotated[
        bool,
        Field(description="Enable fuzzy matching for all changes (default: true)"),
    ] = True,
    preview: Annotated[
        bool,
        Field(
            description="Show diff preview without applying changes. Always preview first!"
        ),
    ] = True,
) -> dict:
    """Edit large files using search/replace with fuzzy matching.

    Use instead of line-based editing to avoid LLM line number errors. Fuzzy
    matching handles whitespace and formatting differences automatically.
    Preview mode (default) shows diff without applying. Creates automatic
    backup before changes - use revert_edit to undo. Does NOT support regex
    in replacement - patterns must be literal text (use fuzzy=true for
    flexibility).
    """
    return tools.edit_content(  # type: ignore[no-any-return]
        absolute_file_path,
        changes=changes,
        fuzzy=fuzzy,
        preview=preview,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    structured_output=False,
)
def revert_edit(
    absolute_file_path: Annotated[
        str, Field(description="Absolute path to the file to revert")
    ],
    backup_id: Annotated[
        str | None,
        Field(description="Backup ID from response. Omit to use most recent."),
    ] = None,
) -> dict:
    """Restore a file to a previous state from automatic backups.

    Use when edit_content made unwanted changes. Backups are created
    automatically before each edit. Current state is saved as new backup
    before reverting (so revert is reversible). Without backup_id, reverts to
    most recent backup. Returns list of available backups with timestamps.
    """
    return tools.revert_edit(  # type: ignore[no-any-return]
        absolute_file_path,
        backup_id=backup_id,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def list_directory(
    absolute_dir_path: Annotated[
        str, Field(description="The absolute path to the directory to list.")
    ],
    max_depth: Annotated[
        int,
        Field(
            description="How many levels deep to recurse (default: 1 = direct children only)."
        ),
    ] = 1,
    max_entries: Annotated[
        int | None,
        Field(
            description="Maximum total entries to return. Defaults to server config (200).",
            ge=1,
        ),
    ] = None,
    include_hidden: Annotated[
        bool,
        Field(description="Include entries starting with '.' (default: false)."),
    ] = False,
) -> dict:
    """List the contents of a directory.

    Each entry has a type field: 'dir' for directories, 'file' for files.
    Use max_depth > 1 to recurse into subdirectories. Automatically ignores
    __pycache__, node_modules, and .git. Returns entry type, size in bytes,
    and child count for directories.
    """
    return tools.list_directory(  # type: ignore[no-any-return]
        absolute_dir_path,
        max_depth=max_depth,
        max_entries=max_entries,
        include_hidden=include_hidden,
    )


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
    structured_output=False,
)
def search_directory(
    absolute_dir_path: Annotated[
        str, Field(description="The absolute path to the directory to search.")
    ],
    pattern: Annotated[str, Field(description="Text pattern to search for.")],
    include_pattern: Annotated[
        str,
        Field(
            description="fnmatch glob matched against file names (default: '*'). Examples: '*.py', '*.md', '*.ts'."
        ),
    ] = "*",
    max_results: Annotated[
        int | None,
        Field(
            description="Total match cap across all files. Defaults to server config (100).",
            ge=1,
            le=100,
        ),
    ] = None,
    context_lines: Annotated[
        int,
        Field(description="Lines of context before/after each match (default: 2)."),
    ] = 2,
    fuzzy: Annotated[
        bool,
        Field(
            description="Enable fuzzy matching (default: false, expensive for many files)."
        ),
    ] = False,
    regex: Annotated[
        bool,
        Field(description="Enable Python regex matching (default: false)."),
    ] = False,
    case_sensitive: Annotated[
        bool,
        Field(description="Case-sensitive search (default: false)."),
    ] = False,
    invert: Annotated[
        bool,
        Field(description="Return non-matching lines, like grep -v (default: false)."),
    ] = False,
    include_hidden: Annotated[
        bool,
        Field(description="Include dot-files and dot-dirs (default: false)."),
    ] = False,
) -> dict:
    """Search for a text pattern across all files in a directory.

    Returns results grouped by file with line numbers and context. Use
    include_pattern to filter by file extension (e.g. '*.py'). Automatically
    ignores __pycache__, node_modules, and .git. Prefer fuzzy=False (default)
    for multi-file search performance.
    """
    return tools.search_directory(  # type: ignore[no-any-return]
        absolute_dir_path,
        pattern,
        include_pattern=include_pattern,
        max_results=max_results,
        context_lines=context_lines,
        fuzzy=fuzzy,
        regex=regex,
        case_sensitive=case_sensitive,
        invert=invert,
        include_hidden=include_hidden,
    )
