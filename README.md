# Largefile MCP Server

An MCP server that enables AI assistants to work with large files that exceed context limits.

[![CI](https://img.shields.io/github/actions/workflow/status/peteretelej/largefile/ci.yml?branch=main&logo=github)](https://github.com/peteretelej/largefile/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/peteretelej/largefile/branch/main/graph/badge.svg)](https://codecov.io/gh/peteretelej/largefile) [![PyPI version](https://img.shields.io/pypi/v/largefile.svg)](https://pypi.org/project/largefile/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Navigate, search, and edit files of any size without loading entire content into memory. Largefile provides targeted access to specific lines, patterns, and sections while maintaining file integrity using research-backed search/replace editing instead of error-prone line-based operations.

Perfect for working with large codebases, generated files, logs, and datasets that would otherwise be inaccessible due to context window limitations.

## MCP Tools

Five tools that work together for progressive file exploration:

| Tool | Purpose |
|------|---------|
| **`get_overview`** | File structure with Tree-sitter semantic analysis, line counts, and search hints |
| **`search_content`** | Pattern search with fuzzy matching, context lines, and semantic information |
| **`read_content`** | Targeted reading by line number, pattern, or tail mode for log files |
| **`edit_content`** | Search/replace editing with batch support, automatic backups, and preview mode |
| **`revert_edit`** | Recover from bad edits by reverting to previous backup states |

## Quick Start

**Prerequisite:** Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (an extremely fast Python package manager) which provides the `uvx` command.

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "largefile": {
      "command": "uvx",
      "args": ["--from", "largefile", "largefile-mcp"]
    }
  }
}
```

## Usage

Your AI Assistant / LLM can now work with very large files that exceed its context limits. Here are some common workflows:

### Analyzing Large Code Files

**AI Question:** _"Can you analyze this large Django models file and tell me about the class structure and any potential issues? It's a large file so use largefile."_

**AI Assistant workflow:**

1. Gets file overview to understand structure
2. Searches for classes and their methods
3. Looks for code issues like TODOs or long functions

```python
# AI gets file structure
overview = get_overview("/path/to/django-models.py")
# Returns: 2,847 lines, 15 classes, semantic outline with Tree-sitter

# AI searches for all class definitions
classes = search_content("/path/to/django-models.py", "class ", max_results=20)
# Returns: Model classes with line numbers and context

# AI examines specific class implementation
model_code = read_content("/path/to/django-models.py", "class User", mode="semantic")
# Returns: Complete class definition with all methods
```

### Working with Documentation

**AI Question:** _"Find all the installation methods mentioned in this README file and update the pip install to use uv instead."_

**AI Assistant workflow:**

1. Search for installation patterns
2. Read the installation section
3. Replace pip commands with uv equivalents

```python
# AI finds installation instructions
install_sections = search_content("/path/to/readme.md", "install", fuzzy=True, context_lines=3)

# AI reads the installation section
install_content = read_content("/path/to/readme.md", "## Installation", mode="semantic")

# AI replaces pip with uv
edit_result = edit_content(
    "/path/to/readme.md",
    search_text="pip install anthropic",
    replace_text="uv add anthropic",
    preview=True
)
```

### Debugging Large Log Files

**AI Question:** _"Check this production log file for any critical errors in the last few thousand lines and show me the context around them. Use largefile mcp."_

**AI Assistant workflow:**

1. Get log file overview
2. Read the last N lines efficiently with tail mode
3. Search for error patterns in recent entries

```python
# AI gets log file overview
overview = get_overview("/path/to/production.log")
# Returns: 150,000 lines, 2.1GB file size

# AI reads the last 1000 lines efficiently (no need to know total line count)
recent = read_content("/path/to/production.log", 1000, mode="tail")
# Returns: Last 1000 lines without loading entire file

# AI searches for critical errors
errors = search_content("/path/to/production.log", "CRITICAL|ERROR", fuzzy=True, max_results=10)

# AI examines context around each error
for error in errors:
    context = read_content("/path/to/production.log", error.line_number, mode="lines")
    # Shows surrounding log entries for debugging
```

### Refactoring Code

**AI Question:** _"I need to rename the function `process_data` to `transform_data` throughout this large codebase file. Can you help me do this safely?"_

**AI Assistant workflow:**

1. Find all occurrences of the function
2. Preview changes to ensure accuracy
3. Apply changes with automatic backup

```python
# AI finds all usages
usages = search_content("/path/to/codebase.py", "process_data", fuzzy=False, max_results=50)

# AI previews the changes
preview = edit_content(
    "/path/to/codebase.py",
    search_text="process_data",
    replace_text="transform_data",
    preview=True
)

