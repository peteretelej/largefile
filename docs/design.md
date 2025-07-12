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

```python
@mcp.tool()
def get_overview(file_path: str) -> FileOverview

@mcp.tool()
def get_lines(file_path: str, start_line: int, end_line: int = None, context_lines: int = 0) -> str

@mcp.tool()
async def search_content(file_path: str, pattern: str, max_results: int = 50, ctx: Context) -> List[SearchResult]

@mcp.tool()
def find_structure(file_path: str, structure_type: str) -> List[StructureItem]

@mcp.tool()
def edit_lines(file_path: str, start_line: int, end_line: int, new_content: str) -> EditResult
```

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
- Lazy loading with caching

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

## Scope

**In**: UTF-8 text files, line-based ops, pattern search, structure detection, atomic editing  
**Out**: Binary files, multi-file ops, collaboration, version control