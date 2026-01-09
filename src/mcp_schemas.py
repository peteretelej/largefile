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
            description="Analyze file structure and generate semantic outline. Use before working with large files to understand organization and find optimal search patterns. Returns file stats, hierarchical outline, and suggested search terms. Requires absolute file paths only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="search_content",
            description="Search for text patterns in large files with fuzzy matching. Use when locating functions, classes, variables, or specific text within files. Returns ranked results with context and similarity scores. Requires absolute file paths only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to find",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (1-100)",
                        "default": 20,
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Context lines before/after match",
                        "default": 2,
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable similarity-based matching",
                        "default": True,
                    },
                },
                "required": ["absolute_file_path", "pattern"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="read_content",
            description="Read specific content from large files using semantic chunking. Use after locating content with search to examine complete functions, classes, or code sections. Returns semantically complete blocks rather than arbitrary line ranges. Use mode='tail' to efficiently read the last N lines from log files or append-only data. Requires absolute file paths only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to target file",
                    },
                    "target": {
                        "oneOf": [{"type": "integer"}, {"type": "string"}],
                        "description": "Line number, search pattern, or number of lines from end (for tail mode)",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Content extraction method: 'lines' for line-based, 'semantic' for tree-sitter chunking, 'tail' for last N lines",
                        "default": "lines",
                        "enum": ["lines", "semantic", "tail"],
                    },
                },
                "required": ["absolute_file_path", "target"],
            },
            annotations=types.ToolAnnotations(readOnlyHint=True),
        ),
        types.Tool(
            name="edit_content",
            description="Modify large files using search and replace operations with fuzzy matching. Supports single edit (search_text/replace_text) or batch edit (changes array) for multiple atomic changes. Returns diff preview and creates automatic backups. Requires absolute file paths only.",
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
                        "description": "New text content (single edit mode)",
                    },
                    "changes": {
                        "type": "array",
                        "description": "Array of changes for batch edit mode. Each change has search, replace, and optional fuzzy fields",
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
                                    "description": "Per-change fuzzy override",
                                },
                            },
                            "required": ["search", "replace"],
                        },
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable similarity-based text matching (default for all changes)",
                        "default": True,
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Show changes without applying them",
                        "default": True,
                    },
                },
                "required": ["absolute_file_path"],
            },
            annotations=types.ToolAnnotations(destructiveHint=True),
        ),
        types.Tool(
            name="revert_edit",
            description="Revert a file to a previous backup state. Creates backup of current state before reverting. Use to recover from bad edits. Returns available backups list. Requires absolute file paths only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to revert",
                    },
                    "backup_id": {
                        "type": "string",
                        "description": "Backup timestamp ID to revert to. If omitted, uses most recent backup.",
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
