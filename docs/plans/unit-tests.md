# Unit Tests Plan

**Minimal unit test strategy for maximum coverage impact.**

## Current State: 25 integration tests, 45% coverage

**Missing Coverage Analysis:**
- **tree_parser.py**: 180/247 lines missing = **22.6% of entire codebase**
- **file_access.py**: 91/135 lines missing = **11.4% of entire codebase**  
- **editor.py**: 84/112 lines missing = **10.5% of entire codebase**
- **utils.py**: 33/45 lines missing = **4.1% of entire codebase**

**Total impact: 48.6% of codebase in just 4 modules**

## Minimal Unit Test Strategy

### **Target: 45% → 70% coverage (+25%) with 8 unit tests**

### 1. **Tree Parser** (1 file, 3 tests) → **+11% total coverage**
*Target: 50% coverage on tree_parser.py*

```python
# tests/unit/test_tree_parser.py
def test_language_detection():
    """Test file extension to language mapping."""
    
def test_basic_parsing():
    """Test successful AST parsing for Python/JS."""
    
def test_parsing_fallback():
    """Test graceful fallback when parsing fails."""
```

### 2. **File Access** (1 file, 3 tests) → **+6% total coverage**
*Target: 50% coverage on file_access.py*

```python  
# tests/unit/test_file_access.py
def test_strategy_selection():
    """Test file size → strategy mapping."""
    
def test_memory_file_reading():
    """Test memory strategy file operations."""
    
def test_file_info_extraction():
    """Test file metadata extraction."""
```

### 3. **Editor** (1 file, 2 tests) → **+5% total coverage**
*Target: 50% coverage on editor.py*

```python
# tests/unit/test_editor.py  
def test_content_replacement():
    """Test find/replace operations."""
    
def test_backup_handling():
    """Test backup file creation."""
```

**Total: 8 tests for +22% coverage = 2.75% per test**

## Implementation Priority

### **Phase 1: Tree Parser (highest impact)**
- 3 tests targeting the most used functions
- Focus on language detection and basic parsing
- Skip complex AST manipulation details

### **Phase 2: File Access (medium impact)**  
- 3 tests for strategy selection and basic reading
- Skip mmap/streaming implementation details

### **Phase 3: Editor (lower impact)**
- 2 tests for core edit operations
- Skip advanced backup scenarios

## Coverage Strategy

**Focus on high-impact, frequently called functions:**

1. **tree_parser.py** - Target `detect_language()`, `parse_file_content()`, `extract_outline()`
2. **file_access.py** - Target `choose_file_strategy()`, `get_file_info()`, `read_file_content()`  
3. **editor.py** - Target `replace_content()`, `create_backup()`

**Skip low-impact code:**
- Complex error handling branches
- Advanced tree-sitter features 
- Streaming/mmap implementation details
- Utility formatting functions

## Test Principles

1. **High coverage per test** - Target 3-4% coverage gain per test
2. **Focus on core paths** - Test the 80% use cases, not edge cases
3. **Mock external dependencies** - Keep tests fast and isolated
4. **Simple assertions** - Verify core functionality works

## Expected Outcome

**Before:** 25 integration tests, 45% coverage  
**After:** 25 integration + 8 unit tests, 70% coverage

**Efficiency:** 8 tests for 25% coverage improvement = **3.1% per test**

This achieves comprehensive coverage with minimal test overhead while maintaining the principle of "small number of tests, simple code, clear flows."