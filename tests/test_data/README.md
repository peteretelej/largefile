# Test Data Files

Curated real-world files for testing the largefile MCP server with comprehensive coverage of file types, sizes, and use cases.

## File Inventory

### Markdown Documentation (5 files)
- **anthropic-readme.md** (25KB) - AI SDK documentation
- **fastapi-docs.md** (24KB) - Web framework documentation  
- **nodejs-readme.md** (41KB) - Runtime documentation
- **openai-readme.md** (27KB) - AI SDK documentation
- **pytorch-readme.md** (27KB) - ML framework documentation

### Programming Languages

#### Tree-sitter Supported (5 files)
- **javascript/lodash-utility.js** (532KB) - Utility library (Large!)
- **typescript/vscode-extension.ts** (32KB) - VS Code extension
- **python/django-models.py** (94KB) - Web framework ORM
- **go/docker-daemon.go** (58KB) - Container runtime
- **rust/serde-derive.rs** (111KB) - Serialization library

#### Non-Tree-sitter (3 files)  
- **csharp/aspnet-controller.cs** (143KB) - .NET web framework
- **java/spring-application.java** (5.1KB) - Spring framework
- **php/laravel-model.php** (69KB) - PHP web framework

### Text Files (2 files)
- **text/shakespeare-complete.txt** (5.4MB) - Classic literature (Streaming test)
- **text/rfc-specification.txt** (413KB) - Technical specification

## Performance Strategy Coverage

- **Memory strategy** (<50KB): 7 files
- **Mmap strategy** (50KB-500KB): 6 files  
- **Streaming strategy** (>500KB): 2 files

## Licensing

All files use permissive open-source licenses:
- **MIT**: 8 files (Anthropic, FastAPI, Node.js, OpenAI, Lodash, ASP.NET, Laravel, VS Code)
- **Apache 2.0**: 4 files (PyTorch, Docker, Spring, Serde)  
- **BSD-3-Clause**: 1 file (Django)
- **Public Domain**: 2 files (Shakespeare, RFC)

## Use Cases

Perfect for testing:
- **AI/ML documentation** search and analysis
- **Web framework code** navigation and editing
- **Large codebase** performance optimization
- **Technical documentation** processing
- **Cross-language** compatibility
- **File size strategy** selection