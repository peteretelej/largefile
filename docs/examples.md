# Largefile MCP Server Examples

This document provides examples of using the largefile MCP server for various file operations.

## Basic Tool Usage

### Getting File Overview

Get a hierarchical overview of a file structure:

```python
# Get overview of a Python file
result = get_overview("/path/to/file.py")
print(f"File has {result['line_count']} lines")
print(f"Contains long lines: {result['has_long_lines']}")
print("Outline:")
for item in result['outline']:
    print(f"  {item['type']}: {item['name']} (line {item['line_number']})")
```

Example output:
```
File has 150 lines
Contains long lines: True
Outline:
  import: import os
  import: from pathlib import Path
  function: def process_data()
  class: class DataProcessor
  function:   def __init__()
  function:   def process()
```

### Searching Content

Search for patterns with fuzzy matching:

```python
# Exact search
result = search_content("/path/to/file.py", "def process", fuzzy=False)

# Fuzzy search (default)
result = search_content("/path/to/file.py", "proces", fuzzy=True)

print(f"Found {result['total_matches']} matches")
for match in result['results']:
    print(f"Line {match['line_number']}: {match['match']}")
    print(f"Context: {match['semantic_context']}")
    print(f"Similarity: {match['similarity_score']}")
```

### Reading Content

Read semantic chunks instead of arbitrary line ranges:

```python
# Read by line number (semantic mode)
result = read_content("/path/to/file.py", 42, mode="semantic")
print(f"Content from lines {result['start_line']}-{result['end_line']}:")
print(result['content'])

# Read by pattern
result = read_content("/path/to/file.py", "class DataProcessor", mode="semantic")
print(f"Found at line {result['match_line']}:")
print(result['content'])
```

### Editing Content

Primary editing method using search/replace blocks:

```python
# Preview mode (default)
result = edit_content(
    "/path/to/file.py",
    search_text="old_function_name",
    replace_text="new_function_name",
    preview=True
)
print("Preview:")
print(result['preview'])

# Apply changes
result = edit_content(
    "/path/to/file.py", 
    search_text="old_function_name",
    replace_text="new_function_name",
    preview=False
)
print(f"Backup created: {result['backup_created']}")
print(f"Changed {result['changes_made']} occurrences")
```

## Environment Configuration

Configure performance thresholds via environment variables:

```bash
# File access thresholds
export LARGEFILE_MEMORY_THRESHOLD_MB=50    # Load files < 50MB into memory
export LARGEFILE_MMAP_THRESHOLD_MB=500     # Use mmap for files < 500MB
export LARGEFILE_MAX_LINE_LENGTH=1000      # Trigger truncation at 1000 chars
export LARGEFILE_TRUNCATE_LENGTH=500       # Display length for long lines

# Search settings
export LARGEFILE_FUZZY_THRESHOLD=0.8       # Minimum fuzzy match similarity
export LARGEFILE_MAX_SEARCH_RESULTS=20     # Default result limit
export LARGEFILE_CONTEXT_LINES=2           # Default context window

# Tree-sitter settings
export LARGEFILE_ENABLE_TREE_SITTER=true   # Enable semantic features
export LARGEFILE_TREE_SITTER_TIMEOUT=5     # Max seconds for AST parsing
```

## Common Workflows

### Code Analysis Workflow

```python
# 1. Get overview to understand file structure
overview = get_overview("/path/to/large_file.py")
print(f"File structure ({overview['line_count']} lines):")
for hint in overview['search_hints']:
    matches = search_content("/path/to/large_file.py", hint)
    print(f"  {hint}: {matches['total_matches']} matches")

# 2. Examine specific functions
function_matches = search_content("/path/to/large_file.py", "def ")
for match in function_matches['results'][:5]:  # First 5 functions
    content = read_content("/path/to/large_file.py", match['line_number'], mode="semantic")
    print(f"Function at line {match['line_number']}:")
    print(content['content'][:200] + "...")
```

### Refactoring Workflow

```python
# 1. Find all usages of old name
old_name = "legacy_function"
matches = search_content("/path/to/file.py", old_name, fuzzy=False)
print(f"Found {matches['total_matches']} usages to refactor")

# 2. Preview each change
for match in matches['results']:
    context = read_content("/path/to/file.py", match['line_number'])
    print(f"Usage at line {match['line_number']}:")
    print(context['content'])
    
    # Preview the change
    preview = edit_content(
        "/path/to/file.py",
        old_name,
        "new_function_name",
        preview=True
    )
    print("Would change to:")
    print(preview['preview'])

# 3. Apply changes
result = edit_content(
    "/path/to/file.py",
    old_name, 
    "new_function_name",
    preview=False
)
print(f"Refactoring complete. Backup: {result['backup_created']}")
```

### Large File Handling

For files larger than memory thresholds, the system automatically uses appropriate strategies:

```python
# This automatically uses memory mapping or streaming based on file size
huge_file = "/path/to/huge_file.py"  # > 50MB

# Overview still works efficiently
overview = get_overview(huge_file)
print(f"Large file: {overview['line_count']} lines")

# Search uses chunked processing
matches = search_content(huge_file, "pattern", max_results=10)
print(f"Found {matches['total_matches']} matches in large file")

# Reading uses semantic chunking to avoid loading entire file
content = read_content(huge_file, 1000, mode="semantic")
print("Semantic chunk around line 1000:")
print(content['content'])
```

## Error Handling

The system provides clear error messages and suggestions:

```python
try:
    result = edit_content("/nonexistent/file.py", "old", "new")
except Exception as e:
    print(f"Error: {e}")
    # Error: File access failed: Cannot access file /nonexistent/file.py
    # Suggestion: Check file path and permissions

# Graceful degradation when tree-sitter unavailable
result = get_overview("/path/to/file.unknown_extension")
# Falls back to text-based analysis automatically
```

## Performance Considerations

- **Small files (< 50MB)**: Loaded into memory for fastest access
- **Medium files (50MB - 500MB)**: Memory-mapped for efficient access
- **Large files (> 500MB)**: Streaming access with chunked processing
- **Long lines (> 1000 chars)**: Automatically truncated for display
- **Tree-sitter parsing**: Enhances semantic features when available

## Best Practices

1. **Use semantic mode for reading**: Gets complete functions/classes instead of arbitrary line ranges
2. **Enable fuzzy matching**: Handles whitespace variations in search/replace
3. **Preview before editing**: Always preview changes before applying
4. **Use search hints**: File overview provides optimized search patterns
5. **Configure thresholds**: Adjust environment variables for your use case