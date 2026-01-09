"""Backup management unit tests.

Tests for backup naming, listing, and cleanup functionality.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from src.file_access import (
    cleanup_old_backups,
    create_backup,
    get_backup_filename,
    get_backup_pattern,
    list_backups,
)


class TestBackupNaming:
    """Test backup naming convention."""

    def test_backup_naming_unique_per_path(self):
        """Same filename in different paths get different hashes."""
        path1 = "/home/user/project1/config.py"
        path2 = "/home/user/project2/config.py"

        pattern1 = get_backup_pattern(path1)
        pattern2 = get_backup_pattern(path2)

        # Both should have same basename
        assert pattern1.startswith("config.py.")
        assert pattern2.startswith("config.py.")

        # But different path hashes
        assert pattern1 != pattern2

    def test_backup_filename_format(self):
        """Backup filename follows {name}.{hash}.{timestamp} format."""
        path = "/home/user/myfile.py"
        filename = get_backup_filename(path)

        parts = filename.split(".")
        assert len(parts) == 4  # myfile.py.{hash}.{timestamp}
        assert parts[0] == "myfile"
        assert parts[1] == "py"
        assert len(parts[2]) == 8  # 8-char hash
        assert parts[3].isdigit()  # Unix timestamp

    def test_backup_pattern_format(self):
        """Backup pattern follows {name}.{hash}.* format."""
        path = "/home/user/myfile.py"
        pattern = get_backup_pattern(path)

        assert pattern.startswith("myfile.py.")
        assert pattern.endswith(".*")
        # Extract hash (between basename and .*)
        hash_part = pattern[len("myfile.py.") : -2]  # Remove ".*" suffix
        assert len(hash_part) == 8


class TestListBackups:
    """Test backup listing functionality."""

    def test_list_backups_newest_first(self):
        """Backups sorted by timestamp descending."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create multiple backups with slight time differences
                create_backup(temp_path)
                time.sleep(1.1)  # Ensure different timestamps
                create_backup(temp_path)
                time.sleep(1.1)
                create_backup(temp_path)

                backups = list_backups(temp_path)

                assert len(backups) >= 3
                # Should be newest first
                assert int(backups[0].id) > int(backups[1].id)
                assert int(backups[1].id) > int(backups[2].id)

        Path(temp_path).unlink()

    def test_list_backups_empty_when_no_backups(self):
        """Returns empty list when no backups exist."""
        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir

                backups = list_backups("/nonexistent/file.txt")
                assert backups == []

    def test_list_backups_returns_backup_info(self):
        """Backup list contains BackupInfo objects with correct fields."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content for backup")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                create_backup(temp_path)
                backups = list_backups(temp_path)

                assert len(backups) == 1
                backup = backups[0]

                assert backup.id.isdigit()  # Unix timestamp string
                assert "T" in backup.timestamp  # ISO 8601 format
                assert backup.size > 0
                assert Path(backup.path).exists()

        Path(temp_path).unlink()


class TestCleanupBackups:
    """Test backup cleanup functionality."""

    def test_cleanup_old_backups(self):
        """Deletes oldest when exceeding max_backups."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 100  # High limit for creation
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create 5 backups
                for _ in range(5):
                    create_backup(temp_path)
                    time.sleep(1.1)

                backups_before = list_backups(temp_path)
                assert len(backups_before) == 5

                # Cleanup to max 2
                deleted = cleanup_old_backups(temp_path, max_backups=2)

                assert deleted == 3
                backups_after = list_backups(temp_path)
                assert len(backups_after) == 2

                # Should keep the 2 newest
                assert backups_after[0].id == backups_before[0].id
                assert backups_after[1].id == backups_before[1].id

        Path(temp_path).unlink()

    def test_cleanup_no_action_when_under_limit(self):
        """No deletion when backups count is within limit."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create 2 backups
                create_backup(temp_path)
                time.sleep(1.1)
                create_backup(temp_path)

                # Cleanup with max 5
                deleted = cleanup_old_backups(temp_path, max_backups=5)

                assert deleted == 0
                backups = list_backups(temp_path)
                assert len(backups) == 2

        Path(temp_path).unlink()


class TestCreateBackupWithCleanup:
    """Test that create_backup triggers automatic cleanup."""

    def test_create_backup_triggers_cleanup(self):
        """Cleanup runs automatically on create when over limit."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 3
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create more backups than limit
                for _ in range(5):
                    create_backup(temp_path)
                    time.sleep(1.1)

                backups = list_backups(temp_path)
                # Should have been cleaned up to max_backups
                assert len(backups) == 3

        Path(temp_path).unlink()

    def test_create_backup_returns_backup_info(self):
        """create_backup returns BackupInfo object."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content for backup")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                backup_info = create_backup(temp_path)

                assert backup_info.id.isdigit()
                assert "T" in backup_info.timestamp
                assert backup_info.size > 0
                assert Path(backup_info.path).exists()

                # Verify backup content matches original
                assert Path(backup_info.path).read_text() == "test content for backup"

        Path(temp_path).unlink()
