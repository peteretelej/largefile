"""Tree-sitter integration for semantic analysis and AST parsing."""

from pathlib import Path
from typing import Any

from .config import config
from .data_models import OutlineItem
from .exceptions import TreeSitterError

# Language mappings for supported file extensions
SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
}


def is_tree_sitter_available() -> bool:
    """Check if tree-sitter is available and enabled."""
    if not config.enable_tree_sitter:
        return False

    try:
        import tree_sitter  # noqa: F401

        return True
    except ImportError:
        return False


def get_language_parser(file_extension: str) -> Any | None:
    """Get tree-sitter parser for a file extension."""
    if not is_tree_sitter_available():
        return None

    language_name = SUPPORTED_LANGUAGES.get(file_extension.lower())
    if not language_name:
        return None

    try:
        import tree_sitter

        # Import the specific language module and get language capsule
        language_capsule = None
        if language_name == "python":
            import tree_sitter_python

            language_capsule = tree_sitter_python.language()
        elif language_name == "javascript":
            import tree_sitter_javascript

            language_capsule = tree_sitter_javascript.language()
        elif language_name == "typescript":
            import tree_sitter_typescript

            language_capsule = tree_sitter_typescript.language_typescript()
        elif language_name == "rust":
            import tree_sitter_rust

            language_capsule = tree_sitter_rust.language()
        elif language_name == "go":
            import tree_sitter_go

            language_capsule = tree_sitter_go.language()
        else:
            return None

        # Create Language object from capsule and parser
        language = tree_sitter.Language(language_capsule)
        parser = tree_sitter.Parser(language)
        return parser

    except ImportError as e:
        raise TreeSitterError(
            f"Language parser not available for {language_name}"
        ) from e
    except Exception as e:
        raise TreeSitterError(
            f"Failed to create parser for {language_name}: {e}"
        ) from e


def parse_file_content(file_path: str, content: str) -> Any | None:
    """Parse file content with tree-sitter and return AST."""
    file_extension = Path(file_path).suffix
    parser = get_language_parser(file_extension)

    if not parser:
        return None

    try:
        # Parse the content
        tree = parser.parse(bytes(content, "utf-8"))
        return tree
    except Exception as e:
        raise TreeSitterError(f"Failed to parse {file_path}: {e}") from e


def extract_semantic_context(tree: Any, line_number: int) -> str:
    """Extract semantic context for a given line number."""
    if not tree:
        return f"Line {line_number}"

    try:
        # Convert to 0-based indexing for tree-sitter
        target_line = line_number - 1

        # Find the node that contains this line
        root_node = tree.root_node
        containing_node = find_node_at_line(root_node, target_line)

        if containing_node:
            context_parts = []

            # Walk up the tree to build context
            current_node = containing_node
            while current_node and current_node != root_node:
                node_context = get_node_context(current_node)
                if node_context:
                    context_parts.append(node_context)
                current_node = current_node.parent

            if context_parts:
                return " → ".join(reversed(context_parts))

        return f"Line {line_number}"

    except Exception:
        # Fall back to simple line context
        return f"Line {line_number}"


def find_node_at_line(node: Any, target_line: int) -> Any | None:
    """Find the most specific node that contains the target line."""
    if not node:
        return None

    # Check if this node contains the target line
    if node.start_point[0] <= target_line <= node.end_point[0]:
        # Check children first (more specific)
        for child in node.children:
            child_result = find_node_at_line(child, target_line)
            if child_result:
                return child_result

        # If no child contains it, this node is the best match
        return node

    return None


