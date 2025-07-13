"""File access strategy testing with custom thresholds.

Test mmap and streaming strategies by adjusting environment variables.

File sizes for reference:
- django-models.py: 0.09 MB
- lodash-utility.js: 0.52 MB
- shakespeare-complete.txt: 5.36 MB
"""

from pathlib import Path

from src.file_access import get_file_info, read_file_content, read_file_lines
from src.tools import get_overview, search_content
from tests.utils.env_override import override_env


class TestFileAccessStrategies:
    """Test file access strategies with environment variable overrides."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_mmap_strategy_with_shakespeare(self):
        """Test mmap strategy with Shakespeare text (5.36MB file).

        Lower memory threshold to 1MB so Shakespeare uses mmap strategy.
        """
        shakespeare_file = self.test_data_dir / "text" / "shakespeare-complete.txt"

        if not shakespeare_file.exists():
            return  # Skip if file doesn't exist

        # Set memory threshold to 1MB to force mmap strategy for 5.36MB file
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="1"):
            # Verify strategy selection
            file_info = get_file_info(str(shakespeare_file))
            assert file_info["strategy"] == "mmap", (
                f"Expected mmap strategy, got {file_info['strategy']}"
            )
            assert file_info["size"] > 1_000_000, "File should be larger than 1MB"

            # Test file reading with mmap
            content = read_file_content(str(shakespeare_file))
            assert len(content) > 1_000_000, "Content should be substantial"
            assert "Shakespeare" in content or "HAMLET" in content or "Romeo" in content

            # Test line reading with mmap
            lines = read_file_lines(str(shakespeare_file))
            assert len(lines) > 1000, "Should have many lines"

            # Test overview generation with mmap
            overview = get_overview(str(shakespeare_file))
            assert overview["line_count"] > 1000
            assert overview["file_size"] == file_info["size"]

            # Test search with mmap
            search_results = search_content(
                str(shakespeare_file), "love", max_results=5
            )
            assert search_results["total_matches"] > 0, (
                "Should find 'love' in Shakespeare"
            )

    def test_streaming_strategy_with_shakespeare(self):
        """Test streaming strategy with Shakespeare text.

        Set both memory and mmap thresholds low to force streaming.
        """
        shakespeare_file = self.test_data_dir / "text" / "shakespeare-complete.txt"

        if not shakespeare_file.exists():
            return  # Skip if file doesn't exist

        # Set thresholds to force streaming: memory=1MB, mmap=2MB
        # Shakespeare is 5.36MB, so will use streaming
        with override_env(
            LARGEFILE_MEMORY_THRESHOLD_MB="1", LARGEFILE_MMAP_THRESHOLD_MB="2"
        ):
            # Verify strategy selection
            file_info = get_file_info(str(shakespeare_file))
            assert file_info["strategy"] == "streaming", (
                f"Expected streaming strategy, got {file_info['strategy']}"
            )

            # Test file reading with streaming
            content = read_file_content(str(shakespeare_file))
            assert len(content) > 2_000_000, "Content should be substantial"
            assert "Shakespeare" in content or "HAMLET" in content or "Romeo" in content

            # Test line reading with streaming
            lines = read_file_lines(str(shakespeare_file))
            assert len(lines) > 1000, "Should have many lines"

            # Test overview generation with streaming
            overview = get_overview(str(shakespeare_file))
            assert overview["line_count"] > 1000
            assert overview["file_size"] == file_info["size"]

    def test_mmap_strategy_with_django(self):
        """Test mmap strategy with Django models file (0.09MB).

        Set memory threshold to 0MB to force mmap for Django file.
        """
        django_file = self.test_data_dir / "python" / "django-models.py"

        if not django_file.exists():
            return  # Skip if file doesn't exist

        # Set memory threshold to 0MB to force mmap for 0.09MB file
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="0"):
            # Verify strategy selection
            file_info = get_file_info(str(django_file))
            assert file_info["strategy"] == "mmap", (
                f"Expected mmap strategy, got {file_info['strategy']}"
            )
            assert file_info["size"] > 50_000, "File should be larger than 50KB"

            # Test file operations with mmap
            content = read_file_content(str(django_file))
            assert len(content) > 50_000, "Content should be substantial"
            assert "django" in content.lower() or "model" in content.lower()

            # Test overview with mmap
            overview = get_overview(str(django_file))
            assert overview["line_count"] > 100

            # Test search with mmap
            search_results = search_content(str(django_file), "class", max_results=10)
            assert search_results["total_matches"] > 0, "Should find classes in Python"

    def test_streaming_strategy_with_lodash(self):
        """Test streaming strategy with Lodash file (0.52MB).

        Force streaming by setting very low thresholds.
        """
        lodash_file = self.test_data_dir / "javascript" / "lodash-utility.js"

        if not lodash_file.exists():
            return  # Skip if file doesn't exist

        # Force streaming: memory=0MB, mmap=0MB (Lodash is 0.52MB)
        with override_env(
            LARGEFILE_MEMORY_THRESHOLD_MB="0", LARGEFILE_MMAP_THRESHOLD_MB="0"
        ):
            # Verify strategy selection
            file_info = get_file_info(str(lodash_file))
            assert file_info["strategy"] == "streaming", (
                f"Expected streaming strategy, got {file_info['strategy']}"
            )

            # Test streaming operations
            content = read_file_content(str(lodash_file))
            assert len(content) > 200_000, "Content should be substantial"

            lines = read_file_lines(str(lodash_file))
            assert len(lines) > 100, "Should have many lines"

    def test_memory_vs_mmap_boundary(self):
        """Test strategy selection at memory/mmap boundary."""
        django_file = self.test_data_dir / "python" / "django-models.py"  # 0.09MB

        if not django_file.exists():
            return

        # Test with memory threshold above file size - should use memory
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="1"):  # 1MB > 0.09MB
            file_info = get_file_info(str(django_file))
            assert file_info["strategy"] == "memory"

        # Test with memory threshold below file size - should use mmap
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="0"):  # 0MB < 0.09MB
            file_info = get_file_info(str(django_file))
            assert file_info["strategy"] == "mmap"

    def test_mmap_vs_streaming_boundary(self):
        """Test strategy selection at mmap/streaming boundary."""
        shakespeare_file = (
            self.test_data_dir / "text" / "shakespeare-complete.txt"
        )  # 5.36MB

        if not shakespeare_file.exists():
            return

        # Force mmap by setting thresholds: memory=1MB, mmap=10MB
        with override_env(
            LARGEFILE_MEMORY_THRESHOLD_MB="1", LARGEFILE_MMAP_THRESHOLD_MB="10"
        ):
            file_info = get_file_info(str(shakespeare_file))
            assert file_info["strategy"] == "mmap"  # 5.36MB < 10MB

        # Force streaming by setting thresholds: memory=1MB, mmap=2MB
        with override_env(
            LARGEFILE_MEMORY_THRESHOLD_MB="1", LARGEFILE_MMAP_THRESHOLD_MB="2"
        ):
            file_info = get_file_info(str(shakespeare_file))
            assert file_info["strategy"] == "streaming"  # 5.36MB > 2MB

    def test_strategy_error_handling(self):
        """Test error handling across different strategies."""
        # Test with non-existent file across strategies
        nonexistent = "/nonexistent/file.txt"

        # Test each strategy with non-existent file
        for memory_mb, mmap_mb in [("50", "500"), ("1", "500"), ("1", "2")]:
            with override_env(
                LARGEFILE_MEMORY_THRESHOLD_MB=memory_mb,
                LARGEFILE_MMAP_THRESHOLD_MB=mmap_mb,
            ):
                try:
                    get_file_info(nonexistent)
                    raise AssertionError("Should have raised FileAccessError")
                except Exception as e:
                    assert "Cannot access file" in str(e)

    def test_strategy_consistency(self):
        """Test that strategy selection is consistent and deterministic."""
        shakespeare_file = self.test_data_dir / "text" / "shakespeare-complete.txt"

        if not shakespeare_file.exists():
            return

        # Test same configuration multiple times
        with override_env(LARGEFILE_MEMORY_THRESHOLD_MB="1"):
            strategies = []
            for _ in range(3):
                file_info = get_file_info(str(shakespeare_file))
                strategies.append(file_info["strategy"])

            # All should be the same
            assert len(set(strategies)) == 1, (
                f"Strategy selection not consistent: {strategies}"
            )
            assert strategies[0] == "mmap", (
                f"Expected mmap strategy, got {strategies[0]}"
            )
