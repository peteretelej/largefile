"""revert_edit tool unit tests.

Tests for reverting files to backup states.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from src.file_access import create_backup, list_backups
from src.tools import revert_edit


class TestRevertToLatest:
    """Test reverting to most recent backup."""

    def test_revert_to_latest(self):
        """backup_id=None uses most recent backup."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("original content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create initial backup
                create_backup(temp_path)

                # Modify file
                Path(temp_path).write_text("modified content")
                time.sleep(1.1)  # Ensure different timestamp

                # Revert to latest (only backup)
                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path)

                assert result["success"] is True
                assert result["reverted_to"] is not None
                assert result["current_saved_as"] is not None
                assert Path(temp_path).read_text() == "original content"

        Path(temp_path).unlink(missing_ok=True)


class TestRevertToSpecific:
    """Test reverting to a specific backup."""

    def test_revert_to_specific_backup(self):
        """Reverts to specified backup_id."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("version 1")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create first backup (version 1)
                backup1 = create_backup(temp_path)

                # Modify and create second backup (version 2)
                time.sleep(1.1)
                Path(temp_path).write_text("version 2")
                create_backup(temp_path)

                # Modify to version 3
                time.sleep(1.1)
                Path(temp_path).write_text("version 3")

                # Revert specifically to version 1
                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path, backup_id=backup1.id)

                assert result["success"] is True
                assert result["reverted_to"]["id"] == backup1.id
                assert Path(temp_path).read_text() == "version 1"

        Path(temp_path).unlink(missing_ok=True)


class TestRevertPreservesCurrent:
    """Test that current state is preserved before revert."""

    def test_revert_preserves_current_state(self):
        """Current state saved before revert."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("original")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create backup
                create_backup(temp_path)

                # Modify file
                Path(temp_path).write_text("modified state")
                time.sleep(1.1)

                # Revert
                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path)

                assert result["success"] is True
                assert result["current_saved_as"] is not None

                # Verify the pre-revert state was backed up
                saved_backup_path = result["current_saved_as"]["path"]
                assert Path(saved_backup_path).read_text() == "modified state"

        Path(temp_path).unlink(missing_ok=True)


class TestRevertErrors:
    """Test error conditions for revert_edit."""

    def test_revert_no_backups(self):
        """Returns error with empty available_backups when no backups exist."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10

                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path)

                assert result["success"] is False
                assert result["error"] == "No backups found for this file"
                assert result["available_backups"] == []
                assert result["reverted_to"] is None
                assert result["current_saved_as"] is None

        Path(temp_path).unlink(missing_ok=True)

    def test_revert_invalid_backup_id(self):
        """Returns error with available_backups list for invalid backup_id."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("content")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create a backup
                create_backup(temp_path)

                # Try to revert to non-existent backup
                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path, backup_id="9999999999")

                assert result["success"] is False
                assert "9999999999 not found" in result["error"]
                assert len(result["available_backups"]) > 0
                assert result["reverted_to"] is None
                assert result["current_saved_as"] is None

        Path(temp_path).unlink(missing_ok=True)

    def test_revert_nonexistent_file(self):
        """Returns error for missing file."""
        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir

                with patch("src.tools.config", mock_config):
                    result = revert_edit("/nonexistent/path/file.txt")

                assert result["success"] is False
                assert "does not exist" in result["error"]
                assert result["available_backups"] == []


class TestRevertUpdatesBackupList:
    """Test that available_backups is updated after revert."""

    def test_available_backups_includes_new_backup(self):
        """available_backups includes the newly created backup of current state."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("original")
            temp_path = f.name

        with tempfile.TemporaryDirectory() as backup_dir:
            with patch("src.file_access.config") as mock_config:
                mock_config.backup_dir = backup_dir
                mock_config.max_backups = 10
                mock_config.memory_threshold = 50 * 1024 * 1024

                # Create backup
                create_backup(temp_path)
                backups_before = list_backups(temp_path)

                # Modify and revert
                Path(temp_path).write_text("modified")
                time.sleep(1.1)

                with patch("src.tools.config", mock_config):
                    result = revert_edit(temp_path)

                # Should have one more backup (the pre-revert state)
                assert len(result["available_backups"]) == len(backups_before) + 1

        Path(temp_path).unlink(missing_ok=True)
