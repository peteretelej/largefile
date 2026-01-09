from dataclasses import dataclass, field


@dataclass
class SimilarMatch:
    """A similar pattern found when search fails."""

    line: int
    content: str  # Truncated to 100 chars
    similarity: float  # 0.0-1.0


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
    # Enhanced error fields
    search_attempted: str | None = None
    fuzzy_enabled: bool | None = None
    similar_matches: list[SimilarMatch] = field(default_factory=list)
    suggestion: str | None = None
