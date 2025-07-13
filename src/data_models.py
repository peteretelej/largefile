from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class FileOverview:
    line_count: int
    file_size: int
    encoding: str
    has_long_lines: bool
    outline: List['OutlineItem']
    search_hints: List[str]


@dataclass
class OutlineItem:
    name: str
    type: str
    line_number: int
    end_line: int
    children: List['OutlineItem']
    line_count: int


@dataclass
class SearchResult:
    line_number: int
    match: str
    context_before: List[str]
    context_after: List[str]
    semantic_context: str
    similarity_score: float
    truncated: bool
    submatches: List[Dict[str, int]]


@dataclass
class EditResult:
    success: bool
    preview: str
    changes_made: int
    line_number: int
    similarity_used: float
    match_type: str = "exact"
    backup_created: Optional[str] = None