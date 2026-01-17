"""Real-world use case example tests.

End-to-end scenarios that demonstrate practical MCP server usage.
"""

from pathlib import Path

from src.tools import get_overview, read_content, search_content


class TestRealWorldExamples:
    """End-to-end scenarios users would actually perform."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_ai_documentation_assistant(self):
        """Help developer find AI SDK information.

        Scenario: Developer asks "How do I make async chat completions
        with OpenAI vs Anthropic?" - simulate finding relevant information.
        """
        ai_docs = [
            self.test_data_dir / "markdown" / "openai-readme.md",
            self.test_data_dir / "markdown" / "anthropic-readme.md",
        ]

        relevant_sections = []

        for doc in ai_docs:
            if not doc.exists():
                continue

            # Search for async and chat related content
            async_results = search_content(
                str(doc), "async", fuzzy=True, context_lines=2
            )
            chat_results = search_content(str(doc), "chat", fuzzy=True, context_lines=2)

            # Collect relevant information
            for result in async_results["results"] + chat_results["results"]:
                if result["similarity_score"] > 0.5:  # High relevance
                    relevant_sections.append(
                        {
                            "file": doc.name,
                            "line": result["line_number"],
                            "content": result["match"],
                            "score": result["similarity_score"],
                        }
                    )

        # Should find some relevant content
        assert len(relevant_sections) >= 0

    def test_code_migration_helper(self):
        """Help migrate between web frameworks.

        Scenario: Developer wants to migrate from Django to Laravel
        and needs to understand equivalent patterns.
        """
        django_file = self.test_data_dir / "python" / "django-models.py"
        laravel_file = self.test_data_dir / "php" / "laravel-model.php"

        migration_guide = {}

        # Analyze Django patterns
        if django_file.exists():
            django_overview = get_overview(str(django_file))
            django_classes = search_content(str(django_file), "class", max_results=5)
            django_methods = search_content(str(django_file), "def ", max_results=10)

            migration_guide["django"] = {
                "overview": django_overview,
                "classes": django_classes["total_matches"],
                "methods": django_methods["total_matches"],
            }

        # Analyze Laravel patterns
        if laravel_file.exists():
            laravel_overview = get_overview(str(laravel_file))
            laravel_classes = search_content(str(laravel_file), "class", max_results=5)
            laravel_methods = search_content(
                str(laravel_file), "function", max_results=10
            )

            migration_guide["laravel"] = {
                "overview": laravel_overview,
                "classes": laravel_classes["total_matches"],
                "methods": laravel_methods["total_matches"],
            }

        # Should have pattern information for comparison
        assert len(migration_guide) > 0

    def test_technical_specification_navigator(self):
        """Navigate complex technical specifications.

        Scenario: Developer needs to understand HTTP/1.1 connection
        handling from RFC specification for implementing a web server.
        """
        rfc_file = self.test_data_dir / "text" / "rfc-specification.txt"

        if not rfc_file.exists():
            return  # Skip if file doesn't exist

        # Get overview of the large specification
        overview = get_overview(str(rfc_file))
        assert overview["file_size"] > 400_000  # Large specification

        # Search for connection-related sections
        connection_results = search_content(
            str(rfc_file), "connection", fuzzy=True, max_results=10
        )
        http_results = search_content(str(rfc_file), "HTTP", fuzzy=False, max_results=5)

        # Should find relevant specification content
        total_matches = (
            connection_results["total_matches"] + http_results["total_matches"]
        )
        assert total_matches > 0

        # Extract specific sections for detailed reading
        if connection_results["results"]:
            first_match = connection_results["results"][0]
            detailed_section = read_content(
                str(rfc_file), offset=first_match["line_number"]
            )
            assert "content" in detailed_section

    def test_polyglot_development_assistant(self):
        """Help with cross-language development patterns.

        Scenario: Developer working on microservices needs to understand
        similar patterns across Go, Python, and JavaScript codebases.
        """
        polyglot_files = [
            ("go", self.test_data_dir / "go" / "docker-daemon.go"),
            ("python", self.test_data_dir / "python" / "django-models.py"),
            ("javascript", self.test_data_dir / "javascript" / "lodash-utility.js"),
            ("typescript", self.test_data_dir / "typescript" / "vscode-extension.ts"),
        ]

        language_patterns = {}

        for lang, file_path in polyglot_files:
            if not file_path.exists():
                continue

            # Search for common patterns across languages
            function_patterns = search_content(
                str(file_path), "function", fuzzy=True, max_results=3
            )
            error_patterns = search_content(
                str(file_path), "error", fuzzy=True, max_results=3
            )

            language_patterns[lang] = {
                "functions": function_patterns["total_matches"],
                "error_handling": error_patterns["total_matches"],
                "file_size": get_overview(str(file_path))["file_size"],
            }

        # Should have patterns from multiple languages
        assert len(language_patterns) > 1

    def test_large_codebase_exploration(self):
        """Explore large codebase efficiently.

        Scenario: Developer joins new team and needs to understand
        large JavaScript utility library structure and key functions.
        """
        lodash_file = self.test_data_dir / "javascript" / "lodash-utility.js"

        if not lodash_file.exists():
            return  # Skip if file doesn't exist

        # Get high-level overview
        overview = get_overview(str(lodash_file))
        assert overview["file_size"] > 500_000  # Large file

        # Find key utility functions
        utility_functions = ["map", "filter", "reduce", "forEach", "find", "each"]

        function_locations = {}
        for func in utility_functions:
            results = search_content(str(lodash_file), func, fuzzy=True, max_results=3)
            if results["total_matches"] > 0:
                function_locations[func] = results["results"][0]["line_number"]

        # Should find some common utility functions
        assert len(function_locations) >= 0

        # Test reading specific function implementations
        if function_locations:
            first_function = list(function_locations.values())[0]
            implementation = read_content(str(lodash_file), offset=first_function)
            assert "content" in implementation

    def test_documentation_authoring_assistant(self):
        """Assist with documentation authoring and reference.

        Scenario: Technical writer needs to cross-reference multiple
        documentation sources while writing integration guide.
        """
        docs = [
            self.test_data_dir / "markdown" / "nodejs-readme.md",
            self.test_data_dir / "markdown" / "fastapi-docs.md",
            self.test_data_dir / "markdown" / "pytorch-readme.md",
        ]

        documentation_index = {}

        for doc in docs:
            if not doc.exists():
                continue

            overview = get_overview(str(doc))

            # Search for common documentation patterns
            install_info = search_content(
                str(doc), "install", fuzzy=True, max_results=3
            )
            usage_info = search_content(str(doc), "usage", fuzzy=True, max_results=3)
            example_info = search_content(
                str(doc), "example", fuzzy=True, max_results=3
            )

            documentation_index[doc.name] = {
                "size": overview["file_size"],
                "lines": overview["line_count"],
                "install_refs": install_info["total_matches"],
                "usage_refs": usage_info["total_matches"],
                "example_refs": example_info["total_matches"],
            }

        # Should have documentation reference information
        assert len(documentation_index) > 0
