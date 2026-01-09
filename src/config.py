import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Environment-based configuration with sensible defaults."""

    memory_threshold_mb: int = int(os.getenv("LARGEFILE_MEMORY_THRESHOLD_MB", "50"))
    mmap_threshold_mb: int = int(os.getenv("LARGEFILE_MMAP_THRESHOLD_MB", "500"))
    max_line_length: int = int(os.getenv("LARGEFILE_MAX_LINE_LENGTH", "1000"))
    truncate_length: int = int(os.getenv("LARGEFILE_TRUNCATE_LENGTH", "500"))

    fuzzy_threshold: float = float(os.getenv("LARGEFILE_FUZZY_THRESHOLD", "0.8"))
    max_search_results: int = int(os.getenv("LARGEFILE_MAX_SEARCH_RESULTS", "20"))
    context_lines: int = int(os.getenv("LARGEFILE_CONTEXT_LINES", "2"))

    similar_match_limit: int = int(os.getenv("LARGEFILE_SIMILAR_MATCH_LIMIT", "3"))
    similar_match_threshold: float = float(
        os.getenv("LARGEFILE_SIMILAR_MATCH_THRESHOLD", "0.6")
    )

    streaming_chunk_size: int = int(os.getenv("LARGEFILE_STREAMING_CHUNK_SIZE", "8192"))
    backup_dir: str = os.getenv(
        "LARGEFILE_BACKUP_DIR", str(Path.home() / ".largefile" / "backups")
    )
    max_backups: int = int(os.getenv("LARGEFILE_MAX_BACKUPS", "10"))
    max_batch_changes: int = int(os.getenv("LARGEFILE_MAX_BATCH_CHANGES", "50"))

    enable_tree_sitter: bool = (
        os.getenv("LARGEFILE_ENABLE_TREE_SITTER", "true").lower() == "true"
    )
    tree_sitter_timeout: int = int(os.getenv("LARGEFILE_TREE_SITTER_TIMEOUT", "5"))

    @property
    def memory_threshold(self) -> int:
        """Memory threshold in bytes."""
        return self.memory_threshold_mb * 1024 * 1024

    @property
    def mmap_threshold(self) -> int:
        """Memory mapping threshold in bytes."""
        return self.mmap_threshold_mb * 1024 * 1024


config = Config()
