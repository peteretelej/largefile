"""Change-marking logic for diff-aware file overviews.

Classifies outline symbols as added, modified, or removed based on
changed line ranges from a diff.
"""

from __future__ import annotations

from .data_models import OutlineItem

# (start_line, end_line, change_type)
# change_type: "added" | "modified" | "removed"
ChangedLineRange = tuple[int, int, str]

_VALID_CHANGE_TYPES = frozenset({"added", "modified", "removed"})


def parse_changed_lines(raw: list[list[int | str]]) -> list[ChangedLineRange]:
    """Validate and convert JSON input to internal ``ChangedLineRange`` list.

    Each element of *raw* is ``[start, end]`` or ``[start, end, type]``.
    When *type* is omitted it defaults to ``"modified"``.

    After validation the ranges are sorted by start line and adjacent /
    overlapping ranges **of the same type** are merged.
    """
    validated: list[ChangedLineRange] = []

    for entry in raw:
        if not isinstance(entry, list | tuple) or len(entry) not in (2, 3):
            raise ValueError(
                f"Each entry must have 2 or 3 elements, got {len(entry) if isinstance(entry, list | tuple) else type(entry).__name__}"
            )

        start = entry[0]
        end = entry[1]
        change_type: str = str(entry[2]) if len(entry) == 3 else "modified"

        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(
                f"start and end must be integers, got {type(start).__name__} and {type(end).__name__}"
            )
        if start < 1:
            raise ValueError(f"start must be >= 1, got {start}")
        if start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")
        if change_type not in _VALID_CHANGE_TYPES:
            raise ValueError(
                f"type must be one of {sorted(_VALID_CHANGE_TYPES)}, got {change_type!r}"
            )

        validated.append((start, end, change_type))

    # Sort by start line
    validated.sort(key=lambda r: r[0])

    # Merge overlapping / adjacent ranges of the same type
    merged: list[ChangedLineRange] = []
    for rng in validated:
        if merged and merged[-1][2] == rng[2] and merged[-1][1] >= rng[0] - 1:
            # Extend the previous range
            prev = merged[-1]
            merged[-1] = (prev[0], max(prev[1], rng[1]), prev[2])
        else:
            merged.append(rng)

    return merged


def classify_change(
    symbol_start: int,
    symbol_end: int,
    changed_ranges: list[ChangedLineRange],
) -> str | None:
    """Determine the change classification for a single symbol.

    Returns ``"added"``, ``"modified"``, ``"removed"``, or ``None``.
    """
    overlapping: list[ChangedLineRange] = [
        r for r in changed_ranges if r[0] <= symbol_end and r[1] >= symbol_start
    ]

    if not overlapping:
        return None

    types = {r[2] for r in overlapping}

    if types == {"removed"}:
        return "removed"

    if types == {"added"}:
        # Check full coverage: compute union of overlapping added ranges
        # clipped to symbol bounds
        symbol_len = symbol_end - symbol_start + 1
        covered = _union_coverage(overlapping, symbol_start, symbol_end)
        if covered == symbol_len:
            return "added"
        return "modified"

    # Mixed types
    return "modified"


def _union_coverage(
    ranges: list[ChangedLineRange], clip_start: int, clip_end: int
) -> int:
    """Compute the total number of lines covered by *ranges* within [clip_start, clip_end]."""
    clipped = []
    for start, end, _ in ranges:
        cs = max(start, clip_start)
        ce = min(end, clip_end)
        if cs <= ce:
            clipped.append((cs, ce))

    if not clipped:
        return 0

    clipped.sort()
    total = 0
    cur_start, cur_end = clipped[0]
    for s, e in clipped[1:]:
        if s <= cur_end + 1:
            cur_end = max(cur_end, e)
        else:
            total += cur_end - cur_start + 1
            cur_start, cur_end = s, e
    total += cur_end - cur_start + 1
    return total


def mark_outline(
    items: list[OutlineItem],
    changed_ranges: list[ChangedLineRange],
) -> tuple[list[OutlineItem], int]:
    """Classify each item in a flat outline list and set its ``changes`` field.

    The list returned by ``generate_outline()`` is already flattened via
    ``_flatten_outline_items()``, so children appear as top-level entries.
    This function does **not** recurse into ``item.children`` to avoid
    double-counting.

    Returns ``(items, changed_count)`` - items are mutated in place.
    """
    changed_count = 0
    for item in items:
        result = classify_change(item.line_number, item.end_line, changed_ranges)
        item.changes = result
        if result is not None:
            changed_count += 1
    return items, changed_count
