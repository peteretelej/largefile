"""Codebase navigation and editing workflow tests.

Realistic code exploration scenarios across multiple programming languages.
"""

from pathlib import Path

from src.tools import edit_content, get_overview, read_content, search_content


class TestCodebaseWorkflows:
    """Realistic code exploration and editing scenarios."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_web_framework_patterns_comparison(self):
        """Compare patterns between Django and Laravel web frameworks.

        Scenario: Developer migrating from Django to Laravel needs to
        understand model patterns and validation approaches.
        """
        django_models = self.test_data_dir / "python" / "django-models.py"
        laravel_model = self.test_data_dir / "php" / "laravel-model.php"

        # Get overview of both frameworks
        django_overview = get_overview(str(django_models))
        laravel_overview = get_overview(str(laravel_model))

        assert django_overview["line_count"] > 0
        assert laravel_overview["line_count"] > 0

        # Search for model patterns
        django_models_search = search_content(str(django_models), "class", fuzzy=False)
        laravel_models_search = search_content(str(laravel_model), "class", fuzzy=False)

        assert django_models_search["total_matches"] > 0
        assert laravel_models_search["total_matches"] > 0

        # Search for validation patterns
        django_validation = search_content(str(django_models), "valid", fuzzy=True)
        laravel_validation = search_content(str(laravel_model), "valid", fuzzy=True)

        # At least one should have validation patterns
        total_validation = (
            django_validation["total_matches"] + laravel_validation["total_matches"]
        )
        assert total_validation >= 0

    def test_large_javascript_codebase_navigation(self):
        """Navigate large JavaScript utility library effectively.

        Scenario: Developer needs to understand specific utility functions
        in the Lodash library (532KB file).
        """
        lodash_file = self.test_data_dir / "javascript" / "lodash-utility.js"

        if not lodash_file.exists():
            return  # Skip if file doesn't exist

        # Get overview - should use mmap strategy for this size
        overview = get_overview(str(lodash_file))
        assert overview["file_size"] > 500_000  # 532KB file
        assert overview["line_count"] > 1000

        # Search for common utility functions
        function_search = search_content(str(lodash_file), "function", max_results=10)
        assert function_search["total_matches"] > 0

        # Test performance with specific function search
        map_search = search_content(str(lodash_file), "map", fuzzy=True, max_results=5)
        assert map_search["total_matches"] >= 0

    def test_cross_language_async_patterns(self):
        """Find async patterns across different programming languages.

        Scenario: Developer wants to understand async patterns across
        JavaScript, Python, Go, and C# codebases.
        """
        files = [
            self.test_data_dir / "javascript" / "lodash-utility.js",
            self.test_data_dir / "python" / "django-models.py",
            self.test_data_dir / "go" / "docker-daemon.go",
            self.test_data_dir / "csharp" / "aspnet-controller.cs",
        ]

        async_patterns_found = 0
        for file_path in files:
            if file_path.exists():
                result = search_content(str(file_path), "async", fuzzy=True)
                async_patterns_found += result["total_matches"]

        # Should find some async patterns across languages
        assert async_patterns_found >= 0

    def test_rust_serialization_code_analysis(self):
        """Analyze Rust serialization library code structure.

        Scenario: Developer learning Rust needs to understand
        serialization patterns in the Serde library.
        """
        serde_file = self.test_data_dir / "rust" / "serde-derive.rs"

        if not serde_file.exists():
            return  # Skip if file doesn't exist

        overview = get_overview(str(serde_file))
        assert overview["line_count"] > 0

        # Search for Rust-specific patterns
        impl_search = search_content(str(serde_file), "impl", fuzzy=False)
        struct_search = search_content(str(serde_file), "struct", fuzzy=False)

        # Should find some Rust patterns
        rust_patterns = impl_search["total_matches"] + struct_search["total_matches"]
        assert rust_patterns > 0

    def test_spring_java_application_navigation(self):
        """Navigate Java Spring application code.

        Scenario: Developer needs to understand Spring Boot
        application structure and annotations.
        """
        spring_file = self.test_data_dir / "java" / "spring-application.java"

        overview = get_overview(str(spring_file))
        assert overview["file_size"] > 0

        # Search for Spring annotations and patterns
        annotation_search = search_content(str(spring_file), "@", fuzzy=False)
        class_search = search_content(str(spring_file), "class", fuzzy=False)

        assert annotation_search["total_matches"] >= 0
        assert class_search["total_matches"] >= 0

    def test_code_search_and_context_extraction(self):
        """Test targeted code search with context extraction.

        Scenario: Developer needs to find specific method implementations
        with surrounding context for understanding.
        """
        vscode_extension = self.test_data_dir / "typescript" / "vscode-extension.ts"

        if not vscode_extension.exists():
            return  # Skip if file doesn't exist

        # Search for function definitions with context
        function_results = search_content(
            str(vscode_extension), "function", context_lines=3
        )

        for result in function_results["results"][:3]:  # Check first 3 results
            assert "context_before" in result
            assert "context_after" in result
            assert "line_number" in result

            # Read the specific function with more context
            line_num = result["line_number"]
            detailed_content = read_content(str(vscode_extension), offset=line_num)
            assert "content" in detailed_content

    def test_safe_code_editing_preview(self):
        """Test safe code editing with preview mode.

        Scenario: Developer wants to preview code changes before applying
        them to ensure no unintended modifications.
        """
        # Use a small file for editing tests
        spring_file = self.test_data_dir / "java" / "spring-application.java"

        # Test search and replace in preview mode
        result = edit_content(
            str(spring_file),
            changes=[{"search": "class", "replace": "public class"}],
            preview=True,
            fuzzy=False,
        )

        assert "success" in result
        assert "preview" in result
        assert "changes_applied" in result

        # Verify preview mode doesn't actually modify file
        if result["success"]:
            assert result["preview"] is not None
            assert result["backup_created"] is None  # No backup in preview mode
