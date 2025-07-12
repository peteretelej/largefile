# Model Context Protocol (MCP) Python SDK

## Overview

The Model Context Protocol (MCP) enables applications to provide context to Large Language Models in a standardized way. MCP servers expose three types of capabilities:

- **Resources**: Read-only data that LLMs can access (files, API responses, database queries)
- **Tools**: Functions that LLMs can execute to perform actions
- **Prompts**: Reusable templates for common LLM interactions

## Installation

```bash
# Using uv (recommended)
uv add "mcp[cli]"

# Using pip
pip install "mcp[cli]"
```

## Quick Start

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)  # Use safe evaluation in production

@mcp.resource("config://{key}")
def get_config(key: str) -> str:
    """Get configuration value"""
    configs = {"api_url": "https://api.example.com", "timeout": "30"}
    return configs.get(key, "Not found")

if __name__ == "__main__":
    mcp.run()
```

## Core Concepts

### Tools

Tools allow LLMs to perform actions and can modify state:

```python
@mcp.tool()
def create_file(path: str, content: str) -> str:
    """Create a new file with content"""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_database(query: str, limit: int = 10) -> list[dict]:
    """Search database records"""
    # Your database search implementation
    return [
        {"id": 1, "title": "Result 1", "score": 0.95},
        {"id": 2, "title": "Result 2", "score": 0.87}
    ][:limit]
```

### Resources

Resources expose data using URI templates with parameters:

```python
@mcp.resource("file://{filepath}")
def read_file(filepath: str) -> str:
    """Read file contents"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.resource("api://users/{user_id}")
def get_user(user_id: str) -> str:
    """Get user information"""
    import json
    # Your API call implementation
    user_data = {"id": user_id, "name": "John Doe", "email": "john@example.com"}
    return json.dumps(user_data)

@mcp.resource("status://system")
def get_system_status() -> str:
    """Get system status"""
    import json
    return json.dumps({
        "status": "healthy",
        "uptime": "24h",
        "version": "1.0.0"
    })
```

### Prompts

Prompts provide reusable templates for LLM interactions:

```python
from mcp.server.fastmcp.prompts import base

@mcp.prompt(title="Code Review")
def review_code(language: str, code: str) -> str:
    """Generate code review prompt"""
    return f"Please review this {language} code for best practices, bugs, and improvements:\n\n{code}"

@mcp.prompt(title="Debug Assistant")
def debug_error(error_message: str, context: str) -> list[base.Message]:
    """Create debugging conversation"""
    return [
        base.UserMessage(f"I'm encountering this error: {error_message}"),
        base.UserMessage(f"Context: {context}"),
        base.AssistantMessage("I'll help you debug this issue. Let me analyze the error and context.")
    ]
```

### Structured Output

Tools can return structured data with automatic validation:

```python
from pydantic import BaseModel, Field
from typing import TypedDict

# Using Pydantic models
class SearchResult(BaseModel):
    title: str = Field(description="Result title")
    score: float = Field(description="Relevance score")
    url: str = Field(description="Result URL")

@mcp.tool()
def web_search(query: str) -> list[SearchResult]:
    """Search the web and return structured results"""
    return [
        SearchResult(title="Example Result", score=0.95, url="https://example.com"),
        SearchResult(title="Another Result", score=0.87, url="https://another.com")
    ]

# Using TypedDict
class UserInfo(TypedDict):
    name: str
    email: str
    active: bool

@mcp.tool()
def get_user_info(user_id: str) -> UserInfo:
    """Get user information"""
    return UserInfo(name="John Doe", email="john@example.com", active=True)

# Simple dictionaries
@mcp.tool()
def get_stats() -> dict[str, int]:
    """Get system statistics"""
    return {"users": 150, "files": 1200, "requests": 5000}
```

## Context and Progress

### Progress Reporting

Use context for logging and progress updates during long operations:

```python
from mcp.server.fastmcp import Context

@mcp.tool()
async def process_large_dataset(dataset_path: str, ctx: Context) -> str:
    """Process large dataset with progress updates"""
    import os

    await ctx.info(f"Starting to process: {dataset_path}")

    # Simulate processing with progress updates
    total_items = 1000
    for i in range(total_items):
        # Process item
        if i % 100 == 0:
            progress = i / total_items
            await ctx.report_progress(
                progress=progress,
                total=1.0,
                message=f"Processed {i}/{total_items} items"
            )

    await ctx.info("Processing complete")
    return f"Successfully processed {total_items} items"
```

### Logging

Different log levels for debugging and monitoring:

```python
@mcp.tool()
async def complex_operation(data: str, ctx: Context) -> str:
    """Operation with comprehensive logging"""
    await ctx.debug(f"Starting operation with data: {data[:50]}...")
    await ctx.info("Validating input data")

    try:
        # Your operation logic
        result = perform_operation(data)
        await ctx.info("Operation completed successfully")
        return f"Result: {result}"
    except ValueError as e:
        await ctx.warning(f"Validation error: {str(e)}")
        return f"Validation failed: {str(e)}"
    except Exception as e:
        await ctx.error(f"Operation failed: {str(e)}")
        raise
```

### Notifications

Notify clients about changes:

```python
@mcp.tool()
async def update_data(new_data: str, ctx: Context) -> str:
    """Update data and notify about changes"""
    # Update your data
    save_data(new_data)

    # Notify clients that resources have changed
    await ctx.session.send_resource_list_changed()

    return "Data updated successfully"
```

## Advanced Features

### Completions

Provide completion suggestions for arguments:

```python
from mcp.types import (
    Completion, CompletionArgument, CompletionContext,
    PromptReference, ResourceTemplateReference
)

@mcp.resource("project://{owner}/{repo}")
def get_project(owner: str, repo: str) -> str:
    """Get project information"""
    return f"Project: {owner}/{repo}"

@mcp.completion()
async def handle_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Provide completions for arguments"""

    if isinstance(ref, ResourceTemplateReference):
        if ref.uri == "project://{owner}/{repo}":
            if argument.name == "owner":
                owners = ["microsoft", "google", "facebook", "apple"]
                matches = [o for o in owners if o.startswith(argument.value)]
                return Completion(values=matches, hasMore=False)

            elif argument.name == "repo" and context and context.arguments:
                owner = context.arguments.get("owner")
                if owner == "microsoft":
                    repos = ["vscode", "typescript", "azure-docs"]
                    matches = [r for r in repos if r.startswith(argument.value)]
                    return Completion(values=matches, hasMore=False)

    return None