def get_node_context(node: Any) -> str | None:
    """Get a human-readable context description for a node."""
    if not node:
        return None

    node_type = node.type

    # Handle different node types
    if node_type == "function_definition":
        # Try to get function name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break

        if name_node:
            return f"function {name_node.text.decode('utf-8')}()"
        return "function"

    elif node_type == "class_definition":
        # Try to get class name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break

        if name_node:
            return f"class {name_node.text.decode('utf-8')}"
        return "class"

    elif node_type == "method_definition":
        # Try to get method name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break

        if name_node:
            return f"method {name_node.text.decode('utf-8')}()"
        return "method"

    elif node_type in ["if_statement", "if"]:
        return "if statement"

    elif node_type in ["for_statement", "for"]:
        return "for loop"

    elif node_type in ["while_statement", "while"]:
        return "while loop"

    elif node_type == "try_statement":
        return "try block"

    elif node_type == "except_clause":
        return "except block"

    elif node_type == "with_statement":
        return "with block"

    elif node_type in ["struct_item", "struct"]:
        return "struct"

    elif node_type in ["impl_item", "impl"]:
        return "impl block"

    elif node_type == "interface_declaration":
        return "interface"

    # Return None for nodes we don't have specific handling for
    return None


def generate_outline(file_path: str, content: str) -> list[OutlineItem]:
    """Generate hierarchical outline from AST."""
    tree = parse_file_content(file_path, content)

    if not tree:
        # Fall back to simple text-based outline
        return generate_simple_outline(file_path, content)

    try:
        outline_items: list[OutlineItem] = []
        root_node = tree.root_node

        # Extract top-level definitions
        extract_outline_items(root_node, outline_items, 0)

        return outline_items

    except Exception:
        # Fall back to simple outline on any error
        return generate_simple_outline(file_path, content)


def extract_outline_items(node: Any, items: list[OutlineItem], depth: int) -> None:
    """Recursively extract outline items from AST nodes."""
    if not node:
        return

    # Check if this node represents a definition we care about
    outline_item = create_outline_item_from_node(node, depth)
    if outline_item:
        # Look for child definitions
        child_items: list[OutlineItem] = []
        extract_outline_items(node, child_items, depth + 1)
        outline_item.children = child_items
        items.append(outline_item)
        return

    # If this node isn't a definition, check its children
    for child in node.children:
        extract_outline_items(child, items, depth)


def create_outline_item_from_node(node: Any, depth: int) -> OutlineItem | None:
    """Create an OutlineItem from an AST node if it represents a definition."""
    if not node:
        return None

    node_type = node.type

    # Map node types to outline items
    if node_type == "function_definition":
        name = extract_node_name(node, "identifier")
        if name:
            return OutlineItem(
                name=f"def {name}()",
                type="function",
                line_number=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                children=[],
                line_count=node.end_point[0] - node.start_point[0] + 1,
            )

    elif node_type == "class_definition":
        name = extract_node_name(node, "identifier")
        if name:
            return OutlineItem(
                name=f"class {name}",
                type="class",
                line_number=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                children=[],
                line_count=node.end_point[0] - node.start_point[0] + 1,
            )

    elif node_type == "method_definition":
        name = extract_node_name(node, "identifier")
        if name:
            return OutlineItem(
                name=f"  def {name}()",
                type="method",
                line_number=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                children=[],
                line_count=node.end_point[0] - node.start_point[0] + 1,
            )

    elif node_type == "import_statement" or node_type == "import_from_statement":
        # Get import text (first few characters)
        import_text = node.text.decode("utf-8")[:50]
        return OutlineItem(
            name=import_text,
            type="import",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            children=[],
            line_count=node.end_point[0] - node.start_point[0] + 1,
        )

    # Language-specific nodes
    elif node_type in ["struct_item", "struct"]:
        name = extract_node_name(node, "type_identifier") or extract_node_name(
            node, "identifier"
        )
        if name:
            return OutlineItem(
                name=f"struct {name}",
                type="struct",
                line_number=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                children=[],
                line_count=node.end_point[0] - node.start_point[0] + 1,
            )

    elif node_type in ["impl_item", "impl"]:
        return OutlineItem(
            name="impl block",
            type="impl",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            children=[],
            line_count=node.end_point[0] - node.start_point[0] + 1,
        )

    elif node_type == "interface_declaration":
        name = extract_node_name(node, "type_identifier") or extract_node_name(
            node, "identifier"
        )
        if name:
            return OutlineItem(
                name=f"interface {name}",
                type="interface",
                line_number=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                children=[],
                line_count=node.end_point[0] - node.start_point[0] + 1,
            )

    return None


