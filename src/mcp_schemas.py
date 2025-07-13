"""MCP tool schema definitions."""

from mcp import types


def get_tool_schemas() -> list[types.Tool]:
    """Get all MCP tool schema definitions."""
    return [
        types.Tool(
            name="get_overview",
            description="Get file structure with basic analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8",
                    },
                },
                "required": ["absolute_file_path"],
            },
        ),
        types.Tool(
            name="search_content",
            description="Find patterns with fuzzy matching and context",
            inputSchema={
                "type": "object",
                "properties": {
                    "absolute_file_path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8",
                    },
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
            description="Read content from specific location in file",
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
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8",
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
            description="PRIMARY EDITING METHOD using search/replace blocks",
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
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8",
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


def register_tool_handlers(server, tools_module):
    """Register tool handlers with the MCP server."""
    
    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available tools."""
        return get_tool_schemas()

    @server.call_tool()
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