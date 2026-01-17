"""MCP tool schema definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from mcp import types

if TYPE_CHECKING:
    from mcp.server import Server


class ToolsModule(Protocol):
    """Protocol for the tools module."""

    def get_overview(self, **kwargs: Any) -> Any: ...
    def search_content(self, **kwargs: Any) -> Any: ...
    def read_content(self, **kwargs: Any) -> Any: ...
    def edit_content(self, **kwargs: Any) -> Any: ...
    def revert_edit(self, **kwargs: Any) -> Any: ...


def get_tool_schemas() -> list[types.Tool]:
    """Get all MCP tool schema definitions."""
    return [
        types.Tool(
            name="get_overview",
            description=(
                "Get file structure, size, and semantic outline for large files (code, logs, data). "
                "Use FIRST when working with any file over 1000 lines or when you need to understand file structure. "
                "Returns: line count, byte size, binary detection, section headings, and suggested search patterns. "
                "For code files, uses Tree-sitter to extract functions, classes, and structure. "
                "Does NOT return file content - use read_content or search_content for that."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file (e.g., /path/to/large_module.py)",
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="search_content",
            description=(
                "Search large files for text patterns without loading entire content into memory. "
                "Use when finding functions, classes, errors, log entries, or counting occurrences. "
                "Supports: fuzzy matching (handles typos/whitespace), regex patterns, case-insensitive search, "
                "inverted matching (like grep -v), and count-only mode. "
                "Returns ranked matches with line numbers and surrounding context. "
                "For log files, combine with read_content tail mode to search recent entries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to find (e.g., 'class User', 'ERROR', or regex like r'\\d{3}-\\d{4}')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (1-100)",
                        "default": 20,
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Lines of context before/after each match",
                        "default": 2,
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching to handle typos and whitespace differences (default: true)",
                        "default": True,
                    },
                    "regex": {
                        "type": "boolean",
                        "description": "Enable regex pattern matching (e.g., r'error.*timeout'). Disables fuzzy matching.",
                        "default": False,
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Match exact case when true (default: false for case-insensitive)",
                        "default": False,
                    },
                    "invert": {
                        "type": "boolean",
                        "description": "Return lines that do NOT match the pattern (like grep -v)",
                        "default": False,
                    },
                    "count_only": {
                        "type": "boolean",
                        "description": "Return only the match count, not content. Efficient for large files.",
                        "default": False,
                    },
                },
                "required": ["absolute_file_path", "pattern"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="read_content",
            description=(
                "Read specific portions of large files efficiently. "
                "Use after search_content locates content, or directly with tail/head modes for logs. "
                "Modes: 'lines' (read by offset/limit), 'semantic' (complete functions/classes via Tree-sitter), "
                "'tail' (last N lines - ideal for logs), 'head' (first N lines). "
                "Does NOT search - use search_content first to find line numbers, then read_content to examine. "
                "For files over 500MB, tail/head modes are most efficient."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting line number, 1-indexed (default: 1). Ignored in tail/head modes.",
                        "default": 1,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum lines to return. For tail/head, number of lines from end/start.",
                        "default": 100,
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern to locate content. Reads around the first match.",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Reading mode: 'lines' (by range), 'semantic' (tree-sitter chunks), 'tail' (last N), 'head' (first N)",
                        "default": "lines",
                        "enum": ["lines", "semantic", "tail", "head"],
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="edit_content",
            description=(
                "Edit large files using search/replace with fuzzy matching. "
                "Use instead of line-based editing to avoid LLM line number errors. "
                "Fuzzy matching handles whitespace and formatting differences automatically. "
                "Always use preview=true first to verify matches before applying. "
                "Creates automatic backup before changes - use revert_edit to undo. "
                "Batch mode applies multiple changes atomically. "
                "Does NOT support regex in replacement - patterns must be literal text (use fuzzy=true for flexibility)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                    "search_text": {
                        "type": "string",
                        "description": "Text to find and replace (single edit mode)",
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "Replacement text (single edit mode)",
                    },
                    "changes": {
                        "type": "array",
                        "description": "Array of changes for batch editing. Each: {search, replace, fuzzy?}",
                        "items": {
                            "type": "object",
                            "properties": {
                                "search": {
                                    "type": "string",
                                    "description": "Text to find",
                                },
                                "replace": {
                                    "type": "string",
                                    "description": "Replacement text",
                                },
                                "fuzzy": {
                                    "type": "boolean",
                                    "description": "Override fuzzy matching for this change",
                                },
                            },
                            "required": ["search", "replace"],
                        },
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching for all changes (default: true)",
                        "default": True,
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Show diff preview without applying changes. Always preview first!",
                        "default": True,
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(destructiveHint=True),
        ),
        types.Tool(
            name="revert_edit",
            description=(
                "Restore a file to a previous state from automatic backups. "
                "Use when edit_content made unwanted changes. "
                "Backups are created automatically before each edit. "
                "Current state is saved as new backup before reverting (so revert is reversible). "
                "Without backup_id, reverts to most recent backup. "
                "Returns list of available backups with timestamps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to revert",
                    },
                    "backup_id": {
                        "type": "string",
                        "description": "Backup timestamp ID (e.g., '20240115_143022'). Omit for most recent.",
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(destructiveHint=True),
        ),
    ]


def register_tool_handlers(server: Server, tools_module: ToolsModule) -> None:
    """Register tool handlers with the MCP server."""

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[types.Tool]:
        """List available tools."""
        return get_tool_schemas()

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        if name == "get_overview":
            result = tools_module.get_overview(**arguments)
        elif name == "search_content":
            result = tools_module.search_content(**arguments)
        elif name == "read_content":
            result = tools_module.read_content(**arguments)
        elif name == "edit_content":
            result = tools_module.edit_content(**arguments)
        elif name == "revert_edit":
            result = tools_module.revert_edit(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=str(result))]
