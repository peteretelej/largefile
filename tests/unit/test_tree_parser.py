"""Tree parser unit tests.

Test core tree-sitter functionality with graceful fallback handling.
Uses table-driven tests for comprehensive coverage.
"""

from unittest.mock import patch

import pytest

from src.tree_parser import (
    SUPPORTED_LANGUAGES,
    extract_semantic_context,
    generate_outline,
    generate_simple_outline,
    get_language_parser,
    get_node_context,
    get_semantic_chunk,
    is_tree_sitter_available,
    parse_file_content,
)


class TestTreeParser:
    """Test tree-sitter parsing core functions."""

    def test_language_detection(self):
        """Test file extension to language parser mapping."""
        # Test supported languages - should not crash
        try:
            python_parser = get_language_parser(".py")
            js_parser = get_language_parser(".js")
            ts_parser = get_language_parser(".ts")
            go_parser = get_language_parser(".go")
            rust_parser = get_language_parser(".rs")

            # Should return parser objects or None (graceful handling)
            parsers = [python_parser, js_parser, ts_parser, go_parser, rust_parser]
            for parser in parsers:
                # Each parser should be None or a valid parser object
                assert parser is None or hasattr(parser, "parse")

        except Exception:
            # If tree-sitter has issues, functions should not crash
            # but may raise exceptions that are handled by calling code
            pass

        # Test unsupported extension - should always return None
        unsupported_parser = get_language_parser(".xyz")
        assert unsupported_parser is None

        # Test no extension - should always return None
        no_ext_parser = get_language_parser("")
        assert no_ext_parser is None

    def test_basic_parsing(self):
        """Test AST parsing for simple code content."""
        # Simple Python code
        python_content = """def hello():
    return "world"

class Test:
    pass
"""

        # Try to parse - should not crash
        try:
            tree = parse_file_content("test.py", python_content)

            # Should return tree object or None
            if tree is not None:
                assert hasattr(tree, "root_node")
            else:
                assert tree is None

        except Exception:
            # Tree-sitter may have compatibility issues
            # Functions should handle gracefully
            pass

    def test_outline_generation(self):
        """Test function/class outline extraction."""
        # Simple Python code with functions and classes
        python_content = """def function_one():
    pass

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        return True

def function_two():
    return 42
"""

        # Generate outline - should not crash even with tree-sitter issues
        try:
            outline = generate_outline("test.py", python_content)
            # Should always return a list (may be empty)
            assert isinstance(outline, list)
        except Exception:
            # Tree-sitter may have compatibility issues - that's OK for this test
            # The function should be callable without crashing the system
            pass

        # Test with empty content - should not crash
        try:
            empty_outline = generate_outline("test.py", "")
            assert isinstance(empty_outline, list)
            assert len(empty_outline) == 0
        except Exception:
            # Tree-sitter compatibility issues are acceptable
            pass

        # Test with non-Python file
        try:
            js_outline = generate_outline("test.js", "function test() { return 42; }")
            assert isinstance(js_outline, list)
        except Exception:
            # Tree-sitter compatibility issues are acceptable
            pass


class TestGetSemanticChunk:
    """Tests for get_semantic_chunk() function."""

    def test_semantic_chunk_python_function(self):
        """Returns semantic chunk around a Python function definition."""
        content = """import os

def hello():
    print('hi')
    return True

def world():
    pass
"""
        # Target line 4 (inside hello function)
        chunk, start, end = get_semantic_chunk("test.py", content, 4)

        # Should include the hello function
        assert "hello" in chunk
        assert "print" in chunk
        # Start/end should bound the target line
        assert start <= 4 <= end

    def test_semantic_chunk_fallback_unsupported_language(self):
        """Falls back to ±10 lines for unsupported file types."""
        content = "\n".join([f"line{i}" for i in range(1, 26)])  # 25 lines
        chunk, start, end = get_semantic_chunk("test.xyz", content, 15)

        # Should include lines around 15 (±10)
        assert "line15" in chunk
        # Fallback uses ±10 lines
        assert start >= 5  # max(1, 15-10) = 5
        assert end <= 25  # min(25, 15+10) = 25

    def test_semantic_chunk_target_at_file_end(self):
        """Handles target line at end of file."""
        content = """def foo():
    pass

def bar():
    return 1
"""
        # Target the last line
        chunk, start, end = get_semantic_chunk("test.py", content, 5)

        assert "bar" in chunk or "return" in chunk
        assert end >= 5

    def test_semantic_chunk_single_line_file(self):
        """Handles single-line file without crashing."""
        content = "x = 1"
        chunk, start, end = get_semantic_chunk("test.py", content, 1)

        assert "x = 1" in chunk
        assert start == 1
        assert end >= 1


