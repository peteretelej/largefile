"""Search/replace engine with fuzzy matching and atomic operations."""

import difflib
import os

from .config import config
from .data_models import Change, ChangeResult, EditResult, SimilarMatch
from .exceptions import EditError
from .file_access import normalize_path, read_file_content, write_file_content
from .search_engine import find_similar_patterns


def generate_diff_preview(original: str, modified: str, search_text: str) -> str:
    """Generate a diff preview showing before/after changes."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="original",
            tofile="modified",
            lineterm="",
            n=3,
        )
    )

    if not diff_lines:
        return "No changes detected"

    # Format the diff for better readability
    preview_lines = []
    for line in diff_lines[2:]:  # Skip file headers
        if line.startswith("@@"):
            preview_lines.append(line)
        elif line.startswith("-"):
            preview_lines.append(f"  {line}")
        elif line.startswith("+"):
            preview_lines.append(f"  {line}")
        else:
            preview_lines.append(f"  {line}")

    return "\n".join(preview_lines)


def generate_suggestion(
    similar_matches: list[SimilarMatch], fuzzy_enabled: bool
) -> str:
    """Generate actionable suggestion based on similar matches found.

    Args:
        similar_matches: List of similar patterns found in the file
        fuzzy_enabled: Whether fuzzy matching was enabled for the search

    Returns:
        Actionable suggestion string for the LLM
    """
    if not similar_matches:
        if fuzzy_enabled:
            return (
                "No similar patterns found. Verify the search text exists in the file."
            )
        return "No similar patterns found. Try enabling fuzzy matching."

    if fuzzy_enabled:
        return f"Found {len(similar_matches)} similar pattern(s). Use one as your search text."

    best = similar_matches[0]
    if best.similarity > 0.9:
        return f"Found near-match at line {best.line}. Enable fuzzy matching or use exact text."
    return f"Found {len(similar_matches)} similar pattern(s). Enable fuzzy matching for partial matches."


def fuzzy_replace_content(
    content: str, search_text: str, replace_text: str
) -> tuple[str, float]:
    """Perform fuzzy search and replace on content."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError as e:
        raise EditError("rapidfuzz not installed - fuzzy matching unavailable") from e

    lines = content.splitlines()

    # Find the best matching line
    choices = [(line, i) for i, line in enumerate(lines)]
    line_texts = [line for line, _ in choices]

    result = process.extractOne(
        search_text,
        line_texts,
        scorer=fuzz.ratio,
        score_cutoff=config.fuzzy_threshold * 100,
    )

    if not result:
        raise EditError(f"No fuzzy match found for: {search_text}")

    best_match, similarity_score, line_index = result
    similarity = similarity_score / 100.0

    # Replace the matched line
    lines[line_index] = replace_text
    modified_content = "\n".join(lines)

    return modified_content, similarity


def find_best_match_location(
    content: str, search_text: str, fuzzy: bool = True
) -> tuple[int, str, float, str] | None:
    """Find the best match location and return line number, content, similarity, and type."""
    lines = content.splitlines()

    # Try exact match first
    for i, line in enumerate(lines):
        if search_text in line:
            return i + 1, line, 1.0, "exact"

    if not fuzzy:
        return None

    # Try fuzzy matching
    try:
        from rapidfuzz import fuzz
    except ImportError as e:
        raise EditError("rapidfuzz not installed - fuzzy matching unavailable") from e

    best_similarity = 0.0
    best_line_num = 0
    best_line_content = ""

    for i, line in enumerate(lines):
        similarity = fuzz.ratio(search_text, line.strip()) / 100.0
        if similarity >= config.fuzzy_threshold and similarity > best_similarity:
            best_similarity = similarity
            best_line_num = i + 1
            best_line_content = line

    if best_line_num > 0:
        return best_line_num, best_line_content, best_similarity, "fuzzy"

    return None


