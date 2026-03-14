"""Unit tests for the search_directory tool function."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.exceptions import FileAccessError, SearchError
from src.tools import search_directory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tree(base: Path, structure: dict) -> None:
    """Recursively create files/dirs described by *structure*.

    Keys ending in '/' are directories; other keys are files.
    Values for files are the byte-string content; values for dirs are
    nested structure dicts.
    """
    for name, content in structure.items():
        if name.endswith("/"):
            child = base / name.rstrip("/")
            child.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                _make_tree(child, content)
        else:
            (base / name).write_bytes(
                content if isinstance(content, bytes) else content.encode()
            )


# ---------------------------------------------------------------------------
# TestSearchDirectoryErrors  — invalid inputs / wrong path types
# ---------------------------------------------------------------------------


class TestSearchDirectoryErrors:
    def test_nonexistent_path_returns_error(self, tmp_path: Path) -> None:
        with pytest.raises(ToolError, match="Not a directory"):
            search_directory(str(tmp_path / "does_not_exist"), "pattern")

    def test_file_path_returns_error(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.txt"
        f.write_text("hello")
        with pytest.raises(ToolError, match="Not a directory"):
            search_directory(str(f), "hello")

    def test_invalid_max_results_zero_returns_error(self, tmp_path: Path) -> None:
        with pytest.raises(ToolError, match="max_results"):
            search_directory(str(tmp_path), "x", max_results=0)

    def test_invalid_max_results_negative_returns_error(self, tmp_path: Path) -> None:
        with pytest.raises(ToolError, match="max_results"):
            search_directory(str(tmp_path), "x", max_results=-5)


# ---------------------------------------------------------------------------
# TestSearchDirectoryBasic  — happy path, return dict shape
# ---------------------------------------------------------------------------


class TestSearchDirectoryBasic:
    def test_empty_directory_returns_zero_matches(self, tmp_path: Path) -> None:
        result = search_directory(str(tmp_path), "anything")
        assert result["total_matches"] == 0
        assert result["files_searched"] == 0
        assert result["files_with_matches"] == 0
        assert result["results"] == []
        assert result["truncated"] is False
        assert result["truncated_at"] is None

    def test_returns_expected_top_level_keys(self, tmp_path: Path) -> None:
        result = search_directory(str(tmp_path), "x")
        expected = {
            "path",
            "pattern",
            "include_pattern",
            "total_matches",
            "files_searched",
            "files_with_matches",
            "truncated",
            "truncated_at",
            "results",
        }
        assert set(result.keys()) == expected

    def test_finds_pattern_in_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world\nsecond line\n")
        result = search_directory(str(tmp_path), "hello", fuzzy=False)
        assert result["total_matches"] == 1
        assert result["files_with_matches"] == 1
        assert result["files_searched"] == 1
        assert result["results"][0]["file"] == "hello.txt"
        assert result["results"][0]["matches"][0]["line_number"] == 1

    def test_finds_pattern_across_multiple_files(self, tmp_path: Path) -> None:
        _make_tree(
            tmp_path,
            {
                "a.txt": b"needle here\n",
                "b.txt": b"nothing here\n",
                "c.txt": b"also needle\n",
            },
        )
        result = search_directory(str(tmp_path), "needle", fuzzy=False)
        assert result["total_matches"] == 2
        assert result["files_with_matches"] == 2
        assert result["files_searched"] == 3

    def test_no_match_returns_empty_results(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("nothing relevant\n")
        result = search_directory(str(tmp_path), "XYZZY_NOT_THERE", fuzzy=False)
        assert result["total_matches"] == 0
        assert result["results"] == []

    def test_result_file_paths_are_relative(self, tmp_path: Path) -> None:
        _make_tree(tmp_path, {"sub/": {"deep.txt": b"target\n"}})
        result = search_directory(str(tmp_path), "target", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert all(not os.path.isabs(f) for f in files)

    def test_result_file_paths_use_forward_slashes(self, tmp_path: Path) -> None:
        """Relative paths must use '/' even on Windows."""
        _make_tree(tmp_path, {"sub/": {"deep.txt": b"target\n"}})
        result = search_directory(str(tmp_path), "target", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert all("\\" not in f for f in files)
        assert any("sub/" in f for f in files)

    def test_path_in_result_matches_input(self, tmp_path: Path) -> None:
        result = search_directory(str(tmp_path), "x")
        assert result["path"] == str(tmp_path)

    def test_pattern_and_include_pattern_echoed(self, tmp_path: Path) -> None:
        result = search_directory(str(tmp_path), "myterm", include_pattern="*.py")
        assert result["pattern"] == "myterm"
        assert result["include_pattern"] == "*.py"

    def test_match_object_has_expected_keys(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("line with match\n")
        result = search_directory(str(tmp_path), "match", fuzzy=False)
        m = result["results"][0]["matches"][0]
        assert set(m.keys()) == {
            "line_number",
            "match",
            "context_before",
            "context_after",
            "similarity_score",
            "match_type",
            "truncated",
        }


# ---------------------------------------------------------------------------
# TestSearchDirectoryFiltering  — include_pattern, include_hidden, ignored dirs
# ---------------------------------------------------------------------------


class TestSearchDirectoryFiltering:
    def test_include_pattern_filters_by_extension(self, tmp_path: Path) -> None:
        _make_tree(
            tmp_path,
            {
                "code.py": b"needle\n",
                "notes.txt": b"needle\n",
                "readme.md": b"needle\n",
            },
        )
        result = search_directory(
            str(tmp_path), "needle", include_pattern="*.py", fuzzy=False
        )
        files = [g["file"] for g in result["results"]]
        assert files == ["code.py"]

    def test_include_pattern_star_matches_all(self, tmp_path: Path) -> None:
        _make_tree(tmp_path, {"a.py": b"x\n", "b.txt": b"x\n"})
        result = search_directory(str(tmp_path), "x", include_pattern="*", fuzzy=False)
        assert result["files_with_matches"] == 2

    def test_hidden_files_excluded_by_default(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden").write_text("secret needle\n")
        (tmp_path / "visible.txt").write_text("other content\n")
        result = search_directory(str(tmp_path), "needle", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert ".hidden" not in files

    def test_hidden_files_included_when_requested(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden").write_text("secret needle\n")
        result = search_directory(
            str(tmp_path), "needle", include_hidden=True, fuzzy=False
        )
        files = [g["file"] for g in result["results"]]
        assert ".hidden" in files

    def test_ignored_dir_pycache_skipped(self, tmp_path: Path) -> None:
        _make_tree(
            tmp_path,
            {
                "__pycache__/": {"cached.pyc": b"needle\n"},
                "src/": {"app.py": b"other\n"},
            },
        )
        result = search_directory(str(tmp_path), "needle", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert not any("__pycache__" in f for f in files)

    def test_ignored_dir_node_modules_skipped(self, tmp_path: Path) -> None:
        _make_tree(
            tmp_path,
            {
                "node_modules/": {"lib.js": b"needle\n"},
                "src/": {"index.js": b"other\n"},
            },
        )
        result = search_directory(str(tmp_path), "needle", fuzzy=False)
        files = [g["file"] for g in result["results"]]
        assert not any("node_modules" in f for f in files)

    def test_context_lines_included(self, tmp_path: Path) -> None:
        (tmp_path / "multi.txt").write_text("before\nmatch_target\nafter\n")
        result = search_directory(
            str(tmp_path), "match_target", context_lines=1, fuzzy=False
        )
        m = result["results"][0]["matches"][0]
        assert m["context_before"] == ["before"]
        assert m["context_after"] == ["after"]


# ---------------------------------------------------------------------------
# TestSearchDirectoryTruncation  — max_results cap and truncated flag
# ---------------------------------------------------------------------------


class TestSearchDirectoryTruncation:
    def test_truncation_at_max_results(self, tmp_path: Path) -> None:
        for i in range(10):
            (tmp_path / f"file{i:02d}.txt").write_text("needle\n")
        result = search_directory(str(tmp_path), "needle", max_results=3, fuzzy=False)
        assert result["total_matches"] == 3
        assert result["truncated"] is True

    def test_truncated_flag_set_on_cap(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text("x\n")
        result = search_directory(str(tmp_path), "x", max_results=2, fuzzy=False)
        assert result["truncated"] is True
        assert result["truncated_at"] is not None

    def test_no_truncation_when_under_limit(self, tmp_path: Path) -> None:
        for i in range(3):
            (tmp_path / f"f{i}.txt").write_text("needle\n")
        result = search_directory(str(tmp_path), "needle", max_results=100, fuzzy=False)
        assert result["truncated"] is False
        assert result["truncated_at"] is None
        assert result["total_matches"] == 3

    def test_truncated_at_is_relative_forward_slash(self, tmp_path: Path) -> None:
        _make_tree(
            tmp_path, {"sub/": {"a.txt": b"x\n", "b.txt": b"x\n", "c.txt": b"x\n"}}
        )
        result = search_directory(str(tmp_path), "x", max_results=1, fuzzy=False)
        if result["truncated_at"] is not None:
            assert "\\" not in result["truncated_at"]

    def test_mid_file_truncation(self, tmp_path: Path) -> None:
        """max_results reached inside a file with multiple matches."""
        (tmp_path / "many.txt").write_text("needle\nneedle\nneedle\n")
        result = search_directory(str(tmp_path), "needle", max_results=2, fuzzy=False)
        assert result["total_matches"] == 2
        assert result["truncated"] is True
        assert result["truncated_at"] == "many.txt"


# ---------------------------------------------------------------------------
# TestSearchDirectorySearchModes  — fuzzy, regex, case_sensitive, invert
# ---------------------------------------------------------------------------


class TestSearchDirectorySearchModes:
    def test_case_insensitive_by_default(self, tmp_path: Path) -> None:
        """Default is case-insensitive."""
        (tmp_path / "f.txt").write_text("Hello World\n")
        result = search_directory(str(tmp_path), "hello world", fuzzy=False)
        assert result["total_matches"] == 1

    def test_case_insensitive_when_requested(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("Hello World\n")
        result = search_directory(
            str(tmp_path), "hello world", case_sensitive=False, fuzzy=False
        )
        assert result["total_matches"] == 1

    def test_regex_mode(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("error: code 404\ninfo: all good\n")
        result = search_directory(
            str(tmp_path), r"error: code \d+", regex=True, fuzzy=False
        )
        assert result["total_matches"] == 1

    def test_invert_mode(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("line1\nDEBUG: skip me\nline3\n")
        result = search_directory(str(tmp_path), "DEBUG", invert=True, fuzzy=False)
        # 2 non-DEBUG lines
        assert result["total_matches"] == 2

    def test_fuzzy_mode_finds_approximate_match(self, tmp_path: Path) -> None:
        # fuzzy=True also runs exact matching; write a line that is an exact match
        # to verify the fuzzy routing path returns results
        (tmp_path / "f.txt").write_text("def process_data(x):\n    pass\n")
        result = search_directory(str(tmp_path), "process_data", fuzzy=True)
        assert result["total_matches"] >= 1

    def test_max_files_cap_truncates(self, tmp_path: Path) -> None:
        """files_visited > max_dir_search_files sets truncated=True and stops the walk."""
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text("x\n")

        with patch("src.tools.config") as mock_cfg:
            mock_cfg.max_dir_search_files = 2
            mock_cfg.max_dir_search_results = 100
            mock_cfg.ignored_dir_patterns = []
            result = search_directory(str(tmp_path), "x", fuzzy=False)

        assert result["truncated"] is True
        assert result["files_with_matches"] <= 2


# ---------------------------------------------------------------------------
# TestSearchDirectoryErrorPaths  — OS errors, binary/unreadable files
# ---------------------------------------------------------------------------


class TestSearchDirectoryErrorPaths:
    def test_unreadable_file_is_skipped_silently(self, tmp_path: Path) -> None:
        """FileAccessError from search_file (unreadable / binary) causes the file to be skipped."""
        (tmp_path / "good.txt").write_text("needle\n")
        (tmp_path / "bad.txt").write_text("needle\n")

        real_search = __import__(
            "src.search_engine", fromlist=["search_file"]
        ).search_file
        call_count = {"n": 0}

        def patched_search(path: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            call_count["n"] += 1
            if "bad.txt" in path:
                raise FileAccessError("Cannot read bad.txt: access denied")
            return real_search(path, *args, **kwargs)

        with patch("src.tools.search_file", side_effect=patched_search):
            result = search_directory(str(tmp_path), "needle", fuzzy=False)

        # bad.txt skipped; good.txt still found
        assert result["files_with_matches"] == 1
        assert result["total_matches"] == 1
        files = [g["file"] for g in result["results"]]
        assert "good.txt" in files
        assert "bad.txt" not in files

    def test_files_searched_does_not_count_skipped_files(self, tmp_path: Path) -> None:
        """Files that raise FileAccessError on search_file are not counted in files_searched."""
        (tmp_path / "a.txt").write_text("x\n")
        (tmp_path / "b.txt").write_text("x\n")

        def patched_search(path: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if "b.txt" in path:
                raise FileAccessError("Cannot read b.txt: denied")
            return []

        with patch("src.tools.search_file", side_effect=patched_search):
            result = search_directory(str(tmp_path), "x", fuzzy=False)

        assert result["files_searched"] == 1

    def test_read_file_lines_failure_yields_empty_context(self, tmp_path: Path) -> None:
        """If read_file_lines fails after a match is found, context is empty."""
        (tmp_path / "f.txt").write_text("needle\n")

        with patch(
            "src.tools.read_file_lines",
            side_effect=FileAccessError("read failed"),
        ):
            result = search_directory(str(tmp_path), "needle", fuzzy=False)

        assert result["total_matches"] == 1
        m = result["results"][0]["matches"][0]
        assert m["context_before"] == []
        assert m["context_after"] == []

    def test_search_error_propagates_as_tool_error(self, tmp_path: Path) -> None:
        """SearchError propagates through @handle_tool_errors as ToolError."""
        (tmp_path / "f.txt").write_text("some content\n")

        with patch(
            "src.tools.search_file",
            side_effect=SearchError("regex+fuzzy not allowed"),
        ):
            with pytest.raises(ToolError, match="regex\\+fuzzy not allowed"):
                search_directory(str(tmp_path), ".*", regex=True)

    def test_invalid_regex_raises_tool_error(self, tmp_path: Path) -> None:
        """An invalid regex pattern raises ToolError."""
        (tmp_path / "f.txt").write_text("hello\n")
        with pytest.raises(ToolError, match="Search failed"):
            search_directory(str(tmp_path), "[unclosed", regex=True)