```

### Sampling (LLM Integration)

Tools can interact with LLMs through sampling:

```python
from mcp.types import SamplingMessage, TextContent

@mcp.tool()
async def generate_summary(text: str, ctx: Context) -> str:
    """Generate summary using LLM"""
    prompt = f"Summarize this text in 2-3 sentences:\n\n{text}"

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt)
            )
        ],
        max_tokens=150
    )

    if result.content.type == "text":
        return result.content.text
    return str(result.content)
```

### User Elicitation

Request additional information from users:

```python
from pydantic import BaseModel, Field

class UserPreferences(BaseModel):
    format: str = Field(description="Output format (json, xml, csv)")
    include_metadata: bool = Field(description="Include metadata in output")

@mcp.tool()
async def export_data(data_type: str, ctx: Context) -> str:
    """Export data with user preferences"""

    # Request preferences from user
    result = await ctx.elicit(
        message="Please specify your export preferences:",
        schema=UserPreferences
    )

    if result.action == "accept" and result.data:
        format_type = result.data.format
        include_meta = result.data.include_metadata
        return f"Exporting {data_type} as {format_type}, metadata: {include_meta}"

    return "Export cancelled"
```

## Server Configuration and Lifecycle

### Application Context

Handle startup/shutdown and shared resources:

```python
from contextlib import asynccontextmanager
from dataclasses import dataclass

@dataclass
class AppContext:
    database: object
    api_client: object
    config: dict

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    # Startup - initialize resources
    db = await init_database()
    client = await init_api_client()
    config = load_config()

    try:
        yield AppContext(database=db, api_client=client, config=config)
    finally:
        # Cleanup - close connections
        await db.close()
        await client.close()

mcp = FastMCP("My Server", lifespan=app_lifespan)

@mcp.tool()
def query_database(sql: str) -> str:
    """Query database using shared connection"""
    ctx = mcp.get_context()
    db = ctx.request_context.lifespan_context.database
    return str(db.execute(sql))
```

### Dependencies

Specify dependencies for deployment:

```python
mcp = FastMCP(
    "My Server",
    dependencies=["requests", "pandas", "sqlalchemy"]
)
```

### Environment Configuration

```python
import os

