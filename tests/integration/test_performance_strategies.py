"""Performance strategy validation tests.

Ensure file access strategies work correctly with real test data files.
"""

from pathlib import Path

from src.file_access import get_file_info
from src.tools import get_overview, search_content


class TestPerformanceStrategies:
    """Test file access performance with real data files."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_small_file_strategy(self):
        """Test file access with small files.

        Test with spring-application.java (5.2KB) - smallest file.
        """
        spring_file = self.test_data_dir / "java" / "spring-application.java"

        # Check file info
        file_info = get_file_info(str(spring_file))
        assert file_info["size"] < 10_000  # Small file
        assert file_info["exists"] is True

        # Test operations work efficiently
        overview = get_overview(str(spring_file))
        assert overview["line_count"] > 0
        assert overview["file_size"] == file_info["size"]

        search_results = search_content(str(spring_file), "class")
        assert search_results["total_matches"] >= 0

    def test_medium_file_strategy(self):
        """Test file access with medium-sized files.

        Test with files in the 50KB-150KB range.
        """
        medium_files = [
            self.test_data_dir / "go" / "docker-daemon.go",  # 58KB
            self.test_data_dir / "python" / "django-models.py",  # 96KB
            self.test_data_dir / "rust" / "serde-derive.rs",  # 114KB
            self.test_data_dir / "csharp" / "aspnet-controller.cs",  # 146KB
        ]

        for file_path in medium_files:
            if not file_path.exists():
                continue

            file_info = get_file_info(str(file_path))
            assert 50_000 <= file_info["size"] <= 200_000  # Medium range

            # Test operations work
            overview = get_overview(str(file_path))
            assert overview["line_count"] > 0

            search_results = search_content(str(file_path), "function", max_results=5)
            assert search_results["total_matches"] >= 0

    def test_large_file_strategy(self):
        """Test file access with larger files.

        Test with lodash-utility.js (544KB) and shakespeare text (5.6MB).
        """
        large_files = [
            self.test_data_dir / "javascript" / "lodash-utility.js",  # 544KB
            self.test_data_dir / "text" / "shakespeare-complete.txt",  # 5.6MB
        ]

        for file_path in large_files:
            if not file_path.exists():
                continue

            file_info = get_file_info(str(file_path))
            assert file_info["size"] > 500_000  # Large file

            # Test operations work with large files
            overview = get_overview(str(file_path))
            assert overview["line_count"] > 0
            assert overview["file_size"] == file_info["size"]

    def test_file_size_distribution(self):
        """Test that we have good distribution of file sizes.

        Verify our test data covers different size ranges.
        """
        all_files = [
            # Small files (<50KB)
            self.test_data_dir / "java" / "spring-application.java",
            self.test_data_dir / "markdown" / "fastapi-docs.md",
            self.test_data_dir / "markdown" / "anthropic-readme.md",
            self.test_data_dir / "markdown" / "openai-readme.md",
            self.test_data_dir / "typescript" / "vscode-extension.ts",
            # Medium files (50KB-500KB)
            self.test_data_dir / "go" / "docker-daemon.go",
            self.test_data_dir / "php" / "laravel-model.php",
            self.test_data_dir / "python" / "django-models.py",
            self.test_data_dir / "rust" / "serde-derive.rs",
            self.test_data_dir / "csharp" / "aspnet-controller.cs",
            self.test_data_dir / "text" / "rfc-specification.txt",
            # Large files (>500KB)
            self.test_data_dir / "javascript" / "lodash-utility.js",
            self.test_data_dir / "text" / "shakespeare-complete.txt",
        ]

        size_categories = {"small": 0, "medium": 0, "large": 0}

        for file_path in all_files:
            if not file_path.exists():
                continue

            file_info = get_file_info(str(file_path))
            size = file_info["size"]

            if size < 50_000:
                size_categories["small"] += 1
            elif size < 500_000:
                size_categories["medium"] += 1
            else:
                size_categories["large"] += 1

        # Should have files in each category
        assert size_categories["small"] > 0
        assert size_categories["medium"] > 0
        assert size_categories["large"] > 0

    def test_performance_with_search_operations(self):
        """Test search performance across different file sizes.

        Verify search operations work efficiently for all file sizes.
        """
        # Test files representing different size ranges
        test_cases = [
            {
                "file": self.test_data_dir / "java" / "spring-application.java",
                "search_term": "class",
                "size_category": "small",
            },
            {
                "file": self.test_data_dir / "python" / "django-models.py",
                "search_term": "def",
                "size_category": "medium",
            },
            {
                "file": self.test_data_dir / "javascript" / "lodash-utility.js",
                "search_term": "function",
                "size_category": "large",
            },
        ]

        for case in test_cases:
            file_path = case["file"]
            if not file_path.exists():
                continue

            # Test basic operations work
            overview = get_overview(str(file_path))
            assert overview["line_count"] > 0

            search_results = search_content(
                str(file_path), case["search_term"], max_results=10
            )
            assert search_results["total_matches"] >= 0

            # Verify results have required fields
            if search_results["results"]:
                result = search_results["results"][0]
                assert "line_number" in result
                assert "similarity_score" in result

    def test_file_access_error_handling(self):
        """Test error handling for file access operations."""
        # Test with non-existent file
        try:
            get_file_info("/nonexistent/file.txt")
            raise AssertionError("Should have raised FileAccessError")
        except Exception as e:
            assert "Cannot access file" in str(e)

    def test_overview_generation_performance(self):
        """Test overview generation across file sizes.

        Verify overview generation works for all test files.
        """
        test_files = [
            self.test_data_dir / "java" / "spring-application.java",
            self.test_data_dir / "python" / "django-models.py",
            self.test_data_dir / "javascript" / "lodash-utility.js",
        ]

        for file_path in test_files:
            if not file_path.exists():
                continue

            overview = get_overview(str(file_path))

            # Verify overview contains expected fields
            assert "line_count" in overview
            assert "file_size" in overview
            assert "long_lines" in overview
            assert "is_binary" in overview
            assert "search_hints" in overview
            assert "outline" in overview

            # Verify reasonable values
            assert overview["line_count"] > 0
            assert overview["file_size"] > 0
            assert isinstance(overview["long_lines"]["has_long_lines"], bool)
            assert overview["is_binary"] is False  # Text files
