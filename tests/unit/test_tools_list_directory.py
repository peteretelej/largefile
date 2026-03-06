"""Unit tests for the list_directory tool function."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.tools import list_directory

# ---------------------------------------------------------------------------
# TestListDirectoryErrors
# ---------------------------------------------------------------------------


class TestListDirectoryErrors:
    def test_raises_on_nonexistent_path(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path / "does_not_exist"))
        assert "error" in result
        assert "Not a directory" in result["error"]

    def test_raises_on_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.txt"
        f.write_text("x")
        result = list_directory(str(f))
        assert "error" in result
        assert "Not a directory" in result["error"]

    def test_invalid_max_depth_zero(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path), max_depth=0)
        assert "error" in result
        assert "max_depth" in result["error"]

    def test_invalid_max_depth_negative(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path), max_depth=-1)
        assert "error" in result
        assert "max_depth" in result["error"]

    def test_invalid_max_entries_zero(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path), max_entries=0)
        assert "error" in result
        assert "max_entries" in result["error"]

    def test_invalid_max_entries_negative(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path), max_entries=-5)
        assert "error" in result
        assert "max_entries" in result["error"]


# ---------------------------------------------------------------------------
# TestListDirectoryBasic
# ---------------------------------------------------------------------------


class TestListDirectoryBasic:
    def test_empty_directory(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path))
        assert result["entries"] == []
        assert result["total_files"] == 0
        assert result["total_dirs"] == 0
        assert result["truncated"] is False
        assert result["truncated_at"] is None

    def test_returns_expected_keys(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path))
        expected = {
            "path",
            "entries",
            "total_files",
            "total_dirs",
            "truncated",
            "truncated_at",
        }
        assert set(result.keys()) == expected

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_bytes(b"hello")
        result = list_directory(str(tmp_path))
        assert result["total_files"] == 1
        assert result["total_dirs"] == 0
        entries = result["entries"]
        assert len(entries) == 1
        assert entries[0]["name"] == "hello.txt"
        assert entries[0]["type"] == "file"
        assert entries[0]["size_bytes"] == 5
        assert entries[0]["child_count"] is None

    def test_single_subdir(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "a.txt").write_text("a")
        result = list_directory(str(tmp_path))
        assert result["total_dirs"] == 1
        assert result["total_files"] == 0
        entries = result["entries"]
        assert len(entries) == 1
        assert entries[0]["name"] == "subdir"
        assert entries[0]["type"] == "dir"
        assert entries[0]["child_count"] == 1

    def test_dirs_listed_before_files(self, tmp_path: Path) -> None:
        (tmp_path / "aaa.txt").write_text("")
        (tmp_path / "zzz/").mkdir(parents=True, exist_ok=True)
        result = list_directory(str(tmp_path))
        types = [e["type"] for e in result["entries"]]
        # First entry should be the dir even though 'aaa' < 'zzz'
        assert types[0] == "dir"
        assert types[1] == "file"

    def test_path_in_result(self, tmp_path: Path) -> None:
        result = list_directory(str(tmp_path))
        assert result["path"] == str(tmp_path)


# ---------------------------------------------------------------------------
# TestListDirectoryHidden
# ---------------------------------------------------------------------------


class TestListDirectoryHidden:
    def test_hides_dotfiles_by_default(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden").write_text("secret")
        (tmp_path / "visible.txt").write_text("ok")
        result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert ".hidden" not in names
        assert "visible.txt" in names

    def test_shows_dotfiles_when_requested(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden").write_text("secret")
        result = list_directory(str(tmp_path), include_hidden=True)
        names = [e["name"] for e in result["entries"]]
        assert ".hidden" in names


# ---------------------------------------------------------------------------
# TestListDirectoryIgnoredPatterns
# ---------------------------------------------------------------------------


class TestListDirectoryIgnoredPatterns:
    def test_default_ignores_pycache(self, tmp_path: Path) -> None:
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "src").mkdir()
        result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert "__pycache__" not in names
        assert "src" in names

    def test_default_ignores_node_modules(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules").mkdir()
        result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert "node_modules" not in names

    def test_default_ignores_dotgit(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        result = list_directory(str(tmp_path), include_hidden=True)
        names = [e["name"] for e in result["entries"]]
        assert ".git" not in names

    def test_file_named_like_ignored_pattern_is_not_skipped(
        self, tmp_path: Path
    ) -> None:
        """A file named '__pycache__' must still appear in listings."""
        (tmp_path / "__pycache__").write_text("I am a file")
        result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert "__pycache__" in names

    def test_dir_named_like_ignored_pattern_is_still_skipped(
        self, tmp_path: Path
    ) -> None:
        """A directory named '__pycache__' must be skipped."""
        (tmp_path / "__pycache__").mkdir()
        result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert "__pycache__" not in names

    def test_child_count_includes_file_named_like_ignored_pattern(
        self, tmp_path: Path
    ) -> None:
        """child_count must count files whose name matches an ignored pattern."""
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "__pycache__").write_text("I am a file")
        (parent / "regular.txt").write_text("ok")
        result = list_directory(str(tmp_path))
        entry = next(e for e in result["entries"] if e["name"] == "parent")
        assert entry["child_count"] == 2

    def test_empty_env_var_disables_all_ignore_patterns(self, tmp_path: Path) -> None:
        """LARGEFILE_IGNORED_DIR_PATTERNS='' must not produce a spurious [''] pattern."""
        with patch.dict(os.environ, {"LARGEFILE_IGNORED_DIR_PATTERNS": ""}):
            from src.config import Config

            cfg = Config()
        assert cfg.ignored_dir_patterns == []


# ---------------------------------------------------------------------------
# TestListDirectoryDepth
# ---------------------------------------------------------------------------


class TestListDirectoryDepth:
    def test_depth_1_does_not_recurse(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_text("deep")
        # depth=1: only 'sub' appears, not 'deep.txt'
        result = list_directory(str(tmp_path), max_depth=1)
        names = [e["name"] for e in result["entries"]]
        assert "sub" in names
        assert "deep.txt" not in names

    def test_depth_2_includes_children(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_text("deep")
        result = list_directory(str(tmp_path), max_depth=2)
        names = [e["name"] for e in result["entries"]]
        assert "sub" in names
        assert "sub/deep.txt" in names


# ---------------------------------------------------------------------------
# TestListDirectoryChildCount
# ---------------------------------------------------------------------------


class TestListDirectoryChildCount:
    def test_child_count_excludes_hidden_entries(self, tmp_path: Path) -> None:
        """child_count must not include dot-entries when include_hidden=False."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "visible.txt").write_text("v")
        (sub / ".hidden").write_text("h")
        result = list_directory(str(tmp_path))
        entry = next(e for e in result["entries"] if e["name"] == "sub")
        # .hidden is excluded by the default include_hidden=False filter
        assert entry["child_count"] == 1

    def test_child_count_includes_hidden_when_requested(self, tmp_path: Path) -> None:
        """child_count includes dot-entries when include_hidden=True."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "visible.txt").write_text("v")
        (sub / ".hidden").write_text("h")
        result = list_directory(str(tmp_path), include_hidden=True)
        entry = next(e for e in result["entries"] if e["name"] == "sub")
        assert entry["child_count"] == 2

    def test_child_count_excludes_ignored_patterns(self, tmp_path: Path) -> None:
        """child_count must not count directories matched by ignored_dir_patterns."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "app.py").write_text("x")
        (sub / "__pycache__").mkdir()
        result = list_directory(str(tmp_path))
        entry = next(e for e in result["entries"] if e["name"] == "sub")
        # __pycache__ is in the default ignore patterns
        assert entry["child_count"] == 1


