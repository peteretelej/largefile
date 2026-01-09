# Configuration Guide

Environment-based configuration for the Largefile MCP Server.

## Overview

Largefile uses environment variables for all configuration to keep MCP tool signatures clean and simple. Set these variables before starting your MCP client.

## File Processing

### Memory Thresholds

Control how files are accessed based on size:

```bash
# Memory loading threshold (default: 50MB)
LARGEFILE_MEMORY_THRESHOLD_MB=50

# Memory mapping threshold (default: 500MB)  
LARGEFILE_MMAP_THRESHOLD_MB=500
```

**File Access Strategy:**
- **< 50MB**: Loaded into memory with Tree-sitter AST caching
- **50-500MB**: Memory-mapped access with streaming search
- **> 500MB**: Chunk-based streaming processing

### Line Handling

Configure line truncation for very long lines:

```bash
# Trigger truncation for lines longer than this (default: 1000)
LARGEFILE_MAX_LINE_LENGTH=1000

# Display length for truncated lines (default: 500)
LARGEFILE_TRUNCATE_LENGTH=500
```

**Behavior:**
- Lines exceeding `MAX_LINE_LENGTH` are truncated in overview and search results
- Original file content is never modified
- Full content available via `read_content` tool

## Search Configuration

### Fuzzy Matching

Control fuzzy search sensitivity and behavior:

```bash
# Minimum similarity score for fuzzy matches (default: 0.8)
LARGEFILE_FUZZY_THRESHOLD=0.8

# Maximum search results returned (default: 20)
LARGEFILE_MAX_SEARCH_RESULTS=20

# Context lines before/after matches (default: 2)
LARGEFILE_CONTEXT_LINES=2
```

**Fuzzy Threshold Values:**
- `1.0`: Exact matches only
- `0.9`: Very strict fuzzy matching
- `0.8`: Balanced (default) - handles typos and formatting
- `0.7`: Loose matching - more results, lower precision
- `< 0.7`: Not recommended - too many false positives

### Performance Settings

```bash
# Chunk size for streaming large files (default: 8192 bytes)
LARGEFILE_STREAMING_CHUNK_SIZE=8192

# Enable parallel processing for multi-pattern search (default: true)
LARGEFILE_ENABLE_PARALLEL_SEARCH=true
```

## Tree-sitter Configuration

Control semantic analysis features:

```bash
# Enable/disable Tree-sitter parsing (default: true)
LARGEFILE_ENABLE_TREE_SITTER=true

# Maximum time for AST parsing (default: 5 seconds)
LARGEFILE_TREE_SITTER_TIMEOUT=5

# Cache parsed ASTs for session reuse (default: true)
LARGEFILE_ENABLE_AST_CACHE=true
```

**When to Disable Tree-sitter:**
- Working primarily with non-code text files
- Memory constraints in containerized environments
- Parsing timeouts on very large or complex files
- Language not supported (falls back to text-based analysis)

## Backup and Safety

Configure automatic backup behavior:

```bash
# Directory for edit backups (default: ~/.largefile/backups)
LARGEFILE_BACKUP_DIR="/path/to/backups"

# Maximum number of backups to keep per file (default: 10)
LARGEFILE_MAX_BACKUPS=10
```

**Backup Behavior:**
- Automatic backup created before every edit operation
- Backups named: `{filename}.{path_hash}.{timestamp}` for uniqueness
- Old backups automatically cleaned up based on `MAX_BACKUPS`
- Use `revert_edit` tool to restore any backup

**Backup Naming Convention:**
```
example.py.a1b2c3d4.20240115_143022
│         │        │
│         │        └── Timestamp (YYYYMMDD_HHMMSS)
│         └── Path hash (first 8 chars of SHA-256)
└── Original filename
```

## Error Recovery

Configure enhanced error messages when edits fail:

```bash
# Maximum similar matches to show on edit failure (default: 3)
LARGEFILE_SIMILAR_MATCH_LIMIT=3

# Minimum similarity score to include in suggestions (default: 0.6)
LARGEFILE_SIMILAR_MATCH_THRESHOLD=0.6
```

**Error Recovery Behavior:**
- When `edit_content` fails to find a pattern, it searches for similar lines
- Returns up to `SIMILAR_MATCH_LIMIT` suggestions with similarity scores
- Only shows matches above `SIMILAR_MATCH_THRESHOLD` (0.0-1.0 scale)
- Includes actionable suggestion like "Did you mean X on line Y?"

