# Examples

Real-world usage examples showing how AI assistants work with the Largefile MCP Server.

## Code Analysis Examples

### Analyzing Large Python Files

**AI Question:** *"Can you analyze this large Django models file and tell me about the class structure and any potential issues? It's a large file so use largefile."*

**AI Assistant workflow:**
1. Get file overview to understand structure
2. Search for classes and their methods  
3. Look for code issues like TODOs or long functions

```python
# AI gets file structure
overview = get_overview("/path/to/django-models.py")
# Returns: 2,847 lines, 15 classes, semantic outline with Tree-sitter

# AI searches for all class definitions
classes = search_content("/path/to/django-models.py", "class ", max_results=20)
# Returns: Model classes with line numbers and context

# AI examines specific class implementation
model_code = read_content("/path/to/django-models.py", "class User", mode="semantic")
# Returns: Complete class definition with all methods

# AI looks for potential issues
todos = search_content("/path/to/django-models.py", "TODO|FIXME", fuzzy=True)
long_methods = search_content("/path/to/django-models.py", "def ", max_results=50)
# Check each method length using read_content
```

### Exploring Large JavaScript/TypeScript Files

**AI Question:** *"What are all the exported functions in this large TypeScript file and show me their signatures?"*

**AI Assistant workflow:**
```python
# AI gets file overview
overview = get_overview("/path/to/vscode-extension.ts")

# AI searches for export patterns
exports = search_content("/path/to/vscode-extension.ts", "export", fuzzy=True, max_results=30)

# AI reads each exported function
for export in exports:
    if "function" in export.match.lower():
        func_code = read_content("/path/to/vscode-extension.ts", export.line_number, mode="semantic")
        # Shows complete function with types and documentation
```

### Analyzing Go Code Structure

**AI Question:** *"Find all the struct definitions and their methods in this large Go file."*

**AI Assistant workflow:**
```python
# AI searches for Go structs
structs = search_content("/path/to/docker-daemon.go", "type.*struct", max_results=20)

# AI finds methods for each struct
for struct in structs:
    struct_name = struct.match.split()[1]  # Extract struct name
    methods = search_content("/path/to/docker-daemon.go", f"func.*{struct_name}", fuzzy=True)
    
    # AI reads complete struct definition
    struct_def = read_content("/path/to/docker-daemon.go", struct.line_number, mode="semantic")
```

## Documentation Examples

### Working with README Files

**AI Question:** *"Find all the installation methods mentioned in this README file and update the pip install to use uv instead."*

**AI Assistant workflow:**
```python
# AI finds installation instructions
install_sections = search_content("/path/to/readme.md", "install", fuzzy=True, context_lines=3)

# AI reads the installation section
install_content = read_content("/path/to/readme.md", "## Installation", mode="semantic")

# AI replaces pip with uv
edit_result = edit_content(
    "/path/to/readme.md",
    search_text="pip install anthropic",
    replace_text="uv add anthropic",
    preview=True
)
```

### Exploring API Documentation

**AI Question:** *"What are all the available methods in this large API documentation file and can you show me examples of authentication?"*

**AI Assistant workflow:**
```python
# AI analyzes document structure  
overview = get_overview("/path/to/api-docs.md")
# Returns: Section outline, headings, suggested search patterns

# AI finds API methods
methods = search_content("/path/to/api-docs.md", "###", max_results=30)
# Returns: All method headings with context

# AI searches for authentication examples
auth_examples = search_content("/path/to/api-docs.md", "auth", fuzzy=True, context_lines=5)

# AI reads complete authentication section
auth_section = read_content("/path/to/api-docs.md", "## Authentication", mode="semantic")
```

### Updating Documentation

**AI Question:** *"Update all occurrences of 'v1.0' to 'v2.0' in this large documentation file."*

**AI Assistant workflow:**
```python
# AI finds all version references
versions = search_content("/path/to/docs.md", "v1.0", fuzzy=False, max_results=100)

# AI previews all changes first
preview = edit_content("/path/to/docs.md", "v1.0", "v2.0", preview=True)
print(f"Will update {preview.changes_made} occurrences")

# AI applies changes with backup
result = edit_content("/path/to/docs.md", "v1.0", "v2.0", preview=False)
```

