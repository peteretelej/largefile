# API Reference

Detailed documentation for the Largefile MCP Server tools.

## Overview

The Largefile MCP Server provides 4 core tools for working with large text files:

1. **get_overview** - File structure analysis
2. **search_content** - Pattern search with fuzzy matching  
3. **read_content** - Targeted content reading
4. **edit_content** - Search/replace editing

All tools require absolute file paths and support configurable text encoding.

## Tools

### get_overview

Analyze file structure with semantic outline and search hints.

**Signature:**
```python
def get_overview(
    absolute_file_path: str
) -> FileOverview
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)

**Returns:** `FileOverview` object with:
- `line_count`: Total lines in file
- `file_size`: File size in bytes
- `encoding`: Auto-detected file encoding
- `has_long_lines`: True if any line exceeds 1000 characters
- `outline`: Hierarchical structure via Tree-sitter (if supported)
- `search_hints`: Suggested search patterns for exploration

**Example:**
```python
overview = get_overview("/path/to/large_file.py")
print(f"File has {overview.line_count} lines")
for item in overview.outline:
    print(f"{item.type}: {item.name} at line {item.line_number}")
```

### search_content

Find patterns with fuzzy matching and semantic context.

**Signature:**
```python
def search_content(
    absolute_file_path: str,
    pattern: str,
    max_results: int = 20,
    context_lines: int = 2,
    fuzzy: bool = True
) -> List[SearchResult]
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `pattern`: Search pattern - exact text or fuzzy match target (required)
- `max_results`: Maximum number of results to return (default: 20)
- `context_lines`: Number of context lines before/after match (default: 2)
- `fuzzy`: Enable fuzzy matching with similarity scoring (default: True)

**Returns:** List of `SearchResult` objects with:
- `line_number`: Line where match was found
- `match`: The matching text (truncated if >500 chars)
- `context_before`: Lines before the match
- `context_after`: Lines after the match
- `semantic_context`: Tree-sitter context (e.g., "inside function foo()")
- `similarity_score`: Fuzzy match score (0.0-1.0, 1.0 for exact matches)
- `truncated`: True if match text was truncated for display

**Example:**
```python
# Exact search
results = search_content("/path/to/file.py", "def process_data", fuzzy=False)

# Fuzzy search for function names
results = search_content("/path/to/file.py", "proces_data", fuzzy=True)
for result in results:
    print(f"Line {result.line_number}: {result.match} (score: {result.similarity_score})")
```

### read_content

Read targeted content by line number or pattern with semantic chunking.

**Signature:**
```python
def read_content(
    absolute_file_path: str,
    target: Union[int, str],
    mode: str = "lines"
) -> str
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `target`: Line number (int) or search pattern (str) to locate content (required)
- `mode`: Reading mode - "lines", "semantic", or "function" (default: "lines")

**Reading Modes:**
- `"lines"`: Read specific line number or lines around pattern match
- `"semantic"`: Use Tree-sitter to read complete semantic blocks (functions, classes)
- `"function"`: Read entire function/method containing the target

**Returns:** String containing the requested content.

**Example:**
```python
# Read specific line
content = read_content("/path/to/file.py", 42, mode="lines")

# Read complete function containing pattern
content = read_content("/path/to/file.py", "def main", mode="semantic")

# Read function semantically by line number
content = read_content("/path/to/file.py", 100, mode="function")
```

### edit_content

Primary editing method using search/replace blocks (not line-based).

**Signature:**
```python
def edit_content(
    absolute_file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy: bool = True,
    preview: bool = True
) -> EditResult
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `search_text`: Text to find and replace (required)
- `replace_text`: Replacement text (required)
- `fuzzy`: Enable fuzzy matching for search_text (default: True)
- `preview`: Show preview without making changes (default: True)

**Returns:** `EditResult` object with:
- `success`: True if operation succeeded
- `preview`: Diff preview showing before/after changes
- `changes_made`: Number of replacements made
- `line_number`: Line where change occurred
- `similarity_used`: Similarity score if fuzzy matching was used
- `backup_created`: Path to backup file (if preview=False)

**Example:**
```python
# Preview mode (safe, no changes made)
result = edit_content("/path/to/file.py", "old_function_name", "new_function_name", preview=True)
print(result.preview)

# Apply changes (creates backup)
if result.success:
    result = edit_content("/path/to/file.py", "old_function_name", "new_function_name", preview=False)
    print(f"Backup created at: {result.backup_created}")
```

## Data Models

### FileOverview
```python
@dataclass
class FileOverview:
    line_count: int
    file_size: int
    encoding: str
    has_long_lines: bool
    outline: List[OutlineItem]
    search_hints: List[str]
```

### OutlineItem
```python
@dataclass
class OutlineItem:
    name: str                    # Function/class name
    type: str                    # "function", "class", "method", "import"
    line_number: int            # Starting line
    end_line: int               # Ending line
    children: List[OutlineItem] # Nested items (methods in class)
    line_count: int             # Total lines in item
```

### SearchResult
```python
@dataclass
class SearchResult:
    line_number: int
    match: str
    context_before: List[str]
    context_after: List[str]
    semantic_context: str
    similarity_score: float
    truncated: bool
    submatches: List[Dict[str, int]]  # [{"start": 10, "end": 15}]
```

### EditResult
```python
@dataclass
class EditResult:
    success: bool
    preview: str
    changes_made: int
    line_number: int
    similarity_used: float
    backup_created: Optional[str] = None
```

## Error Handling

All tools return structured error information when operations fail:

```python
{
    "error": "Description of what went wrong",
    "suggestion": "Actionable advice for resolution"
}
```

**Common Error Types:**
- **File Access**: File not found, permission denied, encoding issues
- **Search**: Pattern not found, invalid regex, search timeout
- **Edit**: Search text not found, write permission denied, backup failed
- **Tree-sitter**: Parsing failed, language not supported, timeout

**Error Recovery:**
- Tools gracefully degrade when Tree-sitter is unavailable
- Fuzzy matching can be disabled for exact-only searches
- Edit operations create backups before making changes
- Clear suggestions provided for resolving common issues

## Performance Considerations

**File Size Handling:**
- Files <50MB: Loaded into memory for fastest access
- Files 50-500MB: Memory-mapped for efficient searching
- Files >500MB: Streaming access with chunked processing

**Search Performance:**
- Exact matches: O(n) scan with early termination
- Fuzzy matches: O(n*m) with configurable similarity threshold
- Tree-sitter parsing: ~100ms for typical source files

**Memory Usage:**
- Small files: File size + parsing overhead
- Large files: Minimal memory footprint via streaming
- AST caching: Parse once per session, reuse for semantic operations

**Configuration:**
See [Configuration Guide](configuration.md) for performance tuning options.