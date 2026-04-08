"""Unit tests for the change_marker module.

Covers parse_changed_lines, classify_change, mark_outline,
and the changed_count return value.
"""

import pytest

from src.change_marker import classify_change, mark_outline, parse_changed_lines
from src.data_models import OutlineItem

# ---------------------------------------------------------------------------
# parse_changed_lines
# ---------------------------------------------------------------------------


class TestParseChangedLines:
    """Validation, sorting, and merging of raw changed-line input."""

    def test_two_element_defaults_to_modified(self):
        result = parse_changed_lines([[10, 15]])
        assert result == [(10, 15, "modified")]

    def test_three_element_preserves_type(self):
        result = parse_changed_lines([[10, 15, "added"]])
        assert result == [(10, 15, "added")]

    def test_mixed_two_and_three_element(self):
        result = parse_changed_lines([[1, 5], [10, 20, "removed"]])
        assert result == [(1, 5, "modified"), (10, 20, "removed")]

    def test_invalid_start_greater_than_end(self):
        with pytest.raises(ValueError, match="start.*<=.*end"):
            parse_changed_lines([[15, 10]])

    def test_invalid_negative_start(self):
        with pytest.raises(ValueError, match="start must be >= 1"):
            parse_changed_lines([[0, 5]])

    def test_invalid_bad_type_string(self):
        with pytest.raises(ValueError, match="type must be one of"):
            parse_changed_lines([[1, 5, "deleted"]])

    def test_invalid_wrong_length_one(self):
        with pytest.raises(ValueError, match="2 or 3 elements"):
            parse_changed_lines([[5]])

    def test_invalid_wrong_length_four(self):
        with pytest.raises(ValueError, match="2 or 3 elements"):
            parse_changed_lines([[1, 2, "added", "extra"]])

    def test_invalid_non_integer_start(self):
        with pytest.raises(ValueError, match="integers"):
            parse_changed_lines([["a", 5]])

    def test_invalid_non_integer_end(self):
        with pytest.raises(ValueError, match="integers"):
            parse_changed_lines([[1, "b"]])

    def test_sorting_unsorted_input(self):
        result = parse_changed_lines([[20, 25], [1, 5], [10, 15]])
        starts = [r[0] for r in result]
        assert starts == [1, 10, 20]

    def test_merge_adjacent_same_type(self):
        # 1-5 and 6-10 are adjacent (end >= start - 1)
        result = parse_changed_lines([[1, 5], [6, 10]])
        assert result == [(1, 10, "modified")]

    def test_merge_overlapping_same_type(self):
        result = parse_changed_lines([[1, 8], [5, 12]])
        assert result == [(1, 12, "modified")]

    def test_no_merge_different_type_overlapping(self):
        result = parse_changed_lines([[1, 10, "added"], [5, 15, "modified"]])
        assert len(result) == 2
        assert result[0] == (1, 10, "added")
        assert result[1] == (5, 15, "modified")

    def test_empty_input(self):
        result = parse_changed_lines([])
        assert result == []

    def test_single_line_range(self):
        result = parse_changed_lines([[5, 5]])
        assert result == [(5, 5, "modified")]

    def test_merge_multiple_adjacent(self):
        result = parse_changed_lines([[1, 2], [3, 4], [5, 6]])
        assert result == [(1, 6, "modified")]


# ---------------------------------------------------------------------------
# classify_change
# ---------------------------------------------------------------------------


class TestClassifyChange:
    """Overlap detection and classification logic."""

    def test_fully_inside_added_range(self):
        ranges = [(1, 20, "added")]
        assert classify_change(5, 10, ranges) == "added"

    def test_fully_covered_by_multiple_adjacent_added(self):
        ranges = [(1, 5, "added"), (6, 10, "added")]
        assert classify_change(1, 10, ranges) == "added"

    def test_partially_overlapping_added_not_fully_covered(self):
        ranges = [(5, 10, "added")]
        assert classify_change(1, 10, ranges) == "modified"

    def test_only_removed_ranges(self):
        ranges = [(1, 10, "removed")]
        assert classify_change(3, 7, ranges) == "removed"

    def test_mixed_added_and_modified(self):
        ranges = [(1, 5, "added"), (6, 10, "modified")]
        assert classify_change(1, 10, ranges) == "modified"

    def test_no_overlap(self):
        ranges = [(1, 5, "modified")]
        assert classify_change(10, 20, ranges) is None

    def test_single_line_symbol_overlapping(self):
        ranges = [(5, 10, "added")]
        assert classify_change(5, 5, ranges) == "added"

    def test_single_line_symbol_no_overlap(self):
        ranges = [(5, 10, "added")]
        assert classify_change(4, 4, ranges) is None

    def test_symbol_spanning_multiple_same_type(self):
        ranges = [(1, 3, "modified"), (7, 10, "modified")]
        assert classify_change(1, 10, ranges) == "modified"

    def test_empty_ranges(self):
        assert classify_change(1, 10, []) is None

    def test_symbol_exactly_matches_range(self):
        ranges = [(5, 10, "added")]
        assert classify_change(5, 10, ranges) == "added"

    def test_removed_multiple_ranges(self):
        ranges = [(1, 5, "removed"), (8, 12, "removed")]
        assert classify_change(1, 12, ranges) == "removed"

    def test_added_with_gap_means_modified(self):
        # Two added ranges that don't fully cover the symbol
        ranges = [(1, 3, "added"), (7, 10, "added")]
        assert classify_change(1, 10, ranges) == "modified"


