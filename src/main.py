"""Main entry point for the largefile MCP server."""

import click
from mcp.server import Server


@click.command()
@click.option("--host", default="localhost", help="Host to bind the server to")
@click.option("--port", default=3000, help="Port to bind the server to")
def main(host: str, port: int):
    """Start the largefile MCP server."""
    click.echo(f"Starting largefile MCP server v0.0.1 on {host}:{port}")
    click.echo("This is a placeholder implementation - coming soon!")
    
    # TODO: Initialize actual MCP server
    # server = Server("largefile")
    # server.run(host=host, port=port)


if __name__ == "__main__":
    main()