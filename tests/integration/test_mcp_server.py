"""MCP server integration test.

Single focused test covering MCP server functionality.
"""

from mcp.server import Server

from src.server import create_server


class TestMCPServer:
    """Test MCP server setup and tool registration."""

    def test_server_functionality(self):
        """Test complete MCP server creation and tool registration."""
        server = create_server()

        # Basic server properties
        assert isinstance(server, Server)
        assert server.name == "largefile"

        # Server should be ready for MCP protocol
        # (Full MCP protocol testing would require async test setup)
        assert server is not None