# ---------------------------------------------------------------------------
# mark_outline
# ---------------------------------------------------------------------------


def _make_item(name: str, line_start: int, line_end: int) -> OutlineItem:
    """Helper to create a minimal OutlineItem."""
    return OutlineItem(
        name=name,
        type="function",
        line_number=line_start,
        end_line=line_end,
        children=[],
        line_count=line_end - line_start + 1,
    )


class TestMarkOutline:
    """Flat outline marking and count tracking."""

    def test_some_items_overlap(self):
        items = [_make_item("a", 1, 10), _make_item("b", 20, 30)]
        ranges = [(5, 15, "modified")]
        result_items, count = mark_outline(items, ranges)
        assert result_items[0].changes == "modified"
        assert result_items[1].changes is None
        assert count == 1

    def test_empty_outline(self):
        items, count = mark_outline([], [(1, 10, "modified")])
        assert items == []
        assert count == 0

    def test_no_overlap_all_none(self):
        items = [_make_item("a", 1, 5), _make_item("b", 10, 15)]
        ranges = [(50, 60, "added")]
        _, count = mark_outline(items, ranges)
        assert count == 0
        assert all(item.changes is None for item in items)

    def test_multiple_items_multiple_ranges(self):
        items = [
            _make_item("a", 1, 10),
            _make_item("b", 15, 25),
            _make_item("c", 30, 40),
        ]
        ranges = [(1, 10, "added"), (20, 22, "modified")]
        result_items, count = mark_outline(items, ranges)
        assert result_items[0].changes == "added"
        assert result_items[1].changes == "modified"
        assert result_items[2].changes is None
        assert count == 2

    def test_does_not_recurse_into_children(self):
        """Children in the flat list are separate top-level entries.

        mark_outline should not touch item.children directly.
        """
        child = _make_item("child", 5, 8)
        parent = OutlineItem(
            name="parent",
            type="class",
            line_number=1,
            end_line=20,
            children=[child],
            line_count=20,
        )
        # Only pass the parent, not the child (simulating non-flattened case)
        # child should remain untouched
        ranges = [(1, 20, "modified")]
        result_items, count = mark_outline([parent], ranges)
        assert result_items[0].changes == "modified"
        # The child was NOT in the top-level list, so it stays None
        assert child.changes is None
        assert count == 1

    def test_mutates_in_place(self):
        items = [_make_item("a", 1, 10)]
        ranges = [(1, 10, "added")]
        result_items, _ = mark_outline(items, ranges)
        assert result_items is items
        assert items[0].changes == "added"


class TestMarkOutlineChangedCount:
    """Verify returned count matches items with non-None changes."""

    def test_count_matches_marked_items(self):
        items = [
            _make_item("a", 1, 10),
            _make_item("b", 15, 25),
            _make_item("c", 30, 40),
            _make_item("d", 50, 60),
        ]
        ranges = [(1, 10, "added"), (30, 40, "removed")]
        _, count = mark_outline(items, ranges)
        marked = sum(1 for item in items if item.changes is not None)
        assert count == marked == 2

    def test_count_zero_when_no_changes(self):
        items = [_make_item("a", 1, 10)]
        _, count = mark_outline(items, [(100, 200, "modified")])
        assert count == 0

    def test_count_all_when_everything_changed(self):
        items = [_make_item("a", 1, 10), _make_item("b", 11, 20)]
        _, count = mark_outline(items, [(1, 20, "modified")])
        assert count == 2
