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


def get_tool_schemas() -> list[types.Tool]:
    """Get all MCP tool schema definitions."""
    return [
        types.Tool(
            name="get_overview",
            description="Get file structure with Tree-sitter semantic analysis for large files. Use this as your FIRST STEP when working with any file over 1000 lines or when you need to understand file structure before targeted operations. CRITICAL: You must use an absolute file path - relative paths will fail. DO NOT attempt to read large files directly as they exceed context limits and waste tokens on irrelevant content. This tool provides the roadmap for systematic file exploration and suggests optimal search patterns for the specific file type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                },
                "required": ["absolute_file_path"],
            },
        ),
        types.Tool(
            name="search_content",
            description="Find patterns in large files with fuzzy matching and semantic context. Use this when you need to locate specific functions, classes, patterns, or text within files that are too large for direct reading. CRITICAL: You must use an absolute file path - relative paths will fail. DO NOT attempt to grep or search large files directly - use this tool for efficient pattern location with context. Essential for finding all instances of functions, variables, TODO comments, error patterns, or any text within large codebases. Use fuzzy matching to handle formatting variations and typos.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Context lines around match",
                        "default": 2,
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching",
                        "default": True,
                    },
                },
                "required": ["absolute_file_path", "pattern"],
            },
        ),
        types.Tool(
            name="read_content",
            description="Read targeted content from large files using semantic chunking instead of arbitrary line ranges. Use this when you need to examine specific functions, classes, or code sections after locating them with search_content. CRITICAL: You must use an absolute file path - relative paths will fail. DO NOT attempt to read large files directly - use this tool to get manageable, semantically complete chunks. Essential for understanding code context, examining function implementations, or reading specific sections without loading entire files. Use semantic mode to get complete functions/classes instead of cut-off arbitrary ranges.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "target": {
                        "oneOf": [{"type": "integer"}, {"type": "string"}],
                        "description": "Line number or search pattern",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Reading mode",
                        "default": "lines",
                        "enum": ["lines", "semantic"],
                    },
                },
                "required": ["absolute_file_path", "target"],
            },
        ),
        types.Tool(
            name="edit_content",
            description="PRIMARY EDITING METHOD for large files using search/replace blocks instead of error-prone line-based editing. Use this for ALL file modifications when working with large files - never attempt manual line-based edits. CRITICAL: You must use an absolute file path - relative paths will fail. ALWAYS use preview=True first to verify changes before applying. This tool eliminates LLM line number confusion and handles whitespace variations with fuzzy matching. Essential for refactoring, renaming, bug fixes, and any code modifications. Creates automatic backups before all changes for safety.",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "search_text": {
                        "type": "string",
                        "description": "Text to find and replace",
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Enable fuzzy matching",
                        "default": True,
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Show preview without making changes",
                        "default": True,
                    },
                },
                "required": ["absolute_file_path", "search_text", "replace_text"],
            },
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
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=str(result))]
