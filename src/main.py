from .server import mcp


def cli_main() -> None:
    """CLI entry point."""
    mcp.run()


if __name__ == "__main__":
    cli_main()
