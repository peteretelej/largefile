# Largefile Design

## Problem

LLMs cannot work with large files due to context window limitations. Need precise file operations (navigation, search, editing) without loading entire files into memory.

## Solution

Dual-interface tool: CLI commands + MCP server for large file handling.

## Architecture

### Interfaces

**CLI**: `largefile overview|lines|search|structure|edit <file> [options]`  
**MCP Server**: `largefile-mcp` (stdio transport)

### Core Components

```
File � Canonicalize � Hash � Session Management � Tools
                                     �
              File Access (Memory/mmap/Stream)
                     �
         [Navigation] [Search] [Structure] [Edit]
```

## Tools

### MCP Tools (FastMCP)

**Progressive Discovery Workflow:**

**1. Overview Tool** - Start here to understand file scope and structure:
```python
@mcp.tool()
def get_overview(absolute_file_path: str) -> FileOverview
```
Auto-loads file with optimal defaults. Use this first to understand file size, encoding, and available structure types. CRITICAL: Must use absolute file path - relative paths will fail. DO NOT attempt to read large files directly as they exceed context limits.

**2. Navigation Tools** - Locate content of interest:
```python
@mcp.tool()
async def search_content(absolute_file_path: str, pattern: str, max_results: int = 50, context_lines: int = 2, ctx: Context) -> List[SearchResult]

@mcp.tool()
def find_structure(absolute_file_path: str, structure_type: str) -> List[StructureItem]
```
Essential for targeted analysis when you need to focus on specific patterns or structural elements. Returns line numbers for use with get_lines. Auto-loads file if not already loaded.

**3. Targeted Access** - Examine specific content:
```python
@mcp.tool()
def get_lines(absolute_file_path: str, start_line: int, end_line: int = None, context_lines: int = 0) -> str
```
Retrieve specific line ranges identified via search_content or find_structure. Auto-loads file if needed. Use this for detailed examination of located content.

**4. Editing Tool** - Make precise modifications:
```python
@mcp.tool()
def edit_lines(absolute_file_path: str, start_line: int, end_line: int, new_content: str) -> EditResult
```
Atomic line-based editing with backup capability. Use after locating target lines with navigation tools.

**Optional Configuration Tool** - Use ONLY when you need non-default settings:
```python
@mcp.tool()
def load_file(absolute_file_path: str, chunk_size: int = 1000, encoding: str = "utf-8") -> Dict[str, Any]
```
Custom configuration for chunk sizes and encoding. Otherwise, use auto-loading tools with optimal defaults.

### Data Models

```python
@dataclass
class FileOverview:
    line_count: int
    file_size: int
    encoding: str
    structure_types: List[str]

@dataclass
class SearchResult:
    line_number: int
    match: str
    context_before: List[str]
    context_after: List[str]

@dataclass
class StructureItem:
    name: str
    type: str  # "function", "class", "header"
    line_number: int
    end_line: Optional[int]
```

## File Handling

### Access Strategy
- **<10MB**: Memory loading
- **>10MB**: Memory-mapped or streaming
- Line indexing for navigation

### Sessions
- Key: `canonical_path + SHA-256(content)`  
- Change detection via hashing
- Auto-loading with sensible defaults
- Lazy loading with caching

### Path Requirements
- **Absolute paths only** with canonicalization
- Home directory expansion (`~/file` → `/home/user/file`)
- Cross-platform compatibility

## MCP Configuration

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

## Project Structure

```
src/
├── main.py      # CLI entry point
├── server.py    # MCP server  
├── tools.py     # MCP tools
├── engine.py    # File access engine
├── editor.py    # Safe editing operations
└── searcher.py  # Pattern search functionality
```

## Scope

**In**: UTF-8 text files, line-based ops, pattern search, structure detection, atomic editing  
**Out**: Binary files, multi-file ops, collaboration, version control