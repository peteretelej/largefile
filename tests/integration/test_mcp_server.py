"""MCP server integration test.

Tests covering FastMCP server setup, tool registration, schemas, and annotations.
"""

from mcp.server.fastmcp import FastMCP

from src.server import mcp

EXPECTED_TOOLS = {
    "get_overview",
    "search_content",
    "read_content",
    "edit_content",
    "revert_edit",
    "list_directory",
    "search_directory",
}

READ_ONLY_TOOLS = {
    "get_overview",
    "search_content",
    "read_content",
    "list_directory",
    "search_directory",
}

DESTRUCTIVE_TOOLS = {"edit_content", "revert_edit"}


class TestMCPServer:
    """Test MCP server setup and tool registration."""

    def test_server_is_fastmcp(self):
        """Server is a FastMCP instance."""
        assert isinstance(mcp, FastMCP)
        assert mcp.name == "largefile"

    def test_all_tools_registered(self):
        """All 7 tools are registered."""
        tools = mcp._tool_manager.list_tools()
        tool_names = {t.name for t in tools}
        assert tool_names == EXPECTED_TOOLS

    def test_tool_schemas_have_descriptions(self):
        """All tools have non-empty descriptions."""
        for tool in mcp._tool_manager.list_tools():
            assert tool.description, f"Tool {tool.name} missing description"

    def test_no_output_schema(self):
        """No tool has outputSchema (Claude Code bug #25081)."""
        for tool in mcp._tool_manager.list_tools():
            assert tool.output_schema is None, (
                f"Tool {tool.name} has outputSchema set, which will cause Claude Code to drop all tools"
            )

    def test_read_only_annotations(self):
        """Read-only tools have readOnlyHint=True."""
        for name in READ_ONLY_TOOLS:
            tool = mcp._tool_manager.get_tool(name)
            assert tool is not None, f"{name} not registered"
            assert tool.annotations is not None, f"{name} missing annotations"
            assert tool.annotations.readOnlyHint is True, (
                f"{name} should have readOnlyHint=True"
            )

    def test_destructive_annotations(self):
        """Destructive tools have destructiveHint=True."""
        for name in DESTRUCTIVE_TOOLS:
            tool = mcp._tool_manager.get_tool(name)
            assert tool is not None, f"{name} not registered"
            assert tool.annotations is not None, f"{name} missing annotations"
            assert tool.annotations.destructiveHint is True, (
                f"{name} should have destructiveHint=True"
            )
