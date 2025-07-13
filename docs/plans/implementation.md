# Largefile Implementation Plan

## Work Plan Checklist

**IMPORTANT**: Always update this checklist when completing phases.

### Phase 1: Core Foundation

- [x] Set up project structure with simple, testable modules
- [x] Implement basic file loading with encoding parameter (no auto-detection)
- [x] Create simple session-less file access (evaluate session value later)
- [x] Basic exact string search functionality
- [x] Environment variable configuration system
- [x] Run scripts/pre-push to validate implementation
- [x] Review & Update work plan

### Phase 2: MCP Tool Framework

- [x] Implement 4 core MCP tools with FastMCP decorators
- [x] Clear, structured tool descriptions (following diffchunks pattern)
- [x] Pure functions - predictable inputs/outputs
- [x] Integration test framework for end-to-end tool testing
- [x] Run scripts/pre-push to validate implementation
- [x] Review & Update work plan

### Phase 3: Search/Replace Engine

- [x] Exact search/replace with atomic file operations
- [x] Fuzzy matching with rapidfuzz (sensible defaults)
- [x] Clear error reporting (no silent fallbacks)
- [x] Preview mode for edit operations
- [x] Run scripts/pre-push to validate implementation
- [x] Review & Update work plan

### Phase 4: Tree-sitter Integration

- [x] AST parsing for supported languages (Python, JS, Go, Rust)
- [x] Semantic context extraction
- [x] Hierarchical outline generation
- [x] Graceful degradation when Tree-sitter unavailable (clear error messages)
- [x] Run scripts/pre-push to validate implementation
- [x] Review & Update work plan

### Phase 5: Performance & Polish ✅ COMPLETED

- [x] Memory-mapped file access for large files (>50MB via env var)
- [x] Line truncation for display (>1000 chars)
- [x] Comprehensive integration tests
- [x] Review codebase for simplicity and clarity
- [x] Documentation and examples
- [x] Run scripts/pre-push to validate implementation
- [x] Review & Update work plan

---

## Architecture Overview

**Design Principle**: Simple, stateless, testable functions with clear error reporting.

```
File Input → [Search Engine | Tree-sitter Parser | Editor] → MCP Tools
                ↓              ↓                ↓
           Exact/Fuzzy     AST Parse        Search/Replace
```

**Key Simplifications:**

- **No complex session management** - each call is independent
- **Pure functions** - same inputs always produce same outputs
- **Clear error messages** - no silent fallbacks
- **Environment variable configuration** - keep API signatures clean

## File Access Strategy

**Configurable via Environment Variables:**

```bash
LARGEFILE_MEMORY_THRESHOLD_MB=50       # 50MB default
LARGEFILE_MMAP_THRESHOLD_MB=500        # 500MB default
LARGEFILE_MAX_LINE_LENGTH=1000         # Truncation trigger
LARGEFILE_TRUNCATE_LENGTH=500          # Display length
```

**Access Logic:**

```python
def choose_file_strategy(file_size: int) -> str:
    memory_threshold_mb = int(os.getenv('LARGEFILE_MEMORY_THRESHOLD_MB', '50'))
    mmap_threshold_mb = int(os.getenv('LARGEFILE_MMAP_THRESHOLD_MB', '500'))

    memory_threshold = memory_threshold_mb * 1024 * 1024
    mmap_threshold = mmap_threshold_mb * 1024 * 1024

    if file_size < memory_threshold:
        return "memory"          # Full content in RAM
    elif file_size < mmap_threshold:
        return "mmap"            # Memory-mapped access
    else:
        return "streaming"       # Chunk-based processing
```

## Project Structure

**Simple, Testable Modules:**

```
src/
├── server.py           # MCP server entry point
├── tools.py           # 4 core MCP tools (pure functions)
├── file_access.py     # File loading with encoding parameter
├── search_engine.py   # Exact + fuzzy search (no caching)
├── tree_parser.py     # Tree-sitter integration (no caching)
├── editor.py          # Search/replace operations
└── config.py          # Environment variable configuration
```

## MCP Tool Signatures

**Clean APIs with sensible defaults, advanced config via env vars:**

