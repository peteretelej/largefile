"""MCP server implementation."""

import logging
import sys

from mcp.server import Server

from . import tools
from .config import config
from .mcp_schemas import register_tool_handlers

logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logging.getLogger().setLevel(getattr(logging, config.log_level, logging.WARNING))


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