def replace_content(
    file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy: bool = True,
    preview: bool = True,
) -> EditResult:
    """Replace content using search/replace with auto-detected encoding. Returns clear results or errors."""
    canonical_path = normalize_path(file_path)

    # Read original content
    try:
        original_content = read_file_content(canonical_path)
    except Exception as e:
        raise EditError(f"Cannot read {file_path}: {e}") from e

    # Find matches (exact first, then fuzzy if enabled)
    if search_text in original_content:
        # Exact match found
        modified_content = original_content.replace(search_text, replace_text, 1)
        match_type = "exact"
        similarity = 1.0
        line_number = (
            original_content[: original_content.find(search_text)].count("\n") + 1
        )
    elif fuzzy:
        # Try fuzzy replacement
        try:
            modified_content, similarity = fuzzy_replace_content(
                original_content, search_text, replace_text
            )
            match_type = "fuzzy"

            # Find line number for the change
            match_result = find_best_match_location(
                original_content, search_text, fuzzy=True
            )
            line_number = match_result[0] if match_result else 0
        except EditError:
            # No matches found - find similar patterns for helpful error
            similar = find_similar_patterns(original_content, search_text)
            suggestion = generate_suggestion(similar, fuzzy_enabled=True)
            return EditResult(
                success=False,
                preview=f"No matches found for: {search_text}",
                changes_made=0,
                line_number=0,
                similarity_used=0.0,
                match_type="none",
                search_attempted=search_text,
                fuzzy_enabled=True,
                similar_matches=similar,
                suggestion=suggestion,
            )
    else:
        # No matches found - find similar patterns for helpful error
        similar = find_similar_patterns(original_content, search_text)
        suggestion = generate_suggestion(similar, fuzzy_enabled=False)
        return EditResult(
            success=False,
            preview=f"No exact matches found for: {search_text}",
            changes_made=0,
            line_number=0,
            similarity_used=0.0,
            match_type="none",
            search_attempted=search_text,
            fuzzy_enabled=False,
            similar_matches=similar,
            suggestion=suggestion,
        )

    # Generate preview
    preview_text = generate_diff_preview(
        original_content, modified_content, search_text
    )

    result = EditResult(
        success=True,
        preview=preview_text,
        changes_made=1,
        line_number=line_number,
        similarity_used=similarity,
        match_type=match_type,
    )

    if preview:
        return result

    # Make actual changes atomically
    try:
        # Create backup first
        from .file_access import create_backup

        backup_info = create_backup(canonical_path)

        # Write new content atomically
        write_file_content(canonical_path, modified_content)

        result.backup_created = backup_info.path
        return result

    except Exception as e:
        raise EditError(f"Failed to write changes to {file_path}: {e}") from e


def validate_search_replace_params(search_text: str, replace_text: str) -> None:
    """Validate search/replace parameters."""
    if not search_text:
        raise EditError("Search text cannot be empty")

    if search_text == replace_text:
        raise EditError("Search text and replace text are identical")

    if len(search_text) > 10000:
        raise EditError("Search text too long (max 10000 characters)")

    if len(replace_text) > 10000:
        raise EditError("Replace text too long (max 10000 characters)")


def atomic_edit_file(
    file_path: str,
    search_text: str,
    replace_text: str,
    fuzzy: bool = True,
    preview: bool = True,
) -> EditResult:
    """PRIMARY EDITING METHOD using search/replace blocks with validation and auto-detected encoding."""
    # Validate parameters
    validate_search_replace_params(search_text, replace_text)

    # Normalize path
    canonical_path = normalize_path(file_path)

    # Check file exists and is writable
    if not os.path.exists(canonical_path):
        raise EditError(f"File does not exist: {file_path}")

    if not os.access(canonical_path, os.R_OK):
        raise EditError(f"File is not readable: {file_path}")

    if not preview and not os.access(canonical_path, os.W_OK):
        raise EditError(f"File is not writable: {file_path}")

    # Perform the edit operation
    return replace_content(canonical_path, search_text, replace_text, fuzzy, preview)


def find_match_with_position(
    content: str, search_text: str, fuzzy: bool = True
) -> tuple[int, int, int, str, float] | None:
    """Find match and return (start_pos, end_pos, line_number, match_type, similarity).

    Returns None if no match found.
    """
    # Try exact match first
    start = content.find(search_text)
    if start != -1:
        end = start + len(search_text)
        line_number = content[:start].count("\n") + 1
        return start, end, line_number, "exact", 1.0

    if not fuzzy:
        return None

    # Try fuzzy matching - find the best matching line
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return None

    lines = content.splitlines(keepends=True)
    best_similarity = 0.0
    best_line_idx = -1
    best_line_content = ""

    for i, line in enumerate(lines):
        similarity = fuzz.ratio(search_text, line.rstrip("\n\r")) / 100.0
        if similarity >= config.fuzzy_threshold and similarity > best_similarity:
            best_similarity = similarity
            best_line_idx = i
            best_line_content = line

    if best_line_idx < 0:
        return None

    # Calculate positions
    start = sum(len(lines[j]) for j in range(best_line_idx))
    end = start + len(best_line_content)
    line_number = best_line_idx + 1

    return start, end, line_number, "fuzzy", best_similarity


