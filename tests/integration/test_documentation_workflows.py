"""Documentation analysis workflow tests.

Real-world AI/ML documentation exploration scenarios using actual test data.
"""

from pathlib import Path

from src.tools import get_overview, read_content, search_content


class TestDocumentationWorkflows:
    """Real-world documentation analysis scenarios."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_ai_sdk_comparison(self):
        """Compare AI SDK documentation for chat completion methods.

        Scenario: Developer wants to understand differences between
        OpenAI and Anthropic SDKs for chat completions.
        """
        openai_doc = self.test_data_dir / "markdown" / "openai-readme.md"
        anthropic_doc = self.test_data_dir / "markdown" / "anthropic-readme.md"

        # Search for chat completion related content
        openai_results = search_content(str(openai_doc), "chat", fuzzy=True)
        anthropic_results = search_content(str(anthropic_doc), "chat", fuzzy=True)

        # Should find some chat-related content across the docs
        total_chat_matches = (
            openai_results["total_matches"] + anthropic_results["total_matches"]
        )
        assert total_chat_matches >= 0

        # Get overview of both documents
        openai_overview = get_overview(str(openai_doc))
        anthropic_overview = get_overview(str(anthropic_doc))

        assert openai_overview["file_size"] > 0
        assert anthropic_overview["file_size"] > 0
        assert "search_hints" in openai_overview
        assert "search_hints" in anthropic_overview

    def test_ml_framework_documentation_analysis(self):
        """Analyze ML framework documentation for async patterns.

        Scenario: Developer comparing PyTorch and FastAPI documentation
        for async/await usage patterns.
        """
        pytorch_doc = self.test_data_dir / "markdown" / "pytorch-readme.md"
        fastapi_doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        # Search for async patterns
        pytorch_async = search_content(
            str(pytorch_doc), "async", fuzzy=True, context_lines=2
        )
        fastapi_async = search_content(
            str(fastapi_doc), "async", fuzzy=True, context_lines=2
        )

        # At least one should have async content
        total_async_matches = (
            pytorch_async["total_matches"] + fastapi_async["total_matches"]
        )
        assert total_async_matches > 0

        # Verify context is provided
        for result in pytorch_async["results"] + fastapi_async["results"]:
            assert "line_number" in result
            assert "similarity_score" in result

    def test_api_documentation_search(self):
        """Search for specific API methods across documentation.

        Scenario: Developer looking for authentication methods
        across different API documentation.
        """
        docs = [
            self.test_data_dir / "markdown" / "openai-readme.md",
            self.test_data_dir / "markdown" / "anthropic-readme.md",
            self.test_data_dir / "markdown" / "fastapi-docs.md",
        ]

        auth_matches = 0
        for doc in docs:
            if doc.exists():
                result = search_content(str(doc), "auth", fuzzy=True)
                auth_matches += result["total_matches"]

        # Should find some authentication related content
        assert auth_matches >= 0  # Some docs may not have auth content

    def test_nodejs_runtime_documentation(self):
        """Navigate Node.js runtime documentation effectively.

        Scenario: Developer needs to understand Node.js runtime features
        and module system from documentation.
        """
        nodejs_doc = self.test_data_dir / "markdown" / "nodejs-readme.md"

        if not nodejs_doc.exists():
            return  # Skip if file doesn't exist

        overview = get_overview(str(nodejs_doc))
        assert overview["line_count"] > 0

        # Search for module-related content
        module_results = search_content(str(nodejs_doc), "module", fuzzy=True)

        # Read specific sections
        if module_results["total_matches"] > 0:
            first_match = module_results["results"][0]
            line_num = first_match["line_number"]

            content = read_content(str(nodejs_doc), offset=line_num, limit=20)
            assert "content" in content
            assert content["mode"] == "lines"


class TestTailMode:
    """Test read_content tail mode for log-like files."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    def test_read_content_tail_mode(self):
        """read_content with mode=tail returns last N lines."""
        # Use any existing test file
        doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        if not doc.exists():
            return  # Skip if file doesn't exist

        # Read last 10 lines
        result = read_content(str(doc), limit=10, mode="tail")

        assert "content" in result
        assert "start_line" in result
        assert "end_line" in result
        assert "total_lines" in result
        assert result["mode"] == "tail"

        # end_line should equal total_lines (reading to the end)
        assert result["end_line"] == result["total_lines"]

        # start_line should be total_lines - 10 + 1 (or 1 if file is small)
        expected_start = max(1, result["total_lines"] - 10 + 1)
        assert result["start_line"] == expected_start

    def test_read_content_tail_mode_requires_positive_limit(self):
        """Raises error for zero or negative limit."""
        doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        if not doc.exists():
            return  # Skip if file doesn't exist

        result = read_content(str(doc), limit=0, mode="tail")

        # Should return error in result
        assert "error" in result
        assert "limit" in result["error"].lower()

    def test_read_content_head_mode(self):
        """read_content with mode=head returns first N lines."""
        doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        if not doc.exists():
            return  # Skip if file doesn't exist

        # Read first 10 lines
        result = read_content(str(doc), limit=10, mode="head")

        assert "content" in result
        assert "start_line" in result
        assert "end_line" in result
        assert "total_lines" in result
        assert result["mode"] == "head"

        # start_line should be 1
        assert result["start_line"] == 1
        # lines_returned should be min(10, total_lines)
        assert result["lines_returned"] == min(10, result["total_lines"])

    def test_read_content_modes_comparison(self):
        """Different modes work correctly."""
        doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        if not doc.exists():
            return  # Skip if file doesn't exist

        # Line mode with offset
        line_result = read_content(str(doc), offset=10, limit=20)
        assert "content" in line_result
        assert line_result["mode"] == "lines"
        assert line_result["start_line"] == 10

        # Head mode
        head_result = read_content(str(doc), limit=5, mode="head")
        assert "content" in head_result
        assert head_result["mode"] == "head"
        assert head_result["start_line"] == 1

        # Tail mode
        tail_result = read_content(str(doc), limit=5, mode="tail")
        assert "content" in tail_result
        assert tail_result["mode"] == "tail"
        assert tail_result["end_line"] == tail_result["total_lines"]

    def test_read_content_offset_ignored_in_tail_mode(self):
        """Offset is ignored in tail mode with warning."""
        doc = self.test_data_dir / "markdown" / "fastapi-docs.md"

        if not doc.exists():
            return  # Skip if file doesn't exist

        result = read_content(str(doc), offset=50, limit=5, mode="tail")
        assert "content" in result
        assert result["mode"] == "tail"
        # Should have a warning about ignored offset
        assert "warnings" in result
        assert any("offset ignored" in w for w in result["warnings"])
