import re
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


def find_exact_matches(
    lines: list[str],
    pattern: str,
    case_sensitive: bool = True,
    invert: bool = False,
) -> list[SearchMatch]:
    """Find exact string matches in file lines.

    Args:
        lines: File lines to search
        pattern: Pattern to search for
        case_sensitive: Whether to match case (default True)
        invert: Return non-matching lines instead (default False)
    """
    matches = []
    search_pattern = pattern if case_sensitive else pattern.lower()

    for line_num, line in enumerate(lines, 1):
        line_content = line.rstrip("\n\r")
        compare_line = line_content if case_sensitive else line_content.lower()
        is_match = search_pattern in compare_line

        if invert:
            is_match = not is_match

        if is_match:
            match_type = "exact" if not invert else "exact_inverted"
            matches.append(
                SearchMatch(
                    line_number=line_num,
                    content=line_content,
                    similarity_score=1.0,
                    match_type=match_type,
                )
            )

    return matches


def find_fuzzy_matches(
    lines: list[str],
    pattern: str,
    threshold: float,
    invert: bool = False,
) -> list[SearchMatch]:
    """Use rapidfuzz for fuzzy matching.

    Args:
        lines: File lines to search
        pattern: Pattern to search for
        threshold: Minimum similarity score (0.0-1.0)
        invert: Return lines below threshold instead (default False)
    """
    try:
        from rapidfuzz import fuzz
    except ImportError as e:
        raise SearchError("rapidfuzz not installed - fuzzy matching unavailable") from e

    matches = []
    for line_num, line in enumerate(lines, 1):
        line_content = line.rstrip("\n\r")
        similarity = fuzz.ratio(pattern, line.strip()) / 100.0
        is_match = similarity >= threshold

        if invert:
            is_match = not is_match

        if is_match:
            match_type = "fuzzy" if not invert else "fuzzy_inverted"
            matches.append(
                SearchMatch(
                    line_number=line_num,
                    content=line_content,
                    similarity_score=similarity,
                    match_type=match_type,
                )
            )

    return sorted(matches, key=lambda x: x.similarity_score, reverse=True)


def find_regex_matches(
    lines: list[str],
    pattern: str,
    case_sensitive: bool = True,
    invert: bool = False,
) -> list[SearchMatch]:
    """Find lines matching a regex pattern.

    Args:
        lines: File lines to search
        pattern: Regular expression pattern
        case_sensitive: Whether to match case (default True)
        invert: Return non-matching lines instead (default False)

    Raises:
        SearchError: If regex pattern is invalid
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        raise SearchError(f"Invalid regex pattern: {e}") from e

    matches = []
    for line_num, line in enumerate(lines, 1):
        line_content = line.rstrip("\n\r")
        is_match = compiled.search(line_content) is not None

        if invert:
            is_match = not is_match

        if is_match:
            match_type = "regex" if not invert else "regex_inverted"
            matches.append(
                SearchMatch(
                    line_number=line_num,
                    content=line_content,
                    similarity_score=1.0,
                    match_type=match_type,
                )
            )

    return matches


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


def search_file(
    file_path: str,
    pattern: str,
    fuzzy: bool = True,
    regex: bool = False,
    case_sensitive: bool = True,
    invert: bool = False,
) -> list[SearchMatch]:
    """Search file content using auto-detected encoding.

    Args:
        file_path: Path to file to search
        pattern: Search pattern
        fuzzy: Enable fuzzy matching (default True)
        regex: Enable regex matching (default False)
        case_sensitive: Case sensitive search (default True)
        invert: Return non-matching lines (default False)

    Raises:
        SearchError: If regex and fuzzy are both True, or invalid regex
    """
    # Validate parameter combinations
    if regex and fuzzy:
        raise SearchError("Cannot use regex and fuzzy together")

    try:
        lines = read_file_lines(file_path)
    except Exception as e:
        raise SearchError(f"Cannot read {file_path}: {e}") from e

    # Route to appropriate matcher
    if regex:
        return find_regex_matches(lines, pattern, case_sensitive, invert)

    if fuzzy:
        fuzzy_threshold = config.fuzzy_threshold
        fuzzy_matches = find_fuzzy_matches(lines, pattern, fuzzy_threshold, invert)
        if not invert:
            # For non-inverted fuzzy, also check exact matches
            exact_matches = find_exact_matches(lines, pattern, case_sensitive, invert)
            return combine_results(exact_matches, fuzzy_matches)
        return fuzzy_matches

    # Exact match mode
    return find_exact_matches(lines, pattern, case_sensitive, invert)


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
