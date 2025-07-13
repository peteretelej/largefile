import os
import tempfile
import pytest
from pathlib import Path

from src.file_access import (
    normalize_path, 
    get_file_info, 
    read_file_content, 
    read_file_lines,
    write_file_content,
    create_backup
)
from src.exceptions import FileAccessError


class TestFileAccess:
    
    def test_normalize_path(self):
        """Test path normalization."""
        result = normalize_path("~/test.txt")
        assert result.startswith("/")
        assert "test.txt" in result
    
    def test_get_file_info_existing_file(self):
        """Test file info for existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            info = get_file_info(temp_path)
            assert info["exists"] is True
            assert info["size"] > 0
            assert info["strategy"] in ["memory", "mmap", "streaming"]
        finally:
            os.unlink(temp_path)
    
    def test_get_file_info_nonexistent_file(self):
        """Test file info for nonexistent file."""
        with pytest.raises(FileAccessError):
            get_file_info("/nonexistent/file.txt")
    
    def test_read_file_content(self):
        """Test reading file content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_content = "Hello\nWorld\n"
            f.write(test_content)
            temp_path = f.name
        
        try:
            content = read_file_content(temp_path)
            assert content == test_content
        finally:
            os.unlink(temp_path)
    
    def test_read_file_lines(self):
        """Test reading file as lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Line 1\nLine 2\n")
            temp_path = f.name
        
        try:
            lines = read_file_lines(temp_path)
            assert len(lines) == 2
            assert lines[0] == "Line 1\n"
            assert lines[1] == "Line 2\n"
        finally:
            os.unlink(temp_path)
    
    def test_write_file_content(self):
        """Test writing file content."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            test_content = "New content"
            write_file_content(temp_path, test_content)
            
            with open(temp_path, 'r') as f:
                written_content = f.read()
            assert written_content == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_create_backup(self):
        """Test backup creation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("original content")
            temp_path = f.name
        
        try:
            backup_path = create_backup(temp_path)
            assert os.path.exists(backup_path)
            
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            assert backup_content == "original content"
        finally:
            os.unlink(temp_path)
            if os.path.exists(backup_path):
                os.unlink(backup_path)