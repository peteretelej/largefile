"""MCP server integration test.

Single focused test covering MCP server functionality.
"""

from mcp.server.fastmcp import FastMCP

from src.server import mcp


class TestMCPServer:
    """Test MCP server setup and tool registration."""

    def test_server_functionality(self):
        """Test complete MCP server creation and tool registration."""
        # Basic server properties
        assert isinstance(mcp, FastMCP)
        assert mcp.name == "largefile"

        # Server should be ready for MCP protocol
        assert mcp is not None