```python
@mcp.tool()
def get_overview(
    absolute_file_path: str,
    encoding: str = "utf-8"
) -> FileOverview:
    """Get file structure with Tree-sitter semantic analysis.

    Auto-generates hierarchical outline via Tree-sitter. Detects long lines
    for truncation. Returns semantic structure and search hints for efficient
    exploration.

    CRITICAL: You must use an absolute file path - relative paths will fail.
    DO NOT attempt to read large files directly as they exceed context limits.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - encoding: File encoding (utf-8, latin-1, etc.)
    """

@mcp.tool()
def search_content(
    absolute_file_path: str,
    pattern: str,
    encoding: str = "utf-8",
    max_results: int = 20,
    context_lines: int = 2,
    fuzzy: bool = True
) -> list[SearchResult]:
    """Find patterns with fuzzy matching and semantic context.

    Uses fuzzy matching via Levenshtein distance to handle real-world
    formatting variations. Returns semantic context via Tree-sitter when
    available.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - pattern: Search pattern (exact or fuzzy matching)
    - encoding: File encoding
    - max_results: Maximum number of results to return
    - context_lines: Number of context lines before/after match
    - fuzzy: Enable fuzzy matching (default True)
    """

@mcp.tool()
def read_content(
    absolute_file_path: str,
    target: Union[int, str],
    encoding: str = "utf-8",
    mode: str = "semantic"
) -> str:
    """Read semantic chunks instead of arbitrary lines.

    Uses Tree-sitter to return complete functions/classes/blocks instead
    of arbitrary line ranges. Falls back to line-based reading when
    Tree-sitter unavailable.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - target: Line number or search pattern to locate content
    - encoding: File encoding
    - mode: "semantic"|"lines"|"function" - how to chunk content
    """

@mcp.tool()
def edit_content(
    absolute_file_path: str,
    search_text: str,
    replace_text: str,
    encoding: str = "utf-8",
    fuzzy: bool = True,
    preview: bool = True
) -> EditResult:
    """PRIMARY EDITING METHOD using search/replace blocks.

    Fuzzy matching handles whitespace variations. Eliminates line number
    confusion that causes LLM errors. This replaces line-based editing.
    Creates automatic backups before changes.

    Parameters:
    - absolute_file_path: Absolute path to the file
    - search_text: Text to find and replace
    - replace_text: Replacement text
    - encoding: File encoding
    - fuzzy: Enable fuzzy matching for search_text
    - preview: Show preview without making changes (default True)
    """
```

## Tree-sitter Integration

**No Caching - Parse on Demand:**

```python
def parse_file_ast(file_path: str, content: str) -> Optional[Tree]:
    """Parse file content with Tree-sitter. Returns None if unsupported."""
    file_ext = Path(file_path).suffix.lower()

    if file_ext not in SUPPORTED_LANGUAGES:
        return None  # Clear indication of no support

    try:
        language = get_language(SUPPORTED_LANGUAGES[file_ext])
        parser = Parser(language)
        return parser.parse(bytes(content, 'utf-8'))
    except Exception as e:
        # Clear error - no silent fallback
        raise TreeSitterError(f"Failed to parse {file_ext}: {e}")

SUPPORTED_LANGUAGES = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.rs': 'rust',
    '.go': 'go'
}
```

## Search Engine

**Simple exact + fuzzy matching with clear results:**

```python
def search_file(file_path: str, pattern: str, fuzzy: bool = True) -> list[SearchMatch]:
    """Search file content. Returns clear results or clear errors."""

    # Read file with specified encoding
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        raise SearchError(f"Cannot read {file_path}: {e}")

    # Stage 1: Try exact match first
    exact_matches = find_exact_matches(lines, pattern)
    if exact_matches and not fuzzy:
        return exact_matches

    # Stage 2: Fuzzy matching if enabled
    if fuzzy:
        fuzzy_threshold = float(os.getenv('LARGEFILE_FUZZY_THRESHOLD', '0.8'))
        fuzzy_matches = find_fuzzy_matches(lines, pattern, fuzzy_threshold)
        return combine_results(exact_matches, fuzzy_matches)

    return exact_matches

def find_fuzzy_matches(lines: list[str], pattern: str, threshold: float) -> list[SearchMatch]:
    """Use rapidfuzz for fuzzy matching. No silent fallbacks."""
    from rapidfuzz import fuzz

    matches = []
    for line_num, line in enumerate(lines, 1):
        similarity = fuzz.ratio(pattern, line.strip()) / 100.0

        if similarity >= threshold:
            matches.append(SearchMatch(
                line_number=line_num,
                content=line.strip(),
                similarity_score=similarity,
                match_type="fuzzy"
            ))

    return sorted(matches, key=lambda x: x.similarity_score, reverse=True)
```