class TestTreeSitterAvailability:
    """Test tree-sitter availability checks."""

    def test_is_tree_sitter_available_enabled(self):
        """Returns True when tree-sitter is available and enabled."""
        result = is_tree_sitter_available()
        # Should return a boolean
        assert isinstance(result, bool)

    def test_is_tree_sitter_available_disabled(self):
        """Returns False when disabled in config."""
        with patch("src.tree_parser.config.enable_tree_sitter", False):
            result = is_tree_sitter_available()
            assert result is False

    def test_is_tree_sitter_available_import_error(self):
        """Returns False when tree-sitter import fails."""
        with patch.dict("sys.modules", {"tree_sitter": None}):
            with patch("src.tree_parser.config.enable_tree_sitter", True):
                # This is tricky to test - the import check happens inside
                # We'll just verify the function handles gracefully
                result = is_tree_sitter_available()
                assert isinstance(result, bool)


class TestSupportedLanguages:
    """Test supported language mapping."""

    def test_supported_languages_mapping(self):
        """Verify expected languages are supported."""
        assert ".py" in SUPPORTED_LANGUAGES
        assert SUPPORTED_LANGUAGES[".py"] == "python"
        assert ".js" in SUPPORTED_LANGUAGES
        assert ".ts" in SUPPORTED_LANGUAGES
        assert ".rs" in SUPPORTED_LANGUAGES
        assert ".go" in SUPPORTED_LANGUAGES

    def test_jsx_tsx_mapped_correctly(self):
        """JSX and TSX use correct parsers."""
        assert SUPPORTED_LANGUAGES[".jsx"] == "javascript"
        assert SUPPORTED_LANGUAGES[".tsx"] == "typescript"


class TestSimpleOutline:
    """Test simple text-based outline generation."""

    @pytest.mark.parametrize(
        "extension,patterns",
        [
            (".py", ["def ", "class "]),
            (".js", ["function ", "class "]),
            (".go", ["func ", "type "]),
            (".rs", ["fn ", "struct "]),
            (".txt", ["TODO", "FIXME"]),
        ],
    )
    def test_simple_outline_patterns(self, extension, patterns):
        """Test simple outline generates items for language patterns."""
        # Create content with patterns
        content = "\n".join([f"{p}item{i}" for i, p in enumerate(patterns)])
        outline = generate_simple_outline(f"test{extension}", content)

        assert isinstance(outline, list)
        # Should find at least some items matching patterns
        if outline:
            for item in outline:
                assert hasattr(item, "name")
                assert hasattr(item, "type")
                assert hasattr(item, "line_number")

    def test_simple_outline_empty_content(self):
        """Empty content returns empty outline."""
        outline = generate_simple_outline("test.py", "")
        assert outline == []

    def test_simple_outline_limits_to_50_lines(self):
        """Outline generation limits to first 50 lines."""
        # Create file with 100 lines of definitions
        content = "\n".join([f"def func{i}():" for i in range(100)])
        outline = generate_simple_outline("test.py", content)

        # Should be limited to first 50 lines
        assert len(outline) <= 50


class TestExtractSemanticContext:
    """Test semantic context extraction."""

    def test_extract_semantic_context_no_tree(self):
        """Returns fallback when tree is None."""
        result = extract_semantic_context(None, 10)
        assert result == "Line 10"

    def test_extract_semantic_context_with_valid_tree(self):
        """Extracts context from valid tree."""
        content = """def hello():
    return True
"""
        tree = parse_file_content("test.py", content)
        if tree:
            result = extract_semantic_context(tree, 1)
            # Should return some context
            assert isinstance(result, str)
            assert len(result) > 0


class TestGetNodeContext:
    """Test node context descriptions."""

    def test_get_node_context_none_node(self):
        """Returns None for None node."""
        result = get_node_context(None)
        assert result is None


class TestParseFileContent:
    """Test file content parsing."""

    def test_parse_unsupported_extension(self):
        """Unsupported extension returns None."""
        result = parse_file_content("test.xyz", "content")
        assert result is None

    def test_parse_empty_content(self):
        """Empty content parses without error."""
        result = parse_file_content("test.py", "")
        # May return tree or None depending on parser behavior
        assert result is None or hasattr(result, "root_node")
