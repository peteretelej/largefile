# Contributing

## Setup

```bash
git clone https://github.com/peteretelej/largefile.git
cd largefile
uv sync --dev
```

## Development

```bash
# Run all checks (CI validates this)
./scripts/pre-push

# Optional: Auto-run on git push
ln -sf ./scripts/pre-push .git/hooks/pre-push
```

Individual commands:

```bash
uv run pytest                    # Tests
uv run ruff format              # Format
uv run ruff check --fix         # Lint
uv run mypy src/                # Types
```

### Testing Changes

Run integration tests:
```bash
uv run pytest tests/integration/ -v
```

### Testing Individual Tools

Set test file:
```bash
FILE='tests/test_data/python/django-models.py'
```

**get_overview** - File structure analysis:
```bash
uv run python -c "from src.tools import get_overview; r=get_overview('$FILE'); print(f'Lines: {r[\"line_count\"]}, Outline: {len(r[\"outline\"])} items')"
```

**search_content** - Pattern search with fuzzy matching:
```bash
uv run python -c "from src.tools import search_content; r=search_content('$FILE', 'class', max_results=3); print(f'Found {r[\"total_matches\"]} class matches')"
```

**read_content** - Read semantic chunks:
```bash
uv run python -c "from src.tools import read_content; r=read_content('$FILE', 100, mode='semantic'); print(f'Read {len(r[\"content\"])} chars from line 100')"
```

**edit_content** - Search/replace (preview only):
```bash
uv run python -c "from src.tools import edit_content; r=edit_content('$FILE', 'import copy', 'import copy  # comment', preview=True); print(f'Edit preview: {r[\"success\"]}, {r[\"changes_made\"]} changes')"
```

## Guidelines

- Simple, testable code
- Add tests for new features
- Update docs for user-facing changes
- Use environment variables for config

## Pull Requests

1. Open issue for major changes
2. Create feature branch
3. Run `./scripts/pre-push` before submitting
4. Include clear description and test coverage

Quality checks run automatically in CI.

## Publishing New Version

1. Update version in `pyproject.toml`
2. Create and push git tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

CI will automatically build and publish to PyPI.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