## Search/Replace Engine

**Simple, atomic operations with clear results:**

```python
def replace_content(file_path: str, search_text: str, replace_text: str,
                   encoding: str, fuzzy: bool = True, preview: bool = True) -> EditResult:
    """Replace content using search/replace. Returns clear results or errors."""

    # Read original content
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            original_content = f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        raise EditError(f"Cannot read {file_path}: {e}")

    # Find matches (exact first, then fuzzy if enabled)
    if search_text in original_content:
        # Exact match found
        modified_content = original_content.replace(search_text, replace_text, 1)
        match_type = "exact"
        similarity = 1.0
    elif fuzzy:
        # Try fuzzy replacement
        modified_content, similarity = fuzzy_replace_content(
            original_content, search_text, replace_text
        )
        match_type = "fuzzy"
    else:
        # No matches found
        return EditResult(
            success=False,
            preview=f"No matches found for: {search_text}",
            changes_made=0,
            match_type="none",
            similarity_used=0.0
        )

    # Generate preview
    preview_text = generate_diff_preview(original_content, modified_content, search_text)

    if preview:
        return EditResult(
            success=True,
            preview=preview_text,
            changes_made=1,
            match_type=match_type,
            similarity_used=similarity
        )

    # Make actual changes
    backup_path = create_backup(file_path)
    atomic_write_file(file_path, modified_content, encoding)

    return EditResult(
        success=True,
        preview=preview_text,
        changes_made=1,
        match_type=match_type,
        similarity_used=similarity,
        backup_created=backup_path
    )

def atomic_write_file(file_path: str, content: str, encoding: str):
    """Write file atomically using temp file + rename."""
    temp_path = f"{file_path}.tmp"

    try:
        with open(temp_path, 'w', encoding=encoding) as f:
            f.write(content)
        os.rename(temp_path, file_path)
    except Exception as e:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise EditError(f"Failed to write {file_path}: {e}")
```

## Error Handling Strategy

**Clear, non-silent error reporting:**

```python
# Custom exceptions for clear error communication
class LargeFileError(Exception):
    """Base exception for largefile operations."""
    pass

class FileAccessError(LargeFileError):
    """File cannot be read/written."""
    pass

class SearchError(LargeFileError):
    """Search operation failed."""
    pass

class EditError(LargeFileError):
    """Edit operation failed."""
    pass

class TreeSitterError(LargeFileError):
    """Tree-sitter parsing failed."""
    pass

# Error handling in tools
def handle_tool_errors(func):
    """Decorator to handle tool errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileAccessError as e:
            return {"error": f"File access failed: {e}", "suggestion": "Check file path and permissions"}
        except TreeSitterError as e:
            return {"error": f"Semantic parsing failed: {e}", "suggestion": "File will use text-based analysis"}
        except SearchError as e:
            return {"error": f"Search failed: {e}", "suggestion": "Try different search terms or disable fuzzy matching"}
        except EditError as e:
            return {"error": f"Edit failed: {e}", "suggestion": "Check search text matches exactly or enable fuzzy matching"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}", "suggestion": "Report this issue with file details"}
    return wrapper
```

## Integration Testing Strategy

**Focus on end-to-end tool testing:**

