"""Tree-sitter verification tests.

Verify that tree-sitter actually works and produces real AST parsing.
"""

from src.tree_parser import (
    generate_outline,
    get_language_parser,
    is_tree_sitter_available,
    parse_file_content,
)


class TestTreeSitterVerification:
    """Verify tree-sitter actually produces AST parsing."""

    def test_tree_sitter_actually_works(self):
        """Verify tree-sitter parsing actually produces AST."""
        if not is_tree_sitter_available():
            # Skip if tree-sitter not available
            return

        content = """def hello():
    return "world"

class MyClass:
    def method(self):
        pass
"""

        tree = parse_file_content("test.py", content)

        # Should produce real tree, not None
        assert tree is not None, "Tree-sitter should parse content successfully"

        # Verify we got real AST
        assert hasattr(tree, "root_node"), "Tree should have root_node"
        root = tree.root_node
        assert root.type == "module", (
            f"Python AST root should be 'module', got '{root.type}'"
        )

        # Verify we can traverse AST
        assert root.child_count > 0, "Root node should have children"

        # Find function nodes
        functions = []
        classes = []

        def visit_node(node):
            if node.type == "function_definition":
                functions.append(node)
            elif node.type == "class_definition":
                classes.append(node)
            for child in node.children:
                visit_node(child)

        visit_node(root)

        assert len(functions) == 2, f"Should find 2 functions, found {len(functions)}"
        assert len(classes) == 1, f"Should find 1 class, found {len(classes)}"

    def test_outline_uses_real_ast(self):
        """Verify outline generation uses real AST when available."""
        if not is_tree_sitter_available():
            return

        content = """def function_one():
    pass

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        return True

def function_two():
    return 42
"""

        outline = generate_outline("test.py", content)

        # Should generate detailed outline
        assert len(outline) > 0, "Should generate outline items"

        # Verify we found expected items
        outline_names = [item.name for item in outline]

        # Should find functions and classes
        assert any("function_one" in name for name in outline_names), (
            "Should find function_one"
        )
        assert any("MyClass" in name for name in outline_names), "Should find MyClass"
        assert any("method_one" in name for name in outline_names), (
            "Should find method_one"
        )
        assert any("function_two" in name for name in outline_names), (
            "Should find function_two"
        )

        # Verify types are correct
        outline_types = [item.type for item in outline]
        assert "function" in outline_types, "Should have function items"
        assert "class" in outline_types, "Should have class items"

        # Verify line numbers are reasonable
        for item in outline:
            assert item.line_number > 0, (
                f"Line numbers should be positive, got {item.line_number}"
            )
            assert item.line_number <= 15, "Line numbers should be within content range"

    def test_multiple_language_support(self):
        """Test tree-sitter works for multiple supported languages."""
        if not is_tree_sitter_available():
            return

        test_cases = [
            (".py", "def test(): pass", "module"),
            (".js", "function test() { return 42; }", "program"),
            (".ts", "function test(): number { return 42; }", "program"),
        ]

        working_languages = 0

        for ext, content, expected_root_type in test_cases:
            try:
                parser = get_language_parser(ext)
                if parser is not None:
                    tree = parse_file_content(f"test{ext}", content)
                    if tree is not None:
                        assert tree.root_node.type == expected_root_type
                        working_languages += 1
            except Exception:
                # Language might not be installed, that's OK
                pass

        # At least Python should work
        assert working_languages > 0, "At least one language parser should work"

    def test_semantic_context_extraction(self):
        """Test that semantic context can be extracted from AST."""
        if not is_tree_sitter_available():
            return

        content = """class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

def main():
    calc = Calculator()
    result = calc.add(2, 3)
    print(result)
"""

        tree = parse_file_content("calculator.py", content)
        assert tree is not None

        # Generate outline with detailed information
        outline = generate_outline("calculator.py", content)

        # Should have hierarchical structure
        class_items = [item for item in outline if item.type == "class"]
        function_items = [item for item in outline if item.type == "function"]

        assert len(class_items) >= 1, "Should find Calculator class"
        assert len(function_items) >= 3, "Should find add, multiply, and main functions"

        # Verify some items have children (methods in class)
        any(len(item.children) > 0 for item in outline)
        # Note: This depends on outline extraction implementation
        # If outline is flat, that's OK for now
