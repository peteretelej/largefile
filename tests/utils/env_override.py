"""Environment variable override utilities for testing."""

import importlib
import os
from contextlib import contextmanager


@contextmanager
def override_env(**env_vars: str):
    """Temporarily override environment variables for testing.

    This context manager allows tests to modify environment variables
    and automatically restores them when the test completes.

    Usage:
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="1"):
            # Environment variable is set to "1"
            # Config will be reloaded to pick up new value
            test_code_here()
        # Environment variable is restored to original value

    Args:
        **env_vars: Environment variables to set (key=value)
    """
    old_values: dict[str, str | None] = {}

    try:
        # Save current values and set new ones
        for key, value in env_vars.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = str(value)

        # Force config module reload to pick up new environment variables
        import src.config

        importlib.reload(src.config)

        # Also reload any modules that import config
        import src.file_access

        importlib.reload(src.file_access)

        yield

    finally:
        # Restore original values
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

        # Reload config again to restore original settings
        import src.config

        importlib.reload(src.config)

        # Reload dependent modules
        import src.file_access

        importlib.reload(src.file_access)


def get_test_file_sizes():
    """Get sizes of test data files for strategy testing.

    Returns:
        Dict mapping file names to sizes in bytes
    """
    from pathlib import Path

    test_data_dir = Path(__file__).parent.parent / "test_data"

    files = {
        "spring-application.java": test_data_dir / "java" / "spring-application.java",
        "django-models.py": test_data_dir / "python" / "django-models.py",
        "lodash-utility.js": test_data_dir / "javascript" / "lodash-utility.js",
        "shakespeare-complete.txt": test_data_dir / "text" / "shakespeare-complete.txt",
    }

    sizes = {}
    for name, path in files.items():
        if path.exists():
            sizes[name] = path.stat().st_size

    return sizes
