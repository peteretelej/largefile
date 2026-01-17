# API Reference

Detailed documentation for the Largefile MCP Server tools.

## Overview

The Largefile MCP Server provides 5 tools for working with large text files:

| Tool | Purpose |
|------|---------|
| **get_overview** | File structure analysis with Tree-sitter semantic outline |
| **search_content** | Pattern search with fuzzy, regex, and invert matching |
| **read_content** | Targeted reading by offset, pattern, tail, or head mode |
| **edit_content** | Batch search/replace editing with automatic backups |
| **revert_edit** | Recover from bad edits via backup restoration |

All tools require absolute file paths and support auto-detected text encoding.

## Tools

### get_overview

Analyze file structure with semantic outline and search hints.

**Signature:**
```python
def get_overview(
    absolute_file_path: str
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)

**Returns:** Dictionary with:
- `line_count`: Total lines in file
- `file_size`: File size in bytes
- `encoding`: Auto-detected file encoding (or `None` for binary)
- `is_binary`: `True` if file appears to be binary
- `binary_hint`: Hint about binary type (e.g., "image", "compressed") or `None`
- `long_lines`: Object with detailed long line statistics
- `outline`: Hierarchical structure via Tree-sitter (if supported)
- `search_hints`: Suggested search patterns for exploration

**Long Lines Object:**
```python
{
    "has_long_lines": True,      # Any line exceeds threshold
    "count": 47,                  # Number of long lines
    "max_length": 15000,          # Longest line length
    "threshold": 1000             # Configured threshold
}
```

**Example:**
```python
overview = get_overview("/path/to/large_file.py")
print(f"File has {overview['line_count']} lines")

# Check for binary file
if overview["is_binary"]:
    print(f"Binary file detected: {overview['binary_hint']}")
else:
    for item in overview["outline"]:
        print(f"{item['type']}: {item['name']} at line {item['line_number']}")

# Check for long lines
if overview["long_lines"]["has_long_lines"]:
    print(f"Warning: {overview['long_lines']['count']} lines exceed {overview['long_lines']['threshold']} chars")
