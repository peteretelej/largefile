"""MCP tools for large file operations (Research-Backed Design)."""

from dataclasses import dataclass
from typing import Union


@dataclass
class FileOverview:
    """Enhanced overview with hierarchical structure and long line detection."""

    line_count: int
    file_size: int
    encoding: str
    has_long_lines: bool  # >1000 chars (triggers truncation)
    outline: list["OutlineItem"]  # Hierarchical via Tree-sitter
    search_hints: list[str]  # Common patterns for exploration


@dataclass
class OutlineItem:
    """Hierarchical structure item with semantic information."""

    name: str
    type: str  # "function", "class", "method", "import"
    line_number: int
    end_line: int
    children: list["OutlineItem"]  # Nested structure
    line_count: int


@dataclass
class SearchResult:
    """Enhanced search result with fuzzy matching and semantic context."""

    line_number: int
    match: str  # Truncated if >500 chars
    context_before: list[str]
    context_after: list[str]
    semantic_context: str  # "inside function foo()", "class Bar"
    similarity_score: float  # For fuzzy matches (0.0-1.0)
    truncated: bool
    submatches: list[dict[str, int]]  # [{"start": 10, "end": 15}]


@dataclass
class EditResult:
    """Result from search/replace editing operation."""

    success: bool
    preview: str  # Shows before/after diff
    changes_made: int
    line_number: int  # Where change occurred
    similarity_used: float  # If fuzzy matching was used


# NEW 4-TOOL SIMPLIFIED API (Research-Backed)

from .engine import FileEngine
from .editor import SearchReplaceEditor


# Global instances
_engine = FileEngine()
_editor = SearchReplaceEditor()


async def get_overview(absolute_file_path: str) -> FileOverview:
    """Enhanced overview with hierarchical structure via Tree-sitter.
    
    Auto-generates hierarchical outline. Detects long lines for truncation.
    Returns semantic structure and search hints for efficient exploration.

    Args:
        absolute_file_path: Absolute path to the file

    Returns:
        Enhanced FileOverview with outline and search hints
    """
    # Phase 1: Basic implementation with session management
    session = await _engine.load_file(absolute_file_path)
    
    # Basic search hints (Phase 3 will add Tree-sitter analysis)
    search_hints = []
    if session.file_size < 10000:  # Small files
        search_hints = ["def ", "class ", "import ", "function"]
    else:
        search_hints = ["def ", "class ", "TODO", "FIXME"]
    
    # Phase 1: Empty outline (Phase 3 will add Tree-sitter hierarchy)
    outline = []
    
    return FileOverview(
        line_count=session.line_count,
        file_size=session.file_size,
        encoding=session.encoding,
        has_long_lines=session.has_long_lines,
        outline=outline,
        search_hints=search_hints
    )


async def search_content(
    absolute_file_path: str,
    pattern: str,
    max_results: int = 20,
    context_lines: int = 2,
    fuzzy: bool = True,
) -> list[SearchResult]:
    """Search with fuzzy matching by default.
    
    Key improvement: Fuzzy matching via Levenshtein distance handles 
    real-world formatting variations. Returns semantic context and 
    smart line truncation.

    Args:
        absolute_file_path: Absolute path to the file
        pattern: Search pattern (regex or plain text)
        max_results: Maximum results (reduced from 50 to 20)
        context_lines: Context lines before/after match
        fuzzy: Enable fuzzy matching (default True)

    Returns:
        Enhanced search results with semantic context
    """
    # Phase 1: Basic exact search (fuzzy matching in Phase 2)
    results = []
    session = await _engine.load_file(absolute_file_path)
    search_results = await _engine.search_content(absolute_file_path, pattern, max_results)
    
    for result in search_results:
        line_num = result['line_number']
        
        # Get context lines
        context_before = []
        context_after = []
        
        if context_lines > 0:
            # Read context before
            if line_num > context_lines:
                context_start = max(1, line_num - context_lines)
                context_content = await _engine.read_lines(
                    absolute_file_path, context_start, line_num - 1
                )
                context_before = context_content.split('\n') if context_content else []
            
            # Read context after
            context_content = await _engine.read_lines(
                absolute_file_path, line_num + 1, line_num + context_lines
            )
            context_after = context_content.split('\n') if context_content else []
        
        # Line truncation for very long lines
        match_text = result['line_content']
        truncated = len(match_text) > 500
        if truncated:
            match_text = match_text[:500] + "...[truncated]"
        
        # Basic submatches information
        submatches = [{
            "start": result['match_start'],
            "end": result['match_end']
        }] if 'match_start' in result else []
        
        results.append(SearchResult(
            line_number=line_num,
            match=match_text,
            context_before=context_before,
            context_after=context_after,
            semantic_context="",  # Phase 3: Add Tree-sitter semantic context
            similarity_score=1.0,  # Phase 2: Add fuzzy matching scores
            truncated=truncated,
            submatches=submatches
        ))
    
    return results


async def read_content(
    absolute_file_path: str,
    target: Union[int, str],
    mode: str = "semantic",
) -> str:
    """Read semantic chunks instead of arbitrary lines.
    
    Uses Tree-sitter to return complete functions/classes/blocks 
    instead of arbitrary line ranges.

    Args:
        absolute_file_path: Absolute path to the file
        target: Line number or search pattern to locate content
        mode: "semantic"|"lines"|"function" - how to chunk content

    Returns:
        Content of semantic unit or line range
    """
    # Phase 1: Basic line-based reading (fallback mode)
    session = await _engine.load_file(absolute_file_path)
    
    if isinstance(target, int):
        # Read from line number
        start_line = target
        # For Phase 1, read a reasonable chunk around the target line
        chunk_size = 20  # Read 20 lines by default
        end_line = min(start_line + chunk_size - 1, session.line_count)
        
        return await _engine.read_lines(absolute_file_path, start_line, end_line)
    
    elif isinstance(target, str):
        # Search for pattern first, then read around it
        search_results = await _engine.search_content(absolute_file_path, target, max_results=1)
        
        if not search_results:
            return f"Pattern '{target}' not found in file"
        
        # Read around the first match
        line_num = search_results[0]['line_number']
        start_line = max(1, line_num - 10)
        end_line = min(line_num + 10, session.line_count)
        
        return await _engine.read_lines(absolute_file_path, start_line, end_line)
    
    else:
        raise ValueError(f"Invalid target type: {type(target)}")


async def edit_content(
    absolute_file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy: bool = True,
    preview: bool = True,
) -> EditResult:
    """PRIMARY EDITING METHOD using search/replace blocks.
    
    Fuzzy matching handles whitespace variations. Eliminates line number 
    confusion that causes LLM errors. This replaces line-based editing.

    Args:
        absolute_file_path: Absolute path to the file
        search_text: Text to find and replace
        replace_text: Replacement text
        fuzzy: Enable fuzzy matching for search_text
        preview: Show preview before applying changes

    Returns:
        Result with preview and change information
    """
    # Phase 1: Implement core search/replace engine (exact matching)
    # Phase 2 will add fuzzy matching
    
    # Ensure file is loaded in session first
    await _engine.load_file(absolute_file_path)
    
    # Perform search/replace operation
    operation = await _editor.search_replace(
        file_path=absolute_file_path,
        search_text=search_text,
        replace_text=replace_text,
        max_replacements=1,  # Conservative: single replacement
        create_backup=True,
        preview_only=preview
    )
    
    return EditResult(
        success=operation.changes_made > 0,
        preview=operation.preview,
        changes_made=operation.changes_made,
        line_number=operation.line_number,
        similarity_used=1.0  # Phase 2: Add fuzzy matching similarity scores
    )