## Debugging and Maintenance Examples

### Analyzing Large Log Files

**AI Question:** *"Check this production log file for any critical errors in the last few thousand lines and show me the context around them. Use largefile mcp."*

**AI Assistant workflow:**
```python
# AI gets log file overview
overview = get_overview("/path/to/production.log")
# Returns: 150,000 lines, 2.1GB file size

# AI reads last 2000 lines efficiently using tail mode
recent = read_content("/path/to/production.log", 2000, mode="tail")
# No need to know total line count - just get the end of the file

# AI searches for critical errors in recent entries
errors = search_content("/path/to/production.log", "CRITICAL|ERROR", fuzzy=True, max_results=10)

# AI examines context around each error
for error in errors:
    context = read_content("/path/to/production.log", error.line_number, mode="lines")
    # Shows surrounding log entries for debugging
```

### Finding Configuration Issues

**AI Question:** *"Look through this large config file and find any settings that might be causing performance issues."*

**AI Assistant workflow:**
```python
# AI gets config file overview
overview = get_overview("/path/to/app.conf")

# AI searches for performance-related settings
perf_settings = search_content("/path/to/app.conf", "timeout|cache|pool|thread", fuzzy=True)

# AI examines each setting's context
for setting in perf_settings:
    section = read_content("/path/to/app.conf", setting.line_number, mode="semantic")
    # Shows complete configuration section
```

## Refactoring Examples

### Safe Function Renaming

**AI Question:** *"I need to rename the function `process_data` to `transform_data` throughout this large codebase file. Can you help me do this safely?"*

**AI Assistant workflow:**
```python
# AI finds all usages
usages = search_content("/path/to/codebase.py", "process_data", fuzzy=False, max_results=50)

# AI previews the changes
preview = edit_content(
    "/path/to/codebase.py",
    search_text="process_data",
    replace_text="transform_data", 
    preview=True
)

# AI applies changes after confirmation
result = edit_content(
    "/path/to/codebase.py",
    search_text="process_data",
    replace_text="transform_data",
    preview=False
)
# Creates automatic backup before changes
```

### Code Modernization

**AI Question:** *"Update all the old-style string formatting to use f-strings in this large Python file."*

**AI Assistant workflow:**
```python
# AI finds old-style formatting
old_format = search_content("/path/to/legacy.py", "%s|%d|.format", fuzzy=True, max_results=50)

# AI examines each case and updates appropriately
for match in old_format:
    context = read_content("/path/to/legacy.py", match.line_number, mode="lines")
    
    # AI identifies specific pattern and updates
    if ".format(" in context:
        # Update .format() to f-string
        edit_result = edit_content(
            "/path/to/legacy.py",
            search_text=match.match,
            replace_text="f'...'",  # AI generates appropriate f-string
            preview=True
        )
```

### Removing Deprecated Code

**AI Question:** *"Find and remove all deprecated function calls in this large codebase."*

**AI Assistant workflow:**
```python
# AI searches for deprecated patterns
deprecated = search_content("/path/to/code.py", "deprecated|@deprecated", fuzzy=True)

# AI also searches for specific deprecated functions
old_funcs = search_content("/path/to/code.py", "old_api_call|legacy_method", fuzzy=True)

# AI removes or updates each deprecated usage
for dep in deprecated:
    func_context = read_content("/path/to/code.py", dep.line_number, mode="semantic")
    
    # AI determines replacement and applies
    edit_result = edit_content(
        "/path/to/code.py",
        search_text=dep.match,
        replace_text="new_api_call",  # AI determines correct replacement
        preview=True
    )
```

## Data Analysis Examples

### Processing Large CSV/Data Files

**AI Question:** *"Analyze this large CSV file and tell me about its structure and find any data quality issues."*

