from mcp.server import Server

from src.server import create_server


class TestMCPServer:
    """Test MCP server functionality."""

    def test_server_creation(self):
        """Test that MCP server can be created."""
        server = create_server()

        assert isinstance(server, Server)
        assert server.name == "largefile"

    def test_server_configuration(self):
        """Test that server is properly configured."""
        server = create_server()

        assert server.name == "largefile"
        assert isinstance(server, Server)
