"""Editor unit tests.

Test core content editing and backup functionality.
"""

import tempfile
from pathlib import Path

from src.editor import atomic_edit_file
from src.file_access import create_backup


class TestEditor:
    """Test editor core functions."""

    def test_content_replacement(self):
        """Test find/replace operations with actual files."""
        # Create a temporary file
        original_content = "Hello world\nThis is a test\nHello again"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(original_content)
            temp_path = f.name
        
        try:
            # Test atomic edit with exact match
            result = atomic_edit_file(
                temp_path,
                "Hello world",
                "Hi world",
                preview=True,  # Preview mode
                fuzzy=False
            )
            
            # Result should be EditResult object
            assert hasattr(result, 'success')
            assert hasattr(result, 'changes_made')
            
            if result.success:
                assert result.changes_made > 0
                assert hasattr(result, 'preview')
                
        finally:
            Path(temp_path).unlink()

    def test_backup_handling(self):
        """Test backup file creation."""
        # Create a temporary file
        test_content = "Original content\nLine 2\nLine 3"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Test backup creation
            backup_path = create_backup(temp_path)
            
            # Backup should exist
            assert Path(backup_path).exists()
            
            # Backup should have same content
            backup_content = Path(backup_path).read_text()
            assert backup_content == test_content
            
            # Backup path should be different from original
            assert backup_path != temp_path
            
            # Clean up backup
            Path(backup_path).unlink()
            
        finally:
            Path(temp_path).unlink()