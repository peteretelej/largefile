# Encoding Auto-Detection Plan

## Current Encoding Usage

### APIs (15+ functions with encoding parameter)
- `get_overview(absolute_file_path, encoding="utf-8")`
- `search_content(..., encoding="utf-8", ...)`
- `read_content(..., encoding="utf-8", ...)`
- `edit_content(..., encoding="utf-8", ...)`

### Internal Functions
- `src/file_access.py`: 6 functions with encoding
- `src/search_engine.py`: `search_file()` 
- `src/editor.py`: 2 functions with encoding
- `src/data_models.py`: `FileOverview.encoding`

## Implementation Plan

#### Phase 1: Add chardet and detection
- [x] Add chardet dependency  
- [x] Create `detect_file_encoding(file_path: str) -> str` in `file_access.py`
- [x] Fallback to utf-8 on detection failure

#### Phase 2: Update file access layer
- [ ] Remove encoding parameter from `read_file_content()`
- [ ] Remove encoding parameter from `read_file_lines()`  
- [ ] Remove encoding parameter from `write_file_content()`
- [ ] Update internal strategy functions
- [ ] Add encoding cache per file session

#### Phase 3: Update search and edit layers
- [ ] Remove encoding parameter from `search_file()`
- [ ] Remove encoding parameter from `atomic_edit_file()`
- [ ] Remove encoding parameter from `_preview_edit()`

#### Phase 4: Update public APIs
- [ ] Remove encoding parameter from all 4 MCP tools
- [ ] Update MCP schema definitions
- [ ] Update `FileOverview.encoding` to show detected value

#### Phase 5: Documentation and testing
- [ ] Update API.md, design.md, examples
- [ ] Add encoding detection tests
- [ ] Test various encodings and edge cases

#### Phase 6: Quality assurance
- [ ] Run pre-push script
- [ ] Verify all tests pass
- [ ] Update plan as complete

## Technical Implementation

### Detection Function
```python
def detect_file_encoding(file_path: str) -> str:
    """Detect file encoding using chardet with utf-8 fallback."""
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(65536)  # 64KB sample
            
        if not sample:
            return 'utf-8'
            
        result = chardet.detect(sample)
        return result['encoding'] or 'utf-8'
            
    except Exception:
        return 'utf-8'
```

### Caching
- Cache encoding per file: `canonical_path + mtime`
- Clear cache on file modification

## Testing

### Encodings to Test
- UTF-8, UTF-16 LE/BE, Latin-1, ASCII, Windows-1252

### Edge Cases  
- Empty files, binary files, small files, BOM markers

## Code Quality

### Requirements
- Simple, clear, concise code
- Avoid complexity and premature optimization
- Self-documenting functions
- Minimal abstraction layers
- Direct error handling

### API After Implementation
```python
# Simplified APIs
get_overview("/path/to/file.py")
search_content("/path/to/file.py", "pattern")
read_content("/path/to/file.py", target)
edit_content("/path/to/file.py", search_text, replace_text)
```