# ---------------------------------------------------------------------------
# TestListDirectoryTruncation
# ---------------------------------------------------------------------------


class TestListDirectoryTruncation:
    def test_truncation_at_max_entries(self, tmp_path: Path) -> None:
        for i in range(10):
            (tmp_path / f"file{i:02d}.txt").write_text("")
        result = list_directory(str(tmp_path), max_entries=3)
        assert result["truncated"] is True
        assert len(result["entries"]) == 3
        assert result["truncated_at"] is not None

    def test_no_truncation_when_under_limit(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"file{i}.txt").write_text("")
        result = list_directory(str(tmp_path), max_entries=10)
        assert result["truncated"] is False
        assert len(result["entries"]) == 5


# ---------------------------------------------------------------------------
# TestListDirectoryErrorPaths
# ---------------------------------------------------------------------------


class TestListDirectoryErrorPaths:
    def test_permission_error_on_root_scan_returns_error(self, tmp_path: Path) -> None:
        """PermissionError on os.scandir(dir_path) at root depth returns error dict."""
        with patch("src.tools.os.scandir", side_effect=PermissionError):
            result = list_directory(str(tmp_path))
        assert "error" in result
        assert "Permission denied" in result["error"]

    def test_permission_error_on_nested_scan_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """PermissionError on a nested directory returns empty children gracefully."""
        sub = tmp_path / "restricted"
        sub.mkdir()

        real_scandir = os.scandir
        call_count = {"n": 0}

        def patched_scandir(path: str) -> object:
            call_count["n"] += 1
            if call_count["n"] == 3:  # third call: recursing into restricted/
                raise PermissionError("access denied")
            return real_scandir(path)

        with patch("src.tools.os.scandir", side_effect=patched_scandir):
            result = list_directory(str(tmp_path), max_depth=2)
        assert "error" not in result
        assert result["total_dirs"] == 1

    def test_recursive_truncation_stops_parent_iteration(self, tmp_path: Path) -> None:
        """counter.truncated=True from recursive call breaks parent loop (line 703)."""
        alpha = tmp_path / "alpha"
        alpha.mkdir()
        (alpha / "file_a.txt").write_text("")
        (alpha / "file_b.txt").write_text("")
        (tmp_path / "beta").mkdir()

        # alpha is processed (total=1), file_a in alpha (total=2 == max),
        # file_b triggers truncation inside recursion, then parent loop
        # reaches beta with counter.truncated=True → line 703 break.
        result = list_directory(str(tmp_path), max_depth=2, max_entries=2)

        assert result["truncated"] is True
        names = [e["name"] for e in result["entries"]]
        assert "alpha" in names
        assert "beta" not in names

    def test_permission_error_counting_children_defaults_to_zero(
        self, tmp_path: Path
    ) -> None:
        """PermissionError when counting subdir children falls back to 0 (lines 719-720)."""
        (tmp_path / "mydir").mkdir()

        real_scandir = os.scandir
        call_count = {"n": 0}

        def patched_scandir(path: str) -> object:
            call_count["n"] += 1
            if call_count["n"] == 2:  # second call: counting children of mydir
                raise PermissionError("access denied")
            return real_scandir(path)

        with patch("src.tools.os.scandir", side_effect=patched_scandir):
            result = list_directory(str(tmp_path))

        assert result["total_dirs"] == 1
        assert result["entries"][0]["child_count"] == 0

    def test_oserror_on_stat_defaults_to_zero_bytes(self, tmp_path: Path) -> None:
        """OSError from entry.stat() falls back to size_bytes=0 (lines 744-745)."""
        mock_entry = MagicMock()
        mock_entry.name = "broken_file.txt"
        mock_entry.path = str(tmp_path / "broken_file.txt")
        mock_entry.is_dir.return_value = False
        mock_entry.stat.side_effect = OSError("stat failed")

        with patch("src.tools.os.scandir", return_value=[mock_entry]):
            result = list_directory(str(tmp_path))

        assert result["total_files"] == 1
        assert result["entries"][0]["size_bytes"] == 0
        assert result["entries"][0]["name"] == "broken_file.txt"
