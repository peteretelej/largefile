# Technical Analysis: Large File APIs for LLMs

## Core Findings

**Context limits shape everything**: GitHub Copilot (128K), Claude (200K), but files regularly exceed 1M+ lines. Different tools take different approaches:

- **Cursor**: Abandoned diffs for full rewrites with speculative decoding at 1000 tokens/sec
- **Aider**: Uses search/replace blocks with fuzzy matching, proven more reliable than line numbers
- **RooCode/Cline**: Implements middle-out fuzzy matching with Levenshtein distance
- **WindSurf**: Focuses on contextual awareness with its Cascade system

**Edit format evolution**: Line numbers are problematic for LLMs. Successful patterns:

- Search/replace blocks (<<<<<<< SEARCH / >>>>>>> REPLACE) - used by Aider, Cline, RooCode
- Unified diffs without line numbers - 3X reduction in "lazy coding" for GPT-4 Turbo
- Fuzzy matching essential - exact string matching fails due to whitespace, formatting variations

**Optimal chunk size**: 300-500 tokens with 20% overlap preserves context. Tree-sitter for semantic boundaries beats line-based splitting.

**Search patterns**: Ripgrep's JSON format became the standard. Key: return line numbers + context windows, not full content.

## Lessons from Production Tools

### Fuzzy Matching Strategy (RooCode/Cline)

```python
# Middle-out search when exact match fails:
1. Estimate region (use line number hints)
2. Expand search outwards
3. Score with Levenshtein distance
4. Select best match above threshold
```

### Edit Formats That Work

- **Search/Replace blocks**: Most reliable, avoids line numbers entirely
- **Unified diffs**: Good but strip line numbers (@@ -2,4 +3,5 @@ → ignore)
- **Whole file**: Works but wastes tokens on unchanged code

### Why Line Numbers Fail

- LLMs trained on code without line annotations
- Tokenization breaks on numbers
- Off-by-one errors compound in large files
- Dynamic code changes invalidate absolute positions

## Recommendations for `largefile` MCP

### 1. Enhance Search API with Fuzzy Matching

Current:

```python
def search_content(absolute_file_path: str, pattern: str, max_results: int = 50, context_lines: int = 2)
```

Recommended:

```python
def search_content(
    absolute_file_path: str,
    pattern: str,
    max_results: int = 50,
    context_lines: int = 2,
    max_line_length: int = 500,  # Truncate long lines
    fuzzy_threshold: float = 0.8,  # Levenshtein similarity
    semantic_type: bool = False  # Add AST context
) -> List[SearchResult]:
    # Support both exact and fuzzy matching
    # Return ripgrep-style submatches
```

Enhanced SearchResult:

```python
@dataclass
class SearchResult:
    line_number: int
    match: str  # Truncated if > max_line_length
    context_before: List[str]
    context_after: List[str]
    submatches: List[Dict[str, int]]  # [{start: 10, end: 15}]
    truncated: bool
    similarity_score: float  # For fuzzy matches
    semantic_context: Optional[str]  # "inside function foo()"
```

### 2. Add Hierarchical Navigation

New tool for progressive exploration:

```python
@mcp.tool()
def get_outline(
    absolute_file_path: str,
    max_depth: int = 2,
    include_line_counts: bool = True
) -> List[OutlineItem]:
    """Get hierarchical file structure with size hints"""
    # Use Tree-sitter for language-aware parsing
    # Return nested structure with line spans
```

### 3. Smart Chunking for `get_lines`

Current approach is pure line-based. Add semantic awareness:

```python
@mcp.tool()
def get_semantic_chunk(
    absolute_file_path: str,
    line_number: int,
    chunk_mode: str = "auto"  # auto|function|class|block
) -> ChunkResult:
    """Get semantic unit containing line"""
    # Use Tree-sitter to find enclosing function/class
    # Return complete semantic unit, not arbitrary lines
```

### 4. Efficient Structure Finding

Enhance structure detection with caching:

```python
def find_structure(
    absolute_file_path: str,
    structure_type: str,
    pattern: Optional[str] = None  # Filter by name pattern
) -> List[StructureItem]:
    # Cache parsed AST per session
    # Support: function|class|method|import|comment_block
```

### 5. Line Truncation Strategy

For files with extremely long lines (minified JS, data files):

```python
def get_lines(...) -> str:
    # If line > 1000 chars:
    # Return: "line content start...[truncated 95000 chars]...end"
    # Add get_full_line(file, line_num) for expansion
```

### 6. Add Search Refinement

```python
@mcp.tool()
def refine_search(
    absolute_file_path: str,
    previous_results: List[int],  # Line numbers from prior search
    new_pattern: str,
    expand_context: int = 10
) -> List[SearchResult]:
    """Search within regions around previous results"""
```

### 7. Add Search/Replace Editing (Alternative to Line-Based)

```python
@mcp.tool()
def replace_content(
    absolute_file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy_match: bool = True,
    max_replacements: int = 1
) -> ReplaceResult:
    """Search/replace editing that avoids line numbers entirely"""
    # Use fuzzy matching with configurable threshold
    # Return preview of changes before applying
```

This provides an alternative to `edit_lines` that's proven more reliable for LLMs.

1. **Line truncation** - Critical for handling minified files
2. **Enhanced search with submatches** - Improves LLM understanding
3. **Semantic chunks** - Better than arbitrary line ranges
4. **Tree-sitter integration** - Enables all structure features
5. **Hierarchical outline** - Natural exploration pattern

## API Design Principles

- **Auto-load by default**: Keep current approach, it's correct
- **Return metadata, not content**: Line numbers + summaries for overview
- **Progressive disclosure**: Overview → search → examine → edit
- **Fail gracefully**: Handle 100K+ char lines without OOM
- **Cache aggressively**: AST parsing is expensive

## Skip These Patterns

- **Line-number based editing** - Proven unreliable across all tools
- **Vector search**: Overkill for single-file tool
- **Complex JSON edit formats** - Simple text formats more reliable
- **Multi-file operations**: Keep scope focused
- **Real-time indexing**: Session-based caching sufficient
- **Forcing exact matches**: Fuzzy matching is essential for real-world code
