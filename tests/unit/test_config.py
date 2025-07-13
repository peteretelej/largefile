import os
import pytest

from src.config import Config


class TestConfig:
    
    def test_default_config_values(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.memory_threshold == 52428800  # 50MB
        assert config.mmap_threshold == 524288000   # 500MB
        assert config.max_line_length == 1000
        assert config.truncate_length == 500
        assert config.fuzzy_threshold == 0.8
        assert config.max_search_results == 20
        assert config.context_lines == 2
        assert config.enable_tree_sitter is True
    
    def test_config_attributes_exist(self):
        """Test that all required config attributes exist."""
        config = Config()
        
        assert hasattr(config, 'memory_threshold')
        assert hasattr(config, 'fuzzy_threshold')
        assert hasattr(config, 'max_search_results')
        assert hasattr(config, 'enable_tree_sitter')
        assert isinstance(config.memory_threshold, int)
        assert isinstance(config.fuzzy_threshold, float)