from dataclasses import dataclass

from .config import config
from .data_models import SimilarMatch
from .exceptions import SearchError
from .file_access import read_file_lines


@dataclass
class SearchMatch:
    line_number: int
    content: str
    similarity_score: float
    match_type: str


def find_exact_matches(lines: list[str], pattern: str) -> list[SearchMatch]:
    """Find exact string matches in file lines."""
    matches = []

    for line_num, line in enumerate(lines, 1):
        if pattern in line:
            matches.append(
                SearchMatch(
                    line_number=line_num,
                    content=line.rstrip("\n\r"),
                    similarity_score=1.0,
                    match_type="exact",
                )
            )

    return matches


def find_fuzzy_matches(
    lines: list[str], pattern: str, threshold: float
) -> list[SearchMatch]:
    """Use rapidfuzz for fuzzy matching."""
    try:
        from rapidfuzz import fuzz
    except ImportError as e:
        raise SearchError("rapidfuzz not installed - fuzzy matching unavailable") from e

    matches = []
    for line_num, line in enumerate(lines, 1):
        similarity = fuzz.ratio(pattern, line.strip()) / 100.0

        if similarity >= threshold:
            matches.append(
                SearchMatch(
                    line_number=line_num,
                    content=line.rstrip("\n\r"),
                    similarity_score=similarity,
                    match_type="fuzzy",
                )
            )

    return sorted(matches, key=lambda x: x.similarity_score, reverse=True)


def combine_results(
    exact_matches: list[SearchMatch], fuzzy_matches: list[SearchMatch]
) -> list[SearchMatch]:
    """Combine exact and fuzzy matches, prioritizing exact matches."""
    exact_line_numbers = {match.line_number for match in exact_matches}

    unique_fuzzy = [
        match for match in fuzzy_matches if match.line_number not in exact_line_numbers
    ]

    combined = exact_matches + unique_fuzzy
    return sorted(combined, key=lambda x: (x.line_number, -x.similarity_score))


def search_file(file_path: str, pattern: str, fuzzy: bool = True) -> list[SearchMatch]:
    """Search file content using auto-detected encoding. Returns clear results or clear errors."""

    try:
        lines = read_file_lines(file_path)
    except Exception as e:
        raise SearchError(f"Cannot read {file_path}: {e}") from e

    exact_matches = find_exact_matches(lines, pattern)
    if exact_matches and not fuzzy:
        return exact_matches

    if fuzzy:
        fuzzy_threshold = config.fuzzy_threshold
        fuzzy_matches = find_fuzzy_matches(lines, pattern, fuzzy_threshold)
        return combine_results(exact_matches, fuzzy_matches)

    return exact_matches


def find_similar_patterns(
    content: str,
    search_text: str,
    limit: int | None = None,
    min_similarity: float | None = None,
) -> list[SimilarMatch]:
    """Find lines similar to search_text using rapidfuzz.

    Used to provide actionable suggestions when search/edit operations fail.

    Args:
        content: File content to search
        search_text: Pattern that wasn't found
        limit: Max matches to return (defaults to config.similar_match_limit)
        min_similarity: Min similarity threshold (defaults to config.similar_match_threshold)

    Returns:
        List of SimilarMatch objects sorted by similarity (highest first)
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return []

    limit = limit if limit is not None else config.similar_match_limit
    min_similarity = (
        min_similarity if min_similarity is not None else config.similar_match_threshold
    )

    lines = content.splitlines()
    candidates: list[SimilarMatch] = []
    search_lines = search_text.splitlines()
    window_size = len(search_lines)

    if window_size == 1:
        # Single line comparison
        for i, line in enumerate(lines):
            similarity = fuzz.ratio(search_text, line) / 100.0
            if similarity >= min_similarity:
                candidates.append(
                    SimilarMatch(
                        line=i + 1,
                        content=line[:100],
                        similarity=round(similarity, 2),
                    )
                )
    else:
        # Multi-line: sliding window comparison
        for i in range(len(lines) - window_size + 1):
            window = "\n".join(lines[i : i + window_size])
            similarity = fuzz.ratio(search_text, window) / 100.0
            if similarity >= min_similarity:
                candidates.append(
                    SimilarMatch(
                        line=i + 1,
                        content=window[:100].replace("\n", "↵"),
                        similarity=round(similarity, 2),
                    )
                )

    candidates.sort(key=lambda x: x.similarity, reverse=True)
    return candidates[:limit]