# AI applies changes after confirmation
result = edit_content(
    "/path/to/codebase.py",
    search_text="process_data",
    replace_text="transform_data",
    preview=False
)
# Creates automatic backup before changes
```

### Batch Editing Multiple Patterns

**AI Question:** _"Update all the deprecated API calls in this file - there are several different ones to change."_

**AI Assistant workflow:**

1. Identify all deprecated patterns
2. Apply multiple changes atomically in one call

```python
# AI applies multiple changes in a single atomic operation
result = edit_content(
    "/path/to/api_client.py",
    changes=[
        {"search": "client.get_user(", "replace": "client.fetch_user("},
        {"search": "client.post_data(", "replace": "client.send_data("},
        {"search": "client.delete_item(", "replace": "client.remove_item("},
    ],
    preview=True
)
# Returns per-change results with success/failure status
# All changes applied atomically - partial success is reported
```

### Recovering from Bad Edits

**AI Question:** _"That last edit broke something. Can you undo it?"_

**AI Assistant workflow:**

1. List available backups
2. Revert to previous state (current state is preserved as new backup)

```python
# AI reverts to the most recent backup
result = revert_edit("/path/to/broken_file.py")
# Current state saved as backup, file restored to previous version

# Or revert to a specific backup by ID
result = revert_edit("/path/to/broken_file.py", backup_id="20240115_143022")
# Returns: available_backups list for reference
```

### Exploring API Documentation

**AI Question:** _"What are all the available methods in this large API documentation file and can you show me examples of authentication?"_

**AI Assistant workflow:**

1. Get document structure overview
2. Search for method definitions and auth patterns
3. Extract relevant code examples

```python
# AI analyzes document structure
overview = get_overview("/path/to/api-docs.md")
# Returns: Section outline, headings, suggested search patterns

# AI finds API methods
methods = search_content("/path/to/api-docs.md", "###", max_results=30)
# Returns: All method headings with context

# AI searches for authentication examples
auth_examples = search_content("/path/to/api-docs.md", "auth", fuzzy=True, context_lines=5)

# AI reads complete authentication section
auth_section = read_content("/path/to/api-docs.md", "## Authentication", mode="semantic")
```

## File Size Handling

- **Small files (<50MB)**: Memory loading with Tree-sitter AST caching
- **Medium files (50-500MB)**: Memory-mapped access
- **Large files (>500MB)**: Streaming processing
- **Long lines (>1000 chars)**: Automatic truncation for display

## Supported Languages

Tree-sitter semantic analysis for:

- Python (.py)
- JavaScript/JSX (.js, .jsx)
- TypeScript/TSX (.ts, .tsx)
- Rust (.rs)
- Go (.go)

Files without Tree-sitter support use text-based analysis with graceful degradation.

## Configuration

Configure via environment variables:

```bash
# File processing thresholds
LARGEFILE_MEMORY_THRESHOLD_MB=50        # Memory loading limit
LARGEFILE_MMAP_THRESHOLD_MB=500         # Memory mapping limit

# Search settings
LARGEFILE_FUZZY_THRESHOLD=0.8           # Fuzzy match sensitivity (0.0-1.0)
LARGEFILE_MAX_SEARCH_RESULTS=20         # Result limit per search
LARGEFILE_CONTEXT_LINES=2               # Context lines around matches

# Error recovery
LARGEFILE_SIMILAR_MATCH_LIMIT=3         # Similar matches shown on edit failure
LARGEFILE_SIMILAR_MATCH_THRESHOLD=0.6   # Min similarity for suggestions

# Backup management
LARGEFILE_BACKUP_DIR="~/.largefile/backups"  # Backup location
LARGEFILE_MAX_BACKUPS=10                # Backups retained per file

# Batch editing
LARGEFILE_MAX_BATCH_CHANGES=50          # Max changes per batch call

# Performance
LARGEFILE_ENABLE_TREE_SITTER=true       # Semantic features
```

## Key Features

- **Search/replace editing** - Eliminates LLM line number errors with fuzzy matching
- **Batch operations** - Apply multiple changes atomically in one call
- **Smart error recovery** - Failed edits show similar matches with suggestions
- **Backup & revert** - Automatic backups with full revert capability
- **Tail mode** - Read log file endings without knowing total line count
- **Semantic awareness** - Tree-sitter integration for code structure
- **Memory efficient** - Handles files of any size via tiered access strategy

## Documentation

- [API Reference](docs/API.md) - Detailed tool documentation
- [Configuration Guide](docs/configuration.md) - Environment variables and tuning
- [Examples](docs/examples.md) - Real-world usage examples and workflows
- [Design Document](docs/design.md) - Architecture and implementation details
- [Contributing](docs/CONTRIBUTING.md) - Development setup and guidelines