```python
# tests/integration/test_tools.py
class TestLargeFileTools:
    """Integration tests for the 4 core MCP tools."""

    def test_get_overview_python_file(self):
        """Test overview generation for Python files."""
        result = get_overview("/path/to/test.py", encoding="utf-8")
        assert result.line_count > 0
        assert result.has_long_lines in [True, False]
        assert "def " in result.search_hints

    def test_search_content_exact_and_fuzzy(self):
        """Test both exact and fuzzy search."""
        # Exact search
        results = search_content("/path/to/test.py", "def main", fuzzy=False)
        assert len(results) >= 0

        # Fuzzy search
        results = search_content("/path/to/test.py", "def maine", fuzzy=True)
        assert all(r.similarity_score >= 0.8 for r in results)

    def test_read_content_semantic_and_lines(self):
        """Test reading content in different modes."""
        # Line-based reading
        content = read_content("/path/to/test.py", 10, mode="lines")
        assert isinstance(content, str)

        # Pattern-based reading
        content = read_content("/path/to/test.py", "def main", mode="semantic")
        assert "def " in content

    def test_edit_content_preview_and_apply(self):
        """Test edit operations in preview and apply modes."""
        # Preview mode
        result = edit_content("/path/to/test.py", "old_text", "new_text", preview=True)
        assert result.success in [True, False]
        assert "preview" in result.preview

        # Apply mode (use test copy)
        result = edit_content("/path/to/test_copy.py", "old_text", "new_text", preview=False)
        if result.success:
            assert result.backup_created is not None

# Simple test data
TEST_FILES = {
    "small.py": "def hello():\n    print('world')\n\nclass Test:\n    pass",
    "large.py": "# " + "x" * 2000 + "\ndef function():\n    return True"  # Has long lines
}
```

## Environment Configuration

**All advanced settings via environment variables:**

```bash
# File processing thresholds
LARGEFILE_MEMORY_THRESHOLD_MB=50          # 50MB - load into memory
LARGEFILE_MMAP_THRESHOLD_MB=500           # 500MB - use memory mapping
LARGEFILE_MAX_LINE_LENGTH=1000            # Trigger line truncation
LARGEFILE_TRUNCATE_LENGTH=500             # Display length for long lines

# Search settings
LARGEFILE_FUZZY_THRESHOLD=0.8             # Minimum fuzzy match similarity
LARGEFILE_MAX_SEARCH_RESULTS=20           # Default result limit
LARGEFILE_CONTEXT_LINES=2                 # Default context window

# Performance settings
LARGEFILE_STREAMING_CHUNK_SIZE=8192       # 8KB chunks for streaming
LARGEFILE_BACKUP_DIR=".largefile_backups" # Backup directory location

# Tree-sitter settings
LARGEFILE_ENABLE_TREE_SITTER=true         # Enable/disable semantic features
LARGEFILE_TREE_SITTER_TIMEOUT=5           # Max seconds for AST parsing
```

**Configuration loading:**

```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    """Environment-based configuration with sensible defaults."""

    memory_threshold_mb: int = int(os.getenv('LARGEFILE_MEMORY_THRESHOLD_MB', '50'))
    mmap_threshold_mb: int = int(os.getenv('LARGEFILE_MMAP_THRESHOLD_MB', '500'))
    max_line_length: int = int(os.getenv('LARGEFILE_MAX_LINE_LENGTH', '1000'))
    truncate_length: int = int(os.getenv('LARGEFILE_TRUNCATE_LENGTH', '500'))

    fuzzy_threshold: float = float(os.getenv('LARGEFILE_FUZZY_THRESHOLD', '0.8'))
    max_search_results: int = int(os.getenv('LARGEFILE_MAX_SEARCH_RESULTS', '20'))
    context_lines: int = int(os.getenv('LARGEFILE_CONTEXT_LINES', '2'))

    streaming_chunk_size: int = int(os.getenv('LARGEFILE_STREAMING_CHUNK_SIZE', '8192'))
    backup_dir: str = os.getenv('LARGEFILE_BACKUP_DIR', '.largefile_backups')

    enable_tree_sitter: bool = os.getenv('LARGEFILE_ENABLE_TREE_SITTER', 'true').lower() == 'true'
    tree_sitter_timeout: int = int(os.getenv('LARGEFILE_TREE_SITTER_TIMEOUT', '5'))

    @property
    def memory_threshold(self) -> int:
        """Memory threshold in bytes."""
        return self.memory_threshold_mb * 1024 * 1024

    @property
    def mmap_threshold(self) -> int:
        """Memory mapping threshold in bytes."""
        return self.mmap_threshold_mb * 1024 * 1024

# Global config instance
config = Config()
```

## Implementation Principles

**Keep It Simple:**

- No complex session management - stateless operations
- Clear error messages - no silent fallbacks
- Pure functions - predictable inputs/outputs
- Environment configuration - clean API signatures

**Testing Focus:**

- Integration tests over unit tests
- End-to-end tool workflows
- Real file scenarios
- Clear test data and assertions

**Error Strategy:**

- Fail fast with clear messages
- Provide actionable suggestions
- Let LLM clients make intelligent decisions
- No hidden complexity or magic behavior
