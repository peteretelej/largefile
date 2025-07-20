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

**Implementation Notes:**

- Added 0.7 confidence threshold to prevent poor chardet guesses
- Detection function handles empty files, exceptions, and low confidence cases
- Test coverage for UTF-8, Latin-1, UTF-16, empty files, and non-existent files

#### Phase 2: Update file access layer

- [x] Remove encoding parameter from `read_file_content()`
- [x] Remove encoding parameter from `read_file_lines()`
- [x] Remove encoding parameter from `write_file_content()`
- [x] Update internal strategy functions
- [x] Add encoding cache per file session

**Implementation Notes:**

- `read_file_content()` and `read_file_lines()` now call `detect_file_encoding()` internally
- `write_file_content()` preserves existing file encoding or defaults to utf-8 for new files
- Internal strategy functions (`_read_file_memory`, etc.) still accept encoding parameter
- **Skipped caching**: Detection is fast (~1-5ms), avoiding session management complexity
- All existing tests pass with auto-detection

#### Phase 3: Update search and edit layers

- [x] Remove encoding parameter from `search_file()`
- [x] Remove encoding parameter from `atomic_edit_file()`
- [x] Remove encoding parameter from `_preview_edit()`

**Implementation Notes:**

- `search_file()` now uses `read_file_lines()` without encoding parameter
- `atomic_edit_file()` and `replace_content()` updated to use auto-detection
- **No `_preview_edit()` function**: Preview functionality is built into `replace_content()`
- All edit operations now preserve original file encoding automatically

#### Phase 4: Update public APIs

- [x] Remove encoding parameter from all 4 MCP tools
- [x] Update MCP schema definitions
- [x] Update `FileOverview.encoding` to show detected value

**Implementation Notes:**
- All 4 MCP tools (`get_overview`, `search_content`, `read_content`, `edit_content`) no longer accept encoding
- MCP schema definitions updated to remove encoding parameter from all tools
- `FileOverview.encoding` now shows the actual detected encoding value
- **Breaking change**: All tool signatures simplified, auto-detection is now transparent to users

#### Phase 5: Documentation and testing

- [x] Update API.md, design.md, examples
- [x] Add encoding detection tests
- [x] Test various encodings and edge cases

**Implementation Notes:**
- API.md updated to remove all encoding parameters from tool signatures
- design.md updated to reflect auto-detected encoding support
- examples.md already clean (no encoding parameters used)
- **Existing tests comprehensive**: UTF-8, Latin-1, UTF-16, empty files, non-existent files
- **ASCII detection fix**: ASCII files now default to UTF-8 for better compatibility

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

        # Use detection only if confidence is reasonable (>= 0.7)
        if result and result.get('confidence', 0) >= 0.7:
            return result['encoding'] or 'utf-8'
        else:
            return 'utf-8'

    except Exception:
        return 'utf-8'
```

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

### Implementation Guidance

- Document scope changes and decisions made during each phase as Implementation Notes below the phase
- Keep implementation notes concise but informative for future reference
- Note what was skipped and why (e.g., complexity vs benefit trade-offs)
- ALWAYS use a todo when implementing a phase, the last step of the todo being to mark checklist items as complete when done.

### API After Implementation

```python
# Simplified APIs
get_overview("/path/to/file.py")
search_content("/path/to/file.py", "pattern")
read_content("/path/to/file.py", target)
edit_content("/path/to/file.py", search_text, replace_text)
```