def get_config():
    return {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///app.db"),
        "api_key": os.getenv("API_KEY"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "max_connections": int(os.getenv("MAX_CONNECTIONS", "10"))
    }

config = get_config()
mcp = FastMCP("My Server")

@mcp.tool()
def get_server_config() -> dict:
    """Get current server configuration"""
    return {k: v for k, v in config.items() if k != "api_key"}
```

## Error Handling Patterns

### Graceful Error Handling

```python
@mcp.tool()
def safe_operation(input_data: str) -> str:
    """Operation with comprehensive error handling"""
    try:
        if not input_data.strip():
            return "Error: Input cannot be empty"

        # Your operation
        result = process_data(input_data)
        return f"Success: {result}"

    except ValueError as e:
        return f"Validation error: {str(e)}"
    except ConnectionError as e:
        return f"Connection failed: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@mcp.resource("data://{id}")
def get_data_safe(id: str) -> str:
    """Resource with error handling"""
    try:
        if not id.isdigit():
            return '{"error": "ID must be numeric"}'

        data = fetch_data(int(id))
        return json.dumps(data)
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'
```

## Client Integration

### Writing MCP Clients

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_mcp_server():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"DEBUG": "true"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # Call a tool
            result = await session.call_tool("calculate", {"expression": "2 + 2"})
            print(f"Result: {result}")

            # Read a resource
            content = await session.read_resource("config://api_url")
            print(f"Config: {content}")
```

### HTTP Client

```python
from mcp.client.streamable_http import streamablehttp_client

async def use_http_server():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search", {"query": "example"})
```

## Running and Testing

### Development Mode

```bash
# Test with MCP Inspector
uv run mcp dev server.py

# With dependencies
uv run mcp dev server.py --with requests --with pandas

# With environment variables
DATABASE_URL=sqlite:///test.db uv run mcp dev server.py
```

### Claude Desktop Integration

```bash
# Install server
uv run mcp install server.py --name "My Server"

# With environment variables
uv run mcp install server.py -v API_KEY=secret -v DEBUG=true
```

### Manual Configuration

Edit Claude Desktop config file:

**macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%AppData%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/project", "run", "server.py"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "API_KEY": "your-api-key",
        "DEBUG": "true"
      }
    }
  }
}
```

## Transport Options

### Stdio (Default)

```python
if __name__ == "__main__":
    mcp.run()  # Uses stdio transport
```

### HTTP/SSE Transport

```python
if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)
```

### Streamable HTTP Transport

```python
# Stateless server for scalability
mcp = FastMCP("My Server", stateless_http=True)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8000)
```

### Mounting in Existing ASGI App

```python
from starlette.applications import Starlette
from starlette.routing import Mount

app = Starlette(routes=[
    Mount("/mcp", app=mcp.sse_app()),
    # Your other routes
])
```

## Authentication

### OAuth Resource Server

```python
from mcp.server.auth.provider import TokenVerifier, TokenInfo
from mcp.server.auth.settings import AuthSettings

class MyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> TokenInfo:
        # Verify with your authorization server
        return TokenInfo(
            subject="user123",
            scopes=["read", "write"],
            expires_at=1234567890
        )

mcp = FastMCP(
    "Protected Server",
    token_verifier=MyTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://auth.example.com",
        resource_server_url="http://localhost:3001",
        required_scopes=["mcp:read", "mcp:write"]
    )
)
```

## Debugging

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
```

### Claude Desktop Logs

```bash
# macOS/Linux
tail -f ~/Library/Logs/Claude/mcp*.log

# Windows
Get-Content $env:AppData\Claude\mcp*.log -Wait
```

### Common Issues

1. **Server not appearing**: Check configuration file syntax and absolute paths
2. **Tool failures**: Verify error handling and return types
3. **Connection issues**: Check transport configuration and network connectivity
4. **Performance**: Use async operations and proper resource management

## Best Practices

1. **Type Annotations**: Always use proper type hints for automatic schema generation
2. **Error Handling**: Return user-friendly error messages, not exceptions
3. **Documentation**: Write clear docstrings for all tools, resources, and prompts
4. **Validation**: Validate inputs before processing
5. **Resource Management**: Use lifecycle management for connections and cleanup
6. **Progress Reporting**: Use context for long-running operations
7. **Security**: Validate file paths and sanitize inputs
8. **Performance**: Use async operations for I/O bound tasks
9. **Configuration**: Use environment variables for deployment settings
10. **Testing**: Test with real services and MCP Inspector during development
