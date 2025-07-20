"""Search/replace engine with fuzzy matching and atomic operations."""

import difflib
import os

from .config import config
from .data_models import EditResult
from .exceptions import EditError
from .file_access import normalize_path, read_file_content, write_file_content


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
            # No matches found
            return EditResult(
                success=False,
                preview=f"No matches found for: {search_text}",
                changes_made=0,
                line_number=0,
                similarity_used=0.0,
                match_type="none",
            )
    else:
        # No matches found
        return EditResult(
            success=False,
            preview=f"No exact matches found for: {search_text}",
            changes_made=0,
            line_number=0,
            similarity_used=0.0,
            match_type="none",
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

        backup_path = create_backup(canonical_path)

        # Write new content atomically
        write_file_content(canonical_path, modified_content)

        result.backup_created = backup_path
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
