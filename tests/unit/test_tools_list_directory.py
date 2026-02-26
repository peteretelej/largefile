"""Unit tests for the list_directory tool function."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.tools import list_directory

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
        assert "deep.txt" in names


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
    def test_permission_error_on_root_scan_returns_empty(self, tmp_path: Path) -> None:
        """PermissionError on os.scandir(dir_path) returns empty entries (lines 698-699)."""
        with patch("src.tools.os.scandir", side_effect=PermissionError):
            result = list_directory(str(tmp_path))
        assert result["entries"] == []
        assert result["total_files"] == 0
        assert result["total_dirs"] == 0
        assert result["truncated"] is False

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
