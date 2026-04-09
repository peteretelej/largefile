"""Integration tests for get_overview with changed_lines parameter.

Verifies that diff-aware change marking works end-to-end through the
get_overview tool, including backward compatibility, tree-sitter outlines,
simple outlines, error handling, and binary file rejection.
"""

from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.tools import get_overview


class TestGetOverviewDiff:
    """Integration tests for the changed_lines parameter on get_overview."""

    @property
    def test_data_dir(self):
        return Path(__file__).parent.parent / "test_data"

    # ------------------------------------------------------------------ #
    # Backward compatibility
    # ------------------------------------------------------------------ #

    def test_get_overview_without_changed_lines(self, tmp_path: Path):
        """Calling without changed_lines preserves existing behavior."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "def greet(name):\n"
            "    return f'Hello, {name}'\n"
            "\n"
            "def farewell(name):\n"
            "    return f'Goodbye, {name}'\n"
        )

        result = get_overview(str(py_file))

        # No changes field on any outline item
        for item in result["outline"]:
            assert "changes" not in item

        # No changed_symbols key in the response
        assert "changed_symbols" not in result

    # ------------------------------------------------------------------ #
    # Tree-sitter outline (Python)
    # ------------------------------------------------------------------ #

    def test_get_overview_with_changed_lines_python(self, tmp_path: Path):
        """changed_lines marks the correct symbols in a Python file."""
        py_file = tmp_path / "funcs.py"
        py_file.write_text(
            "def alpha():\n"  # line 1
            "    pass\n"  # line 2
            "\n"  # line 3
            "def beta():\n"  # line 4
            "    pass\n"  # line 5
            "\n"  # line 6
            "def gamma():\n"  # line 7
            "    pass\n"  # line 8
        )

        # Mark lines 4-5 as modified (covers beta)
        result = get_overview(str(py_file), changed_lines=[[4, 5, "modified"]])

        assert "changed_symbols" in result
        assert result["changed_symbols"] >= 1

        # Every outline item must carry a 'changes' key
        for item in result["outline"]:
            assert "changes" in item

        # Find beta - it should be marked modified
        beta_items = [i for i in result["outline"] if "beta" in i["name"]]
        assert beta_items, "beta should appear in the outline"
        assert beta_items[0]["changes"] == "modified"

        # alpha should be unaffected
        alpha_items = [i for i in result["outline"] if "alpha" in i["name"]]
        if alpha_items:
            assert alpha_items[0]["changes"] is None

    # ------------------------------------------------------------------ #
    # "added" change type
    # ------------------------------------------------------------------ #

    def test_get_overview_with_changed_lines_added(self, tmp_path: Path):
        """A function fully covered by an 'added' range gets changes='added'."""
        py_file = tmp_path / "added.py"
        py_file.write_text(
            "def existing():\n"  # line 1
            "    pass\n"  # line 2
            "\n"  # line 3
            "def brand_new():\n"  # line 4
            "    return 42\n"  # line 5
        )

        # Mark lines 4-5 as added (fully covers brand_new)
        result = get_overview(str(py_file), changed_lines=[[4, 5, "added"]])

        new_items = [i for i in result["outline"] if "brand_new" in i["name"]]
        assert new_items, "brand_new should appear in the outline"
        assert new_items[0]["changes"] == "added"

    # ------------------------------------------------------------------ #
    # Simple (non-tree-sitter) outline
    # ------------------------------------------------------------------ #

    def test_get_overview_with_changed_lines_simple_outline(self, tmp_path: Path):
        """Non-tree-sitter files still get their simple outline items marked."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text(
            "TODO: Section One\n"  # line 1
            "some text\n"  # line 2
            "\n"  # line 3
            "FIXME: Section Two\n"  # line 4
            "more text\n"  # line 5
        )

        result = get_overview(str(txt_file), changed_lines=[[1, 2, "modified"]])

        # Outline must be non-empty so the loop below is not vacuous
        assert len(result["outline"]) > 0

        # changed_symbols should exist in the response
        assert "changed_symbols" in result

        # All outline items should have the changes key
        for item in result["outline"]:
            assert "changes" in item

        # At least one item should actually be marked as changed
        assert any(item["changes"] is not None for item in result["outline"])

    # ------------------------------------------------------------------ #
    # Error handling: invalid changed_lines
    # ------------------------------------------------------------------ #

    def test_get_overview_invalid_changed_lines_bad_type(self, tmp_path: Path):
        """Non-list element in changed_lines raises ToolError."""
        py_file = tmp_path / "err.py"
        py_file.write_text("x = 1\n")

        with pytest.raises(ToolError, match="Invalid changed_lines"):
            get_overview(str(py_file), changed_lines=["bad"])  # type: ignore[list-item]

    def test_get_overview_invalid_changed_lines_start_gt_end(self, tmp_path: Path):
        """start > end in a range raises ToolError."""
        py_file = tmp_path / "err2.py"
        py_file.write_text("x = 1\n")

        with pytest.raises(ToolError, match="Invalid changed_lines"):
            get_overview(str(py_file), changed_lines=[[10, 5]])

    def test_get_overview_invalid_changed_lines_empty_inner(self, tmp_path: Path):
        """An empty inner list raises ToolError."""
        py_file = tmp_path / "err3.py"
        py_file.write_text("x = 1\n")

        with pytest.raises(ToolError, match="Invalid changed_lines"):
            get_overview(str(py_file), changed_lines=[[]])  # type: ignore[list-item]

    # ------------------------------------------------------------------ #
    # Binary file rejection
    # ------------------------------------------------------------------ #

    def test_get_overview_binary_file_with_changed_lines(self, tmp_path: Path):
        """Providing changed_lines for a binary file raises ToolError."""
        bin_file = tmp_path / "image.png"
        # Write a minimal PNG header to trigger binary detection
        bin_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        with pytest.raises(ToolError, match="changed_lines not supported for binary"):
            get_overview(str(bin_file), changed_lines=[[1, 5]])

    # ------------------------------------------------------------------ #
    # Two-element default type
    # ------------------------------------------------------------------ #

    def test_get_overview_two_element_default_type(self, tmp_path: Path):
        """Two-element changed_lines entries default to 'modified'."""
        py_file = tmp_path / "defaults.py"
        py_file.write_text(
            "def only_func():\n"  # line 1
            "    return True\n"  # line 2
        )

        # No type specified - should default to "modified"
        result = get_overview(str(py_file), changed_lines=[[1, 2]])

        func_items = [i for i in result["outline"] if "only_func" in i["name"]]
        assert func_items, "only_func should appear in the outline"
        assert func_items[0]["changes"] == "modified"
        assert result["changed_symbols"] >= 1
