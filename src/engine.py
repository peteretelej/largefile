"""File access engine for large file handling."""

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileSession:
    """Session information for a loaded file."""

    canonical_path: str
    content_hash: str
    line_count: int
    file_size: int
    encoding: str
    chunk_size: int
    loaded_at: float
    has_long_lines: bool  # >1000 chars


class FileEngine:
    """Core engine for file access and session management."""

    def __init__(self) -> None:
        """Initialize the file engine."""
        self._sessions: dict[str, FileSession] = {}

    def _get_session_key(self, file_path: str, content_hash: str) -> str:
        """Generate session key from path and content hash."""
        return f"{file_path}:{content_hash}"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()

    def _canonicalize_path(self, file_path: str) -> str:
        """Convert to canonical absolute path."""
        path = Path(file_path).expanduser().resolve()
        return str(path)

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        # Basic encoding detection - start with UTF-8
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Test read small portion
            return "utf-8"
        except UnicodeDecodeError:
            # Fallback to latin-1 which can handle any byte sequence
            return "latin-1"

    def _choose_access_strategy(self, file_size: int) -> str:
        """Choose file access strategy based on size."""
        if file_size < 10 * 1024 * 1024:  # 10MB
            return "memory"
        else:
            return "mmap"

    def _detect_long_lines(self, file_path: Path, encoding: str) -> bool:
        """Check if file has any lines longer than 1000 characters."""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                for line_num, line in enumerate(f, 1):
                    if len(line) > 1000:
                        return True
                    # Only check first 100 lines for performance
                    if line_num > 100:
                        break
            return False
        except Exception:
            return False

    async def load_file(
        self, file_path: str, chunk_size: int = 1000, encoding: Optional[str] = None
    ) -> FileSession:
        """Load a file and create session."""
        canonical_path = self._canonicalize_path(file_path)
        file_path_obj = Path(canonical_path)
        
        # Check if file exists and is readable
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {canonical_path}")
        
        if not file_path_obj.is_file():
            raise ValueError(f"Path is not a file: {canonical_path}")

        # Get file info
        file_size = file_path_obj.stat().st_size
        content_hash = self._calculate_file_hash(file_path_obj)
        session_key = self._get_session_key(canonical_path, content_hash)
        
        # Check if session already exists
        if session_key in self._sessions:
            return self._sessions[session_key]
        
        # Detect encoding if not provided
        if encoding is None:
            encoding = self._detect_encoding(file_path_obj)
        
        # Count lines and detect long lines
        line_count = 0
        has_long_lines = False
        
        with open(file_path_obj, 'r', encoding=encoding) as f:
            for line in f:
                line_count += 1
                if len(line) > 1000:
                    has_long_lines = True
        
        # Create and store session
        session = FileSession(
            canonical_path=canonical_path,
            content_hash=content_hash,
            line_count=line_count,
            file_size=file_size,
            encoding=encoding,
            chunk_size=chunk_size,
            loaded_at=time.time(),
            has_long_lines=has_long_lines
        )
        
        self._sessions[session_key] = session
        return session

    def get_session(self, file_path: str) -> Optional[FileSession]:
        """Get existing session for file."""
        canonical_path = self._canonicalize_path(file_path)
        file_path_obj = Path(canonical_path)
        
        if not file_path_obj.exists():
            return None
        
        # Calculate current content hash
        current_hash = self._calculate_file_hash(file_path_obj)
        session_key = self._get_session_key(canonical_path, current_hash)
        
        return self._sessions.get(session_key)

    async def read_lines(
        self, file_path: str, start_line: int, end_line: Optional[int] = None
    ) -> str:
        """Read specific lines from file."""
        canonical_path = self._canonicalize_path(file_path)
        
        # Auto-load file if not in session
        session = self.get_session(canonical_path)
        if session is None:
            session = await self.load_file(canonical_path)
        
        # Read the specified lines
        lines = []
        with open(canonical_path, 'r', encoding=session.encoding) as f:
            for line_num, line in enumerate(f, 1):
                if line_num >= start_line:
                    if end_line is None or line_num <= end_line:
                        lines.append(line.rstrip('\n'))
                    else:
                        break
        
        return '\n'.join(lines)

    async def search_content(
        self, file_path: str, pattern: str, max_results: int = 20
    ) -> list[dict]:
        """Search for pattern in file content."""
        canonical_path = self._canonicalize_path(file_path)
        
        # Auto-load file if not in session
        session = self.get_session(canonical_path)
        if session is None:
            session = await self.load_file(canonical_path)
        
        results = []
        with open(canonical_path, 'r', encoding=session.encoding) as f:
            for line_num, line in enumerate(f, 1):
                if pattern in line:
                    results.append({
                        'line_number': line_num,
                        'line_content': line.rstrip('\n'),
                        'match_start': line.find(pattern),
                        'match_end': line.find(pattern) + len(pattern)
                    })
                    
                    if len(results) >= max_results:
                        break
        
        return results

    def invalidate_session(self, file_path: str) -> None:
        """Invalidate session for file."""
        canonical_path = self._canonicalize_path(file_path)
        
        # Remove all sessions for this file path
        keys_to_remove = [key for key in self._sessions.keys() if key.startswith(canonical_path)]
        for key in keys_to_remove:
            del self._sessions[key]
