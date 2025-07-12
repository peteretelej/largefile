"""Search/replace editing operations (Research-Backed Design)."""

import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SearchReplaceOperation:
    """Information about a search/replace operation."""

    file_path: str
    search_text: str
    replace_text: str
    matches_found: int
    changes_made: int
    line_number: int  # Where first change occurred
    preview: str  # Before/after diff preview
    backup_path: Optional[str] = None


class SearchReplaceEditor:
    """Search/replace-based file editor (eliminates line number errors)."""

    def __init__(self, backup_dir: Optional[str] = None):
        """Initialize the search/replace editor.

        Args:
            backup_dir: Directory for backup files (default: .largefile_backups)
        """
        self.backup_dir = Path(backup_dir or ".largefile_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def _create_backup(self, file_path: str) -> str:
        """Create a backup of the file before editing."""
        file_path_obj = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path_obj.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        # Copy original file to backup
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return str(backup_path)

    def _generate_preview(self, original_text: str, modified_text: str, search_text: str) -> str:
        """Generate a preview showing changes."""
        # Find the lines around the change for context
        original_lines = original_text.split('\n')
        modified_lines = modified_text.split('\n')
        
        # Simple diff preview showing search/replace operation
        return f"""SEARCH:
{search_text}

REPLACE:
{modified_text[modified_text.find(modified_lines[0]):modified_text.find(modified_lines[0]) + len(search_text) + 50]}

CHANGES: {len(original_lines)} → {len(modified_lines)} lines"""

    async def find_matches(self, file_path: str, search_text: str, exact: bool = True) -> list[dict]:
        """Find all matches of search_text in file.
        
        Args:
            file_path: Path to file to search
            search_text: Text to find
            exact: If True, exact string match; if False, regex match
            
        Returns:
            List of matches with line numbers and positions
        """
        matches = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        if exact:
            # Exact string matching
            for line_num, line in enumerate(lines, 1):
                if search_text in line:
                    start_pos = line.find(search_text)
                    matches.append({
                        'line_number': line_num,
                        'start': start_pos,
                        'end': start_pos + len(search_text),
                        'line_content': line
                    })
        else:
            # Regex matching
            pattern = re.compile(search_text, re.MULTILINE)
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                matches.append({
                    'line_number': line_num,
                    'start': match.start(),
                    'end': match.end(),
                    'match_text': match.group()
                })
                
        return matches

    async def search_replace(
        self,
        file_path: str,
        search_text: str,
        replace_text: str,
        max_replacements: int = 1,
        create_backup: bool = True,
        preview_only: bool = False
    ) -> SearchReplaceOperation:
        """Perform search/replace operation.

        Args:
            file_path: Path to the file to edit
            search_text: Text to find and replace
            replace_text: Replacement text
            max_replacements: Maximum number of replacements (default 1)
            create_backup: Whether to create a backup before editing
            preview_only: If True, only return preview without making changes

        Returns:
            SearchReplaceOperation with details of the operation
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Find matches
        matches = await self.find_matches(file_path, search_text, exact=True)
        
        if not matches:
            return SearchReplaceOperation(
                file_path=file_path,
                search_text=search_text,
                replace_text=replace_text,
                matches_found=0,
                changes_made=0,
                line_number=0,
                preview="No matches found",
                backup_path=None
            )

        # Perform replacement
        modified_content = original_content
        changes_made = 0
        
        # Replace up to max_replacements occurrences
        for i in range(min(len(matches), max_replacements)):
            modified_content = modified_content.replace(search_text, replace_text, 1)
            changes_made += 1

        # Generate preview
        preview = self._generate_preview(original_content, modified_content, search_text)
        
        backup_path = None
        if not preview_only and changes_made > 0:
            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup(file_path)
            
            # Write changes atomically using temporary file
            with tempfile.NamedTemporaryFile(mode='w', dir=Path(file_path).parent, 
                                           delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(modified_content)
                tmp_path = tmp_file.name
            
            # Atomic rename
            Path(tmp_path).rename(file_path)

        return SearchReplaceOperation(
            file_path=file_path,
            search_text=search_text,
            replace_text=replace_text,
            matches_found=len(matches),
            changes_made=changes_made if not preview_only else 0,
            line_number=matches[0]['line_number'] if matches else 0,
            preview=preview,
            backup_path=backup_path
        )
