"""MCP server implementation."""

from mcp.server import Server

from . import tools
from .mcp_schemas import register_tool_handlers


def create_server() -> Server:
    """Create MCP server with largefile tools."""
    server: Server = Server("largefile")
    register_tool_handlers(server, tools)
    return server


async def main() -> None:
    """Main server entry point."""
    server = create_server()

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
