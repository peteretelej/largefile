from typing import List
from dataclasses import dataclass

from .config import config
from .file_access import read_file_lines
from .exceptions import SearchError


@dataclass
class SearchMatch:
    line_number: int
    content: str
    similarity_score: float
    match_type: str


def find_exact_matches(lines: List[str], pattern: str) -> List[SearchMatch]:
    """Find exact string matches in file lines."""
    matches = []
    
    for line_num, line in enumerate(lines, 1):
        if pattern in line:
            matches.append(SearchMatch(
                line_number=line_num,
                content=line.rstrip('\n\r'),
                similarity_score=1.0,
                match_type="exact"
            ))
    
    return matches


def find_fuzzy_matches(lines: List[str], pattern: str, threshold: float) -> List[SearchMatch]:
    """Use rapidfuzz for fuzzy matching."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        raise SearchError("rapidfuzz not installed - fuzzy matching unavailable")
    
    matches = []
    for line_num, line in enumerate(lines, 1):
        similarity = fuzz.ratio(pattern, line.strip()) / 100.0
        
        if similarity >= threshold:
            matches.append(SearchMatch(
                line_number=line_num,
                content=line.rstrip('\n\r'),
                similarity_score=similarity,
                match_type="fuzzy"
            ))
    
    return sorted(matches, key=lambda x: x.similarity_score, reverse=True)


def combine_results(exact_matches: List[SearchMatch], fuzzy_matches: List[SearchMatch]) -> List[SearchMatch]:
    """Combine exact and fuzzy matches, prioritizing exact matches."""
    exact_line_numbers = {match.line_number for match in exact_matches}
    
    unique_fuzzy = [match for match in fuzzy_matches 
                   if match.line_number not in exact_line_numbers]
    
    combined = exact_matches + unique_fuzzy
    return sorted(combined, key=lambda x: (x.line_number, -x.similarity_score))


def search_file(file_path: str, pattern: str, encoding: str = "utf-8", 
                fuzzy: bool = True) -> List[SearchMatch]:
    """Search file content. Returns clear results or clear errors."""
    
    try:
        lines = read_file_lines(file_path, encoding)
    except Exception as e:
        raise SearchError(f"Cannot read {file_path}: {e}")
    
    exact_matches = find_exact_matches(lines, pattern)
    if exact_matches and not fuzzy:
        return exact_matches
    
    if fuzzy:
        fuzzy_threshold = config.fuzzy_threshold
        fuzzy_matches = find_fuzzy_matches(lines, pattern, fuzzy_threshold)
        return combine_results(exact_matches, fuzzy_matches)
    
    return exact_matches