def extract_node_name(node: Any, name_type: str = "identifier") -> str | None:
    """Extract the name from a node by looking for a child of the specified type."""
    if not node:
        return None

    for child in node.children:
        if child.type == name_type:
            try:
                return child.text.decode("utf-8")  # type: ignore
            except (UnicodeDecodeError, AttributeError):
                return None

    return None


def generate_simple_outline(file_path: str, content: str) -> list[OutlineItem]:
    """Generate a simple text-based outline when tree-sitter is not available."""
    file_extension = Path(file_path).suffix.lower()
    lines = content.splitlines()
    outline_items = []

    # Basic patterns for different languages
    if file_extension == ".py":
        patterns = [
            ("def ", "function"),
            ("class ", "class"),
            ("import ", "import"),
            ("from ", "import"),
        ]
    elif file_extension in [".js", ".ts", ".jsx", ".tsx"]:
        patterns = [
            ("function ", "function"),
            ("class ", "class"),
            ("const ", "const"),
            ("import ", "import"),
            ("export ", "export"),
        ]
    elif file_extension == ".go":
        patterns = [
            ("func ", "function"),
            ("type ", "type"),
            ("import ", "import"),
            ("package ", "package"),
        ]
    elif file_extension == ".rs":
        patterns = [
            ("fn ", "function"),
            ("struct ", "struct"),
            ("impl ", "impl"),
            ("use ", "import"),
        ]
    else:
        patterns = [
            ("TODO", "todo"),
            ("FIXME", "fixme"),
            ("NOTE", "note"),
            ("HACK", "hack"),
        ]

    for i, line in enumerate(lines[:50], 1):  # Limit to first 50 lines
        line_stripped = line.strip()
        for pattern, item_type in patterns:
            if line_stripped.startswith(pattern):
                outline_items.append(
                    OutlineItem(
                        name=line_stripped[:50] + "..."
                        if len(line_stripped) > 50
                        else line_stripped,
                        type=item_type,
                        line_number=i,
                        end_line=i,
                        children=[],
                        line_count=1,
                    )
                )
                break

    return outline_items


def get_semantic_chunk(
    file_path: str, content: str, target_line: int
) -> tuple[str, int, int]:
    """Get a semantic chunk of content around a target line."""
    tree = parse_file_content(file_path, content)

    if not tree:
        # Fall back to simple line-based chunk
        lines = content.splitlines()
        start_line = max(1, target_line - 10)
        end_line = min(len(lines), target_line + 10)
        chunk_lines = lines[start_line - 1 : end_line]
        return "\n".join(chunk_lines), start_line, end_line

    try:
        # Find the node containing the target line
        root_node = tree.root_node
        containing_node = find_node_at_line(
            root_node, target_line - 1
        )  # Convert to 0-based

        if containing_node:
            # Get the full node content
            start_line = containing_node.start_point[0] + 1
            end_line = containing_node.end_point[0] + 1

            # Add some context around the node
            lines = content.splitlines()
            context_start = max(1, start_line - 2)
            context_end = min(len(lines), end_line + 2)

            chunk_lines = lines[context_start - 1 : context_end]
            return "\n".join(chunk_lines), context_start, context_end

        # Fall back to simple chunk
        lines = content.splitlines()
        start_line = max(1, target_line - 10)
        end_line = min(len(lines), target_line + 10)
        chunk_lines = lines[start_line - 1 : end_line]
        return "\n".join(chunk_lines), start_line, end_line

    except Exception:
        # Fall back to simple chunk on any error
        lines = content.splitlines()
        start_line = max(1, target_line - 10)
        end_line = min(len(lines), target_line + 10)
        chunk_lines = lines[start_line - 1 : end_line]
        return "\n".join(chunk_lines), start_line, end_line
