# API Reference

Detailed documentation for the Largefile MCP Server tools.

## Overview

The Largefile MCP Server provides 5 tools for working with large text files:

| Tool | Purpose |
|------|---------|
| **get_overview** | File structure analysis with Tree-sitter semantic outline |
| **search_content** | Pattern search with fuzzy matching and context |
| **read_content** | Targeted reading by line, pattern, or tail mode |
| **edit_content** | Search/replace editing with batch support |
| **revert_edit** | Recover from bad edits via backup restoration |

All tools require absolute file paths and support auto-detected text encoding.

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

Read targeted content by line number, pattern, or from end of file.

**Signature:**
```python
def read_content(
    absolute_file_path: str,
    target: Union[int, str],
    mode: str = "lines"
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `target`: Line number (int) or search pattern (str) to locate content (required)
- `mode`: Reading mode (default: "lines")

**Reading Modes:**
| Mode | Description | Target |
|------|-------------|--------|
| `"lines"` | Read from specific line number or around pattern match | Line number or pattern |
| `"semantic"` | Use Tree-sitter to read complete semantic blocks | Line number or pattern |
| `"tail"` | Read last N lines from end of file (efficient for logs) | Number of lines (int) |

**Returns:** Dictionary with:
- `content`: The requested content string
- `start_line`, `end_line`: Line range of returned content
- `total_lines`: Total lines in file
- `mode`: The mode used

**Example:**
```python
# Read specific line range
content = read_content("/path/to/file.py", 42, mode="lines")

# Read complete function containing pattern
content = read_content("/path/to/file.py", "def main", mode="semantic")

# Read last 500 lines of a log file (no need to know total lines)
content = read_content("/path/to/production.log", 500, mode="tail")
# Returns: {"content": "...", "lines_read": 500, "total_lines": 150000}
```

### edit_content

Primary editing method using search/replace blocks. Supports single edits and batch operations.

**Signature:**
```python
def edit_content(
    absolute_file_path: str,
    search_text: str = None,        # Single edit mode
    replace_text: str = None,       # Single edit mode
    changes: list[dict] = None,     # Batch edit mode
    fuzzy: bool = True,
    preview: bool = True
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `search_text`: Text to find and replace (single edit mode)
- `replace_text`: Replacement text (single edit mode)
- `changes`: Array of `{search, replace, fuzzy?}` objects (batch edit mode)
- `fuzzy`: Enable fuzzy matching (default: True, can be overridden per-change)
- `preview`: Show preview without making changes (default: True)

> **Note:** Use either `search_text`/`replace_text` OR `changes`, not both.

**Returns (Single Edit):**
- `success`: True if edit succeeded
- `preview`: Diff preview showing before/after
- `changes_made`: Number of replacements
- `line_number`: Line where change occurred
- `similarity_used`: Fuzzy match score (if used)
- `backup_created`: Backup path (if preview=False)
- `similar_matches`: Suggestions if edit failed (see Enhanced Errors below)

**Returns (Batch Edit):**
- `success`: True if all changes succeeded
- `changes_applied`: Count of successful changes
- `changes_failed`: Count of failed changes
- `results`: Per-change results with individual status
- `preview`: Combined diff preview
- `backup_created`: Backup path (if preview=False)

**Example - Single Edit:**
```python
# Preview mode (safe, no changes made)
result = edit_content("/path/to/file.py", "old_function_name", "new_function_name", preview=True)
print(result["preview"])

# Apply changes (creates backup)
result = edit_content("/path/to/file.py", "old_function_name", "new_function_name", preview=False)
print(f"Backup created at: {result['backup_created']}")
```

**Example - Batch Edit:**
```python
# Apply multiple changes atomically
result = edit_content(
    "/path/to/file.py",
    changes=[
        {"search": "old_func_1", "replace": "new_func_1"},
        {"search": "old_func_2", "replace": "new_func_2"},
        {"search": "exact_match_only", "replace": "replacement", "fuzzy": False},
    ],
    preview=True
)

# Check individual results
for r in result["results"]:
    status = "OK" if r["success"] else f"FAILED: {r.get('error')}"
    print(f"Change {r['index']}: {status}")
```

**Enhanced Error Messages:**

When an edit fails (pattern not found), the response includes helpful suggestions:
```python
{
    "success": False,
    "search_attempted": "def proces_data(",
    "similar_matches": [
        {"line": 42, "content": "def process_data(", "similarity": 0.92},
        {"line": 156, "content": "def process_data_batch(", "similarity": 0.85}
    ],
    "suggestion": "Did you mean 'def process_data(' on line 42?"
}
```

### revert_edit

Recover from bad edits by reverting to a previous backup state.

**Signature:**
```python
def revert_edit(
    absolute_file_path: str,
    backup_id: str = None
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file to revert (required)
- `backup_id`: Timestamp ID of backup to restore (optional, defaults to most recent)

**Returns:**
- `success`: True if revert succeeded
- `reverted_to`: Info about the backup that was restored
- `current_saved_as`: Info about backup created from current state (before revert)
- `available_backups`: List of all available backups for this file
- `error`: Error message if revert failed

**Example:**
```python
# Revert to most recent backup
result = revert_edit("/path/to/file.py")
print(f"Reverted to: {result['reverted_to']['timestamp']}")
print(f"Current state saved as: {result['current_saved_as']['id']}")

# Revert to specific backup
result = revert_edit("/path/to/file.py", backup_id="20240115_143022")

# List available backups without reverting
result = revert_edit("/path/to/nonexistent.py")  # Returns available_backups
```

**Backup Info Structure:**
```python
{
    "id": "20240115_143022",           # Timestamp ID for revert_edit
    "timestamp": "2024-01-15 14:30:22", # Human-readable timestamp
    "size": 4523,                       # File size in bytes
    "path": "/home/user/.largefile/backups/file.abc123.20240115_143022"
}
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

### EditResult (Single Edit)
```python
@dataclass
class EditResult:
    success: bool
    preview: str
    changes_made: int
    line_number: int
    match_type: str              # "exact" or "fuzzy"
    similarity_used: float
    backup_created: Optional[str] = None
    # Enhanced error fields (when success=False):
    search_attempted: Optional[str] = None
    fuzzy_enabled: Optional[bool] = None
    suggestion: Optional[str] = None
    similar_matches: Optional[List[SimilarMatch]] = None
```

### BatchEditResult
```python
@dataclass
class BatchEditResult:
    success: bool                # True if all changes succeeded
    changes_applied: int
    changes_failed: int
    results: List[ChangeResult]  # Per-change results
    preview: str
    backup_created: Optional[str] = None
```

### ChangeResult
```python
@dataclass
class ChangeResult:
    index: int                   # Position in changes array
    success: bool
    line_number: Optional[int] = None
    match_type: Optional[str] = None
    similarity: Optional[float] = None
    error: Optional[str] = None
    similar_matches: Optional[List[SimilarMatch]] = None
```

### SimilarMatch
```python
@dataclass
class SimilarMatch:
    line: int                    # Line number
    content: str                 # Matching line content
    similarity: float            # Similarity score (0.0-1.0)
```

### BackupInfo
```python
@dataclass
class BackupInfo:
    id: str                      # Timestamp ID (e.g., "20240115_143022")
    timestamp: str               # Human-readable timestamp
    size: int                    # File size in bytes
    path: str                    # Full path to backup file
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