## Batch Editing

Configure batch edit limits:

```bash
# Maximum changes per batch edit call (default: 50)
LARGEFILE_MAX_BATCH_CHANGES=50
```

**Batch Editing Behavior:**
- Prevents excessively large batch operations
- All changes in a batch share a single backup
- Partial success is supported (some changes can fail)
- Per-change results include individual error details

## Logging and Debug

Control logging output and debug information:

```bash
# Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
LARGEFILE_LOG_LEVEL=INFO

# Enable performance metrics logging (default: false)
LARGEFILE_ENABLE_METRICS=false

# Log file path (default: stderr)
LARGEFILE_LOG_FILE="/path/to/largefile.log"
```

**Debug Mode:**
```bash
# Enable all debug features
LARGEFILE_LOG_LEVEL=DEBUG
LARGEFILE_ENABLE_METRICS=true
LARGEFILE_TREE_SITTER_TIMEOUT=10
```

## Example Configurations

### High-Performance Setup

For fast machines with plenty of memory:

```bash
# Larger memory thresholds
LARGEFILE_MEMORY_THRESHOLD_MB=200
LARGEFILE_MMAP_THRESHOLD_MB=2000

# More aggressive search
LARGEFILE_MAX_SEARCH_RESULTS=50
LARGEFILE_FUZZY_THRESHOLD=0.7

# Larger chunks for streaming
LARGEFILE_STREAMING_CHUNK_SIZE=65536

# Extended timeouts
LARGEFILE_TREE_SITTER_TIMEOUT=10
```

### Memory-Constrained Environment

For containers or low-memory systems:

```bash
# Conservative memory usage
LARGEFILE_MEMORY_THRESHOLD_MB=10
LARGEFILE_MMAP_THRESHOLD_MB=50

# Disable caching
LARGEFILE_ENABLE_AST_CACHE=false

# Smaller chunks
LARGEFILE_STREAMING_CHUNK_SIZE=4096

# Stricter search limits
LARGEFILE_MAX_SEARCH_RESULTS=10
LARGEFILE_CONTEXT_LINES=1
```

### Text-Only Processing

For non-code files or when Tree-sitter isn't needed:

```bash
# Disable semantic features
LARGEFILE_ENABLE_TREE_SITTER=false
LARGEFILE_ENABLE_AST_CACHE=false

# Focus on text search performance
LARGEFILE_FUZZY_THRESHOLD=0.8
LARGEFILE_MAX_SEARCH_RESULTS=30
LARGEFILE_ENABLE_PARALLEL_SEARCH=true
```

### Development and Testing

For debugging and development:

```bash
# Verbose logging
LARGEFILE_LOG_LEVEL=DEBUG
LARGEFILE_ENABLE_METRICS=true

# Preserve all data
LARGEFILE_MAX_BACKUPS_PER_FILE=100
LARGEFILE_COMPRESS_BACKUPS=false

# Detailed truncation
LARGEFILE_MAX_LINE_LENGTH=500
LARGEFILE_TRUNCATE_LENGTH=200
```

## Configuration Validation

Check your configuration:

```bash
# Verify environment variables are set
env | grep LARGEFILE_

# Test with a sample file
echo "test content" > test.txt
# Use get_overview tool to verify settings are working
```

**Common Issues:**
- **Memory errors**: Reduce `MEMORY_THRESHOLD_MB`
- **Slow performance**: Increase chunk sizes or disable Tree-sitter
- **Too many/few search results**: Adjust `FUZZY_THRESHOLD` and `MAX_SEARCH_RESULTS`
- **Backup failures**: Check `BACKUP_DIR` permissions

## Performance Tuning

### Memory Optimization

1. **Profile your typical file sizes** - set thresholds appropriately
2. **Monitor memory usage** - enable metrics to track consumption
3. **Adjust AST caching** - disable for very large codebases
4. **Use streaming** - for files that don't need semantic analysis

### Search Optimization

1. **Tune fuzzy threshold** - balance precision vs recall
2. **Limit context lines** - reduce for performance, increase for clarity
3. **Use exact matching** - when possible for fastest results
4. **Parallel search** - enable for multi-pattern workflows

### File Handling

1. **SSD storage** - dramatically improves memory-mapped performance
2. **Backup location** - use fast storage for backup directory
3. **Compression** - enable for backup storage efficiency
4. **Cleanup frequency** - adjust max backups based on usage

See [Performance Documentation](performance.md) for detailed benchmarks and optimization guides.