```

### search_content

Find patterns with fuzzy matching, regex, and semantic context.

**Signature:**
```python
def search_content(
    absolute_file_path: str,
    pattern: str,
    max_results: int = 20,
    context_lines: int = 3,
    fuzzy: bool = True,
    regex: bool = False,
    case_sensitive: bool = True,
    invert: bool = False,
    count_only: bool = False,
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `pattern`: Search pattern - exact text, fuzzy match, or regex (required)
- `max_results`: Maximum number of results to return (default: 20)
- `context_lines`: Number of context lines before/after match (default: 3)
- `fuzzy`: Enable fuzzy matching with similarity scoring (default: True)
- `regex`: Enable Python regex pattern matching (default: False)
- `case_sensitive`: Control case sensitivity for exact/regex modes (default: True, ignored for fuzzy)
- `invert`: Return non-matching lines like `grep -v` (default: False)
- `count_only`: Return only match count, not content (default: False)

**Note:** `regex=True` and `fuzzy=True` cannot be used together. Set `fuzzy=False` when using regex.

**Returns (Standard Mode):** Dictionary with:
- `results`: List of search results (see below)
- `total_matches`: Total matches found
- `pattern`: The search pattern used
- `fuzzy_enabled`, `regex_enabled`, `case_sensitive`, `inverted`: Search options used

**Returns (count_only Mode):** Dictionary with:
- `count`: Number of matches found
- `pattern`: The search pattern used
- `fuzzy_enabled`, `regex_enabled`, `case_sensitive`, `inverted`: Search options used
- `warnings`: Array of warnings about ignored parameters (if any)

**Search Result Object:**
- `line_number`: Line where match was found
- `match`: The matching text (truncated if >500 chars)
- `context_before`: Lines before the match
- `context_after`: Lines after the match
- `semantic_context`: Tree-sitter context (e.g., "inside function foo()")
- `similarity_score`: Fuzzy match score (0.0-1.0, 1.0 for exact matches)
- `truncated`: True if match text was truncated for display
- `match_type`: "exact", "fuzzy", or "regex"

**Examples:**
```python
# Exact search (disable fuzzy for precise matching)
results = search_content("/path/to/file.py", "def process_data", fuzzy=False)

# Fuzzy search handles typos and variations
results = search_content("/path/to/file.py", "proces_data", fuzzy=True)
for r in results["results"]:
    print(f"Line {r['line_number']}: {r['match']} (score: {r['similarity_score']})")

# Regex search for IP addresses
results = search_content(
    "/path/to/server.log",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    regex=True,
    fuzzy=False
)

# Count errors without returning content (efficient for large files)
result = search_content("/path/to/app.log", "ERROR", count_only=True, fuzzy=False)
print(f"Found {result['count']} errors")

# Case-insensitive search
results = search_content("/path/to/file.py", "error", case_sensitive=False, fuzzy=False)

# Find non-DEBUG lines (invert matching like grep -v)
results = search_content("/path/to/app.log", "DEBUG", invert=True, fuzzy=False)
```

### read_content

Read targeted content by line offset, search pattern, or from file ends.

**Signature:**
```python
def read_content(
    absolute_file_path: str,
    offset: int = 1,
    limit: int = 100,
    pattern: str | None = None,
    mode: str = "lines",
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `offset`: Starting line number, 1-indexed (default: 1)
- `limit`: Maximum lines to return (default: 100)
- `pattern`: Optional search pattern to locate starting position
- `mode`: Reading mode (default: "lines")

**Reading Modes:**
| Mode | Description | Uses offset | Uses limit | Uses pattern |
|------|-------------|-------------|------------|--------------|
| `"lines"` | Read from specific line offset | Yes | Yes | Optional |
| `"semantic"` | Read complete semantic blocks via Tree-sitter | As start hint | No | Optional |
| `"tail"` | Read last N lines from end (efficient for logs) | Ignored | Yes (N lines) | No |
| `"head"` | Read first N lines from start | Ignored | Yes (N lines) | No |

**Returns:** Dictionary with:
- `content`: The requested content string
- `start_line`, `end_line`: Line range of returned content
- `lines_returned`: Number of lines returned
- `total_lines`: Total lines in file
- `mode`: The mode used
- `truncated`: True if more content exists beyond limit (lines mode)
- `warnings`: Array of warnings about ignored parameters (if any)
- Pattern match info (if pattern used): `pattern`, `match_line`, `similarity_score`

**Examples:**
```python
# Read from specific line offset
content = read_content("/path/to/file.py", offset=100, limit=50)
# Returns lines 100-149

# Read first 200 lines (head mode)
content = read_content("/path/to/file.py", limit=200, mode="head")

# Read last 500 lines of a log file (tail mode - efficient, no full scan)
content = read_content("/path/to/production.log", limit=500, mode="tail")
# Returns: {"content": "...", "start_line": 149501, "end_line": 150000, ...}

# Read around a search pattern
content = read_content("/path/to/file.py", pattern="def main", limit=50)
# Returns 50 lines starting near the match

# Read complete function using semantic mode
content = read_content("/path/to/file.py", pattern="def process_data", mode="semantic")
# Returns the entire function definition
```

### edit_content

Edit files using search/replace with fuzzy matching and automatic backups.

**Signature:**
```python
def edit_content(
    absolute_file_path: str,
    changes: list[dict],
    fuzzy: bool = True,
    preview: bool = True,
) -> dict
```

**Parameters:**
- `absolute_file_path`: Absolute path to the file (required)
- `changes`: Array of change objects (required)
- `fuzzy`: Enable fuzzy matching (default: True, can be overridden per-change)
- `preview`: Show preview without making changes (default: True)

**Change Object:**
```python
{
    "search": "text to find",       # Required
    "replace": "replacement text",  # Required
    "fuzzy": True                   # Optional: override global fuzzy setting
}
```

**Returns:** Dictionary with:
- `success`: True if all changes succeeded
- `changes_applied`: Count of successful changes
- `changes_failed`: Count of failed changes
- `results`: Per-change results with individual status
- `preview`: Combined diff preview
- `backup_created`: Backup path (if preview=False and changes made)

**Per-Change Result:**
- `index`: Position in changes array
- `success`: True if this change succeeded
- `line_number`: Line where change occurred (if successful)
- `match_type`: "exact" or "fuzzy"
- `similarity`: Fuzzy match score (if used)
- `error`: Error message (if failed)
- `similar_matches`: Suggestions if change failed (see Enhanced Errors below)

**Examples:**
```python
# Single edit (use array with one change)
result = edit_content(
    "/path/to/file.py",
    changes=[{"search": "old_name", "replace": "new_name"}],
    preview=True
)
print(result["preview"])

# Apply the change (creates backup)
result = edit_content(
    "/path/to/file.py",
    changes=[{"search": "old_name", "replace": "new_name"}],
    preview=False
)
print(f"Backup created at: {result['backup_created']}")

# Batch edit - multiple changes atomically
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
    "results": [{
        "index": 0,
        "success": False,
        "error": "Search text not found",
        "similar_matches": [
            {"line": 42, "content": "def process_data(", "similarity": 0.92},
            {"line": 156, "content": "def process_data_batch(", "similarity": 0.85}
        ]
    }]
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

# Check available backups
for backup in result["available_backups"]:
    print(f"{backup['id']}: {backup['timestamp']} ({backup['size']} bytes)")
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
{
    "line_count": 1500,
    "file_size": 45000,
    "encoding": "utf-8",
    "is_binary": False,
    "binary_hint": None,
    "long_lines": {
        "has_long_lines": True,
        "count": 47,
        "max_length": 15000,
        "threshold": 1000
    },
    "outline": [...],
    "search_hints": [...]
}
```

### SearchResult
```python
{
    "line_number": 42,
    "match": "def process_data(self, items):",
    "context_before": ["", "class DataProcessor:"],
    "context_after": ["    for item in items:", "        ..."],
    "semantic_context": "inside class DataProcessor",
    "similarity_score": 1.0,
    "truncated": False,
    "match_type": "exact"
}
```

### EditResult
```python
{
    "success": True,
    "changes_applied": 3,
    "changes_failed": 0,
    "results": [
        {"index": 0, "success": True, "line_number": 42, "match_type": "exact"},
        {"index": 1, "success": True, "line_number": 87, "match_type": "fuzzy", "similarity": 0.95},
        {"index": 2, "success": True, "line_number": 156, "match_type": "exact"}
    ],
    "preview": "--- before\n+++ after\n...",
    "backup_created": "/home/user/.largefile/backups/file.abc123.20240115_143022"
}
```

### BackupInfo
```python
{
    "id": "20240115_143022",
    "timestamp": "2024-01-15 14:30:22",
    "size": 4523,
    "path": "/home/user/.largefile/backups/file.abc123.20240115_143022"
}
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
- **Search**: Pattern not found, invalid regex, regex+fuzzy conflict
- **Edit**: Search text not found, write permission denied, backup failed
- **Tree-sitter**: Parsing failed, language not supported

**Error Recovery:**
- Tools gracefully degrade when Tree-sitter is unavailable
- Fuzzy matching can be disabled for exact-only searches
- Edit operations create backups before making changes
- Clear suggestions provided for resolving common issues
- Failed edits include similar matches to help identify typos

## Performance Considerations

**File Size Handling:**
- Files <50MB: Loaded into memory for fastest access
- Files 50-500MB: Memory-mapped for efficient searching
- Files >500MB: Streaming access with chunked processing

**Search Performance:**
- Exact matches: O(n) scan with early termination
- Fuzzy matches: O(n*m) with configurable similarity threshold
- Regex matches: O(n) with Python re module
- Tree-sitter parsing: ~100ms for typical source files

**Memory Usage:**
- Small files: File size + parsing overhead
- Large files: Minimal memory footprint via streaming
- AST caching: Parse once per session, reuse for semantic operations

**Configuration:**
See [Configuration Guide](configuration.md) for performance tuning options.
