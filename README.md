# Largefile MCP Server

Navigate, search, and edit large codebases, logs, and data files that exceed AI context limits.

[![CI](https://img.shields.io/github/actions/workflow/status/peteretelej/largefile/ci.yml?branch=main&logo=github)](https://github.com/peteretelej/largefile/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/peteretelej/largefile/branch/main/graph/badge.svg)](https://codecov.io/gh/peteretelej/largefile) [![PyPI version](https://img.shields.io/pypi/v/largefile.svg)](https://pypi.org/project/largefile/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why Largefile?

- **Go beyond context limits** - Read, search, and edit files too large to fit in AI context windows
- **Semantic code navigation** - Tree-sitter extracts functions/classes for Python, JS/TS, Rust, Go
- **Fewer LLM errors** - Search/replace editing eliminates line number mistakes common with line-based edits
- **Smart search** - Fuzzy matching, regex, case-insensitive, inverted, and count-only modes
- **No size limits** - Handles multi-GB files via tiered memory strategy (RAM → mmap → streaming)

## Quick Start

**Prerequisite:** Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for the `uvx` command.

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

## Tools

| Tool             | Use For                                                |
| ---------------- | ------------------------------------------------------ |
| `get_overview`   | File structure and semantic outline before diving in   |
| `search_content` | Finding patterns, counting occurrences, regex matching |
| `read_content`   | Reading specific sections; tail/head modes for logs    |
| `edit_content`   | Safe search/replace with automatic backups             |
| `revert_edit`    | Recovering from bad edits                              |

## When to Use Largefile

**Use when:**

- File exceeds ~1000 lines or 100KB (supports multi-GB files)
- Navigating large codebases with semantic structure
- Analyzing log files (especially recent entries with tail mode)
- Making search/replace edits across large files
- Counting occurrences without loading full content

**Don't use for:**

- Small files that fit in context (AI doesn't need help with those)
- Binary files (images, executables, compressed)

## Usage Examples

### Large Codebase Navigation

```pythonß
# Get semantic structure of a large Python file
overview = get_overview("/path/to/large_module.py")
# Returns: 2,847 lines, 15 classes, function outline via Tree-sitter

# Find all class definitions
classes = search_content("/path/to/large_module.py", "class ", fuzzy=False)

# Read complete class with semantic chunking
code = read_content("/path/to/large_module.py", pattern="class UserModel", mode="semantic")
```

### Batch Refactoring

```python
# Preview rename across file
preview = edit_content("/path/to/api.py", changes=[
    {"search": "process_data", "replace": "transform_data"},
    {"search": "old_endpoint", "replace": "new_endpoint"}
], preview=True)

# Apply changes (creates automatic backup)
result = edit_content("/path/to/api.py", changes=[...], preview=False)

# Undo if needed
revert_edit("/path/to/api.py")
```

### Log Analysis

```python
# Get log file overview
overview = get_overview("/var/log/app.log")
# Returns: 150,000 lines, 2.1GB

# Read last 500 lines efficiently
recent = read_content("/var/log/app.log", limit=500, mode="tail")

# Count errors without loading content
error_count = search_content("/var/log/app.log", "ERROR", count_only=True, fuzzy=False)

# Find errors with regex
errors = search_content("/var/log/app.log", r"ERROR.*timeout", regex=True)
```

## Supported Languages

Tree-sitter semantic analysis for: **Python**, **JavaScript/JSX**, **TypeScript/TSX**, **Rust**, **Go**

Other file types use text-based analysis with graceful fallback.

## File Size Handling

| Size     | Strategy                                |
| -------- | --------------------------------------- |
| < 50MB   | Full memory loading with AST caching    |
| 50-500MB | Memory-mapped access                    |
| > 500MB  | Streaming (tail/head modes recommended) |

## Configuration

Environment variables for tuning:

```bash
LARGEFILE_MEMORY_THRESHOLD_MB=50      # RAM loading limit
LARGEFILE_MMAP_THRESHOLD_MB=500       # Memory mapping limit
LARGEFILE_FUZZY_THRESHOLD=0.8         # Match sensitivity (0.0-1.0)
LARGEFILE_MAX_SEARCH_RESULTS=20       # Results per search
LARGEFILE_BACKUP_DIR=~/.largefile/backups
```

## Documentation

- [API Reference](docs/API.md) - Detailed tool documentation
- [Configuration Guide](docs/configuration.md) - All environment variables
- [Examples](docs/examples.md) - More workflow examples
- [Design Document](docs/design.md) - Architecture details
- [Contributing](docs/CONTRIBUTING.md) - Development setup