**AI Assistant workflow:**
```python
# AI gets file overview
overview = get_overview("/path/to/large_data.csv")

# AI examines header structure
header = read_content("/path/to/large_data.csv", 1, mode="lines")

# AI searches for potential data issues
empty_fields = search_content("/path/to/large_data.csv", ",,|, ,", max_results=20)
invalid_dates = search_content("/path/to/large_data.csv", "[0-9]{2}/[0-9]{2}/[0-9]{2}", fuzzy=True)

# AI samples different sections of the file
middle_line = overview.line_count // 2
sample_data = read_content("/path/to/large_data.csv", middle_line, mode="lines")
```

### License and Legal Text Analysis

**AI Question:** *"Check this large LICENSES file and list all the different license types mentioned."*

**AI Assistant workflow:**
```python
# AI gets overview of licenses file
overview = get_overview("/path/to/LICENSES.md")

# AI searches for common license patterns
licenses = search_content("/path/to/LICENSES.md", "MIT|Apache|GPL|BSD|ISC", fuzzy=True, max_results=50)

# AI reads each license section
license_types = set()
for license_match in licenses:
    license_section = read_content("/path/to/LICENSES.md", license_match.line_number, mode="semantic")
    # AI extracts license type from context
```

## Multi-File Scenarios

### Cross-File Analysis

**AI Question:** *"Find all the imports of 'shared_utils' across these large project files and show me how it's being used."*

**AI Assistant workflow:**
```python
# AI analyzes multiple files
project_files = [
    "/path/to/main.py",
    "/path/to/service.py", 
    "/path/to/handlers.py"
]

all_imports = {}
for file_path in project_files:
    # AI finds imports in each file
    imports = search_content(file_path, "shared_utils", fuzzy=True, max_results=20)
    
    # AI examines usage context
    usages = []
    for imp in imports:
        usage_context = read_content(file_path, imp.line_number, mode="semantic")
        usages.append(usage_context)
    
    all_imports[file_path] = usages
```

## Performance Examples

### Working with Very Large Files

**AI Question:** *"This log file is 2GB - can you find the most recent error entries without loading the whole file?"*

**AI Assistant workflow:**
```python
# AI efficiently handles large files
huge_file = "/path/to/very_large_file.log"  # 2GB log file

# Overview works efficiently regardless of size
overview = get_overview(huge_file)
print(f"Huge file: {overview.line_count:,} lines ({overview.file_size/1024/1024/1024:.2f} GB)")

# Search uses streaming for large files
recent_errors = search_content(huge_file, "ERROR", max_results=10)

# Reading specific sections is fast
if recent_errors:
    latest_error = recent_errors[0]
    context = read_content(huge_file, latest_error.line_number, mode="lines")
```

### Memory-Efficient Processing

**AI Question:** *"Process this large dataset file in a memory-constrained environment."*

**AI Assistant workflow:**
```python
# AI configures for minimal memory usage
import os
os.environ["LARGEFILE_MEMORY_THRESHOLD_MB"] = "10"    # Conservative memory
os.environ["LARGEFILE_MAX_SEARCH_RESULTS"] = "5"      # Limit results

# AI processes file in chunks
large_file = "/path/to/large_dataset.csv"
overview = get_overview(large_file)

# AI searches for specific data patterns
data_sections = search_content(large_file, "^[0-9]{4}-", max_results=10)  # Date patterns
for section in data_sections:
    section_data = read_content(large_file, section.line_number, mode="lines")
    # Process each section individually
```

## v0.2.0 Feature Examples

### Batch Editing - Multiple Changes at Once

**AI Question:** *"Update all the deprecated API methods in this file - there are about 5 different ones."*

**AI Assistant workflow:**
```python
# AI applies all changes in a single atomic operation
result = edit_content(
    "/path/to/api_client.py",
    changes=[
        {"search": "client.get_user(id)", "replace": "client.fetch_user(id)"},
        {"search": "client.post_data(payload)", "replace": "client.send_data(payload)"},
        {"search": "response.status", "replace": "response.status_code"},
        {"search": "from old_api import", "replace": "from new_api import"},
        {"search": "API_V1_URL", "replace": "API_V2_URL"},
    ],
    preview=True
)

# Check results - partial success is supported
print(f"Applied: {result['changes_applied']}, Failed: {result['changes_failed']}")

# Review individual results
for r in result["results"]:
    if r["success"]:
        print(f"Change {r['index']}: OK at line {r['line_number']}")
    else:
        print(f"Change {r['index']}: FAILED - {r['error']}")
        if r.get("similar_matches"):
            print(f"  Did you mean: {r['similar_matches'][0]['content']}?")
```