def apply_batch_edits(
    content: str, changes: list[Change], default_fuzzy: bool
) -> tuple[str, list[ChangeResult]]:
    """Apply multiple edits atomically with partial success semantics.

    Returns modified content and per-change results.
    Some edits can fail without blocking others.
    """
    results: list[ChangeResult] = []
    pending_edits: list[
        tuple[int, int, int, str, int, str, float]
    ] = []  # (index, start, end, replacement, line_num, match_type, similarity)

    # Phase 1: Locate all matches
    for i, change in enumerate(changes):
        use_fuzzy = change.fuzzy if change.fuzzy is not None else default_fuzzy
        match = find_match_with_position(content, change.search, use_fuzzy)

        if match is None:
            # Find similar patterns for error message
            similar = find_similar_patterns(content, change.search, limit=3)
            results.append(
                ChangeResult(
                    index=i,
                    success=False,
                    error="Pattern not found",
                    similar_matches=similar if similar else None,
                )
            )
            continue

        start, end, line_num, match_type, similarity = match
        pending_edits.append(
            (i, start, end, change.replace, line_num, match_type, similarity)
        )
        results.append(
            ChangeResult(
                index=i,
                success=True,  # Tentative - may fail overlap check
                line_number=line_num,
                match_type=match_type,
                similarity=similarity,
            )
        )

    # Phase 2: Detect overlaps (sort by start position)
    pending_edits.sort(key=lambda x: x[1])
    valid_edits: list[tuple[int, int, int, str, int, str, float]] = []

    for edit in pending_edits:
        idx, start, end, replacement, line_num, match_type, similarity = edit

        # Check overlap with previous valid edit
        if valid_edits and start < valid_edits[-1][2]:
            # Overlap detected - mark as failed
            for r in results:
                if r.index == idx:
                    r.success = False
                    r.error = f"Overlaps with change {valid_edits[-1][0]}"
                    break
            continue

        valid_edits.append(edit)

    # Phase 3: Apply edits (bottom-to-top to preserve positions)
    valid_edits.sort(key=lambda x: x[1], reverse=True)

    for (
        _idx,
        start,
        end,
        replacement,
        _line_num,
        _match_type,
        _similarity,
    ) in valid_edits:
        content = content[:start] + replacement + content[end:]

    return content, results


def batch_edit_content(
    file_path: str,
    changes: list[Change],
    fuzzy: bool = True,
    preview: bool = True,
) -> EditResult:
    """Apply multiple edits to a file atomically."""
    canonical_path = normalize_path(file_path)

    # Check file exists and is readable
    if not os.path.exists(canonical_path):
        raise EditError(f"File does not exist: {file_path}")

    if not os.access(canonical_path, os.R_OK):
        raise EditError(f"File is not readable: {file_path}")

    if not preview and not os.access(canonical_path, os.W_OK):
        raise EditError(f"File is not writable: {file_path}")

    # Read original content
    try:
        original_content = read_file_content(canonical_path)
    except Exception as e:
        raise EditError(f"Cannot read {file_path}: {e}") from e

    # Apply batch edits
    modified_content, change_results = apply_batch_edits(
        original_content, changes, fuzzy
    )

    # Count successes and failures
    changes_applied = sum(1 for r in change_results if r.success)
    changes_failed = sum(1 for r in change_results if not r.success)

    # Generate unified diff preview
    preview_text = generate_diff_preview(original_content, modified_content, "batch")

    result = EditResult(
        success=changes_applied > 0,
        preview=preview_text,
        changes_made=changes_applied,
        line_number=0,  # Not applicable for batch
        similarity_used=0.0,  # Not applicable for batch
        match_type="batch",
        changes_applied=changes_applied,
        changes_failed=changes_failed,
        results=change_results,
    )

    if preview:
        return result

    # Make actual changes atomically
    try:
        from .file_access import create_backup

        backup_info = create_backup(canonical_path)
        write_file_content(canonical_path, modified_content)
        result.backup_created = backup_info.path
        return result

    except Exception as e:
        raise EditError(f"Failed to write changes to {file_path}: {e}") from e
