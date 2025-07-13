from dataclasses import dataclass


@dataclass
class FileOverview:
    line_count: int
    file_size: int
    encoding: str
    has_long_lines: bool
    outline: list["OutlineItem"]
    search_hints: list[str]


@dataclass
class OutlineItem:
    name: str
    type: str
    line_number: int
    end_line: int
    children: list["OutlineItem"]
    line_count: int


@dataclass
class SearchResult:
    line_number: int
    match: str
    context_before: list[str]
    context_after: list[str]
    semantic_context: str
    similarity_score: float
    truncated: bool
    submatches: list[dict[str, int]]


@dataclass
class EditResult:
    success: bool
    preview: str
    changes_made: int
    line_number: int
    similarity_used: float
    match_type: str = "exact"
    backup_created: str | None = None