### Error Recovery with Similar Match Suggestions

**AI Question:** *"Replace the function name 'proces_data' with 'transform_data'."* (typo in search)

**AI Assistant workflow:**
```python
# AI attempts edit with typo
result = edit_content(
    "/path/to/code.py",
    search_text="def proces_data(",  # Typo!
    replace_text="def transform_data(",
    preview=True
)

# Result includes helpful suggestions
if not result["success"]:
    print(f"Search failed for: {result['search_attempted']}")
    print(f"Suggestion: {result['suggestion']}")

    # Similar matches help identify the correct pattern
    for match in result["similar_matches"]:
        print(f"  Line {match['line']}: {match['content']} (similarity: {match['similarity']:.0%})")

    # Output:
    # Search failed for: def proces_data(
    # Suggestion: Did you mean 'def process_data(' on line 42?
    #   Line 42: def process_data( (similarity: 93%)
    #   Line 156: def process_data_batch( (similarity: 85%)
```

### Reverting Bad Edits

**AI Question:** *"That last change broke something. Can you undo it?"*

**AI Assistant workflow:**
```python
# AI reverts to the most recent backup
result = revert_edit("/path/to/broken_code.py")

if result["success"]:
    print(f"Reverted to: {result['reverted_to']['timestamp']}")
    print(f"Your broken version saved as: {result['current_saved_as']['id']}")

    # Can always go back if the revert was wrong
    print("Available backups:")
    for backup in result["available_backups"]:
        print(f"  {backup['id']} - {backup['timestamp']} ({backup['size']} bytes)")

# Or revert to a specific earlier version
result = revert_edit("/path/to/code.py", backup_id="20240115_100000")
```

### Tail Mode for Log Analysis

**AI Question:** *"Check the last 500 lines of this huge log file for errors."*

**AI Assistant workflow:**
```python
# No need to get_overview first or calculate line numbers
# Just read directly from the end

# Get last 500 lines efficiently
recent = read_content("/path/to/huge.log", 500, mode="tail")
print(f"Read {recent['lines_read']} lines from file with {recent['total_lines']} total lines")

# Now search within those recent lines
# Or process the content directly
if "ERROR" in recent["content"]:
    print("Found errors in recent log entries")

# Tail mode works with any file size - uses memory-efficient deque
giant_log = "/path/to/10gb_production.log"
last_1000 = read_content(giant_log, 1000, mode="tail")
# Returns quickly without loading entire file
```

### Combined Workflow - Refactor with Safety Net

**AI Question:** *"Rename 'UserManager' to 'UserService' throughout the codebase file, but make sure I can undo if something breaks."*

**AI Assistant workflow:**
```python
# Step 1: Find all occurrences
usages = search_content("/path/to/app.py", "UserManager", fuzzy=False, max_results=50)
print(f"Found {len(usages['results'])} occurrences")

# Step 2: Preview batch changes
result = edit_content(
    "/path/to/app.py",
    changes=[
        {"search": "class UserManager", "replace": "class UserService"},
        {"search": "UserManager(", "replace": "UserService("},
        {"search": ": UserManager", "replace": ": UserService"},  # Type hints
        {"search": "-> UserManager", "replace": "-> UserService"},  # Return types
    ],
    preview=True
)

# Step 3: Review preview
print(result["preview"])

# Step 4: Apply if looks good
if input("Apply changes? (y/n): ") == "y":
    result = edit_content(
        "/path/to/app.py",
        changes=[...],  # Same changes
        preview=False
    )
    print(f"Backup created: {result['backup_created']}")

# Step 5: If something breaks, revert
# revert_edit("/path/to/app.py")  # Instant recovery
```

---

These examples demonstrate how AI assistants use the Largefile MCP Server to handle real-world scenarios with large files, from code analysis to refactoring to data processing, with robust error recovery and batch operations.