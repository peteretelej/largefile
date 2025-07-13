import os
from dataclasses import dataclass


@dataclass
class Config:
    """Environment-based configuration with sensible defaults."""
    
    memory_threshold: int = int(os.getenv('LARGEFILE_MEMORY_THRESHOLD', '52428800'))
    mmap_threshold: int = int(os.getenv('LARGEFILE_MMAP_THRESHOLD', '524288000'))
    max_line_length: int = int(os.getenv('LARGEFILE_MAX_LINE_LENGTH', '1000'))
    truncate_length: int = int(os.getenv('LARGEFILE_TRUNCATE_LENGTH', '500'))
    
    fuzzy_threshold: float = float(os.getenv('LARGEFILE_FUZZY_THRESHOLD', '0.8'))
    max_search_results: int = int(os.getenv('LARGEFILE_MAX_SEARCH_RESULTS', '20'))
    context_lines: int = int(os.getenv('LARGEFILE_CONTEXT_LINES', '2'))
    
    streaming_chunk_size: int = int(os.getenv('LARGEFILE_STREAMING_CHUNK_SIZE', '8192'))
    backup_dir: str = os.getenv('LARGEFILE_BACKUP_DIR', '.largefile_backups')
    
    enable_tree_sitter: bool = os.getenv('LARGEFILE_ENABLE_TREE_SITTER', 'true').lower() == 'true'
    tree_sitter_timeout: int = int(os.getenv('LARGEFILE_TREE_SITTER_TIMEOUT', '5'))


config = Config()