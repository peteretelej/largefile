# Tree-sitter Python Technical Reference

## Overview

Tree-sitter is a parser generator tool and incremental parsing library that builds concrete syntax trees (CSTs) for source code. It provides fast, robust parsing with error recovery and supports incremental parsing for efficient re-parsing of edited files.

## Core Components

### Language and Parser Setup

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Load language grammar
PY_LANGUAGE = Language(tspython.language())

# Create parser instance
parser = Parser(PY_LANGUAGE)
```

### Basic Parsing

```python
# Parse source code (requires bytes input)
source_code = """
def process_data(items):
    return [item.upper() for item in items if item]
"""

tree = parser.parse(bytes(source_code, "utf8"))
root_node = tree.root_node
```

### Tree Structure and Navigation

```python
# Node properties
node.type           # Node type (e.g., 'function_definition', 'identifier')
node.start_point    # (row, column) start position
node.end_point      # (row, column) end position
node.start_byte     # Byte offset start
node.end_byte       # Byte offset end
node.text           # Source text as bytes
node.children       # List of child nodes
node.parent         # Parent node

# Navigation methods
node.child(index)                    # Get child by index
node.child_by_field_name('name')     # Get child by field name
node.children_by_field_name('body')  # Get all children by field name
```

### Efficient Tree Traversal

```python
# Use TreeCursor for efficient traversal of large trees
cursor = tree.walk()

def traverse_tree(cursor):
    yield cursor.node

    if cursor.goto_first_child():
        yield from traverse_tree(cursor)
        while cursor.goto_next_sibling():
            yield from traverse_tree(cursor)
        cursor.goto_parent()

# Iterate through all nodes
for node in traverse_tree(cursor):
    print(f"{node.type}: {node.start_point}-{node.end_point}")
```

## Pattern Matching with Queries

Tree-sitter queries enable pattern-based code analysis using S-expression syntax.

### Query Syntax

```python
# Define query patterns
query = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params
  body: (block) @function.body)

(call
  function: (identifier) @call.name
  arguments: (argument_list) @call.args)

(import_statement
  name: (dotted_name) @import.module)
""")
```

### Capturing Matches

```python
# Get all captures
captures = query.captures(root_node)
# Returns: {"function.name": [node1, node2], "call.name": [node3], ...}

# Get structured matches
matches = query.matches(root_node)
# Returns: [(pattern_index, capture_dict), ...]

for pattern_index, capture_dict in matches:
    if "function.name" in capture_dict:
        func_name = capture_dict["function.name"][0].text.decode()
        print(f"Found function: {func_name}")
```

## Incremental Parsing

Tree-sitter excels at incremental parsing for handling file edits efficiently.

```python
# Original parsing
tree = parser.parse(original_source)

# Apply edit operations
tree.edit(
    start_byte=10,
    old_end_byte=15,
    new_end_byte=20,
    start_point=(1, 5),
    old_end_point=(1, 10),
    new_end_point=(1, 15)
)

# Reparse with previous tree for speed
new_tree = parser.parse(modified_source, tree)

# Get changed ranges
for range_obj in tree.changed_ranges(new_tree):
    print(f"Changed: {range_obj.start_point} to {range_obj.end_point}")
```

## Large File Handling Strategies

### Streaming Parse with Read Callable

```python
def create_read_callable(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()

    def read_func(byte_offset, point):
        if byte_offset >= len(content):
            return None
        return content[byte_offset:byte_offset + 1]

    return read_func

# Parse large files without loading entirely into memory
tree = parser.parse(create_read_callable("large_file.py"))
```

### Selective Processing

```python
def analyze_functions_only(root_node):
    """Extract only function definitions for analysis"""
    query = PY_LANGUAGE.query("(function_definition) @func")

    functions = []
    for match in query.matches(root_node):
        func_node = match[1]["func"][0]
        functions.append({
            'name': func_node.child_by_field_name('name').text.decode(),
            'start_line': func_node.start_point[0],
            'end_line': func_node.end_point[0],
            'body_node': func_node.child_by_field_name('body')
        })

    return functions
```

## Common Use Cases

### Code Analysis

- **AST-based diffing**: Compare semantic changes ignoring formatting
- **Symbol extraction**: Find all function/class definitions, imports
- **Dependency analysis**: Track function calls and module imports
- **Code metrics**: Calculate complexity, count constructs

### Code Transformation

- **Semantic search**: Find patterns across codebases
- **Refactoring**: Rename symbols, extract functions
- **Code generation**: Template-based code insertion
- **Linting**: Custom style and correctness checks

## Performance Considerations

1. **Reuse parsers**: Create parser instances once per language
2. **Use TreeCursor**: For deep tree traversal instead of recursive children access
3. **Incremental parsing**: Leverage edit operations for file modifications
4. **Query compilation**: Compile queries once, reuse for multiple trees
5. **Memory management**: Tree objects hold references to source bytes

## Error Handling

```python
# Tree-sitter provides error recovery
tree = parser.parse(malformed_source)

def find_errors(node):
    if node.type == "ERROR":
        print(f"Parse error at {node.start_point}: {node.text}")

    for child in node.children:
        find_errors(child)

find_errors(tree.root_node)
```

## Language Support

Install language-specific packages:

```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-rust
```

Available languages include Python, JavaScript/TypeScript, Rust, Go, C/C++, Java, and many others through the tree-sitter ecosystem.
