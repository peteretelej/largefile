import asyncio

from .server import main


def cli_main() -> None:
    """CLI entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
