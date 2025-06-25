# documentation-toolkit

Professional toolkit for documentation analysis and repository management.

## Installation

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN
```

## Usage

### repo-modules-by-version

```bash
# Interactive mode
repo-modules-by-version

# Direct usage
repo-modules-by-version --repo owner/repo --version v1.0.0

# List available repos
repo-modules-by-version --list-repos
```

## Development

After making changes, run the validation script:

```bash
validate-project
```

This will:
- Clean up build artifacts and temporary files
- Format code with ruff and black
- Run linting with ruff
- Run type checking with mypy
- Run tests with pytest
- Update documentation timestamps
- Sync agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

### Development Commands

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .

# Type checking
uv run mypy src/

# Run tests
uv run pytest -v

# Full project validation
validate-project
```

## Dependencies

- Python 3.13+
- PyGitHub for GitHub API interactions
- python-dotenv for environment variable management
- click for enhanced CLI features
- mypy for type checking
- loguru for enhanced logging
- pytest for testing
- ruff for fast linting and formatting
- black for code formatting

## Project Structure

```
src/
├── __init__.py
├── dev_tools/                  # Development and validation tools
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point for validation
│   ├── validator.py           # Project validation logic
│   ├── docs_sync.py          # Documentation synchronization
│   └── cleanup.py            # Artifact cleanup utilities
└── repo_modules_by_version/    # Tool for extracting data from GitHub repos by version
    ├── __init__.py
    ├── main.py                 # CLI entry point
    ├── config.py              # Repository configuration system
    ├── github_client.py       # GitHub API client
    └── parser_factory.py      # Extensible parsing framework
```

## Environment Variables

- `GITHUB_TOKEN` - GitHub Personal Access Token for API access (optional but recommended for higher rate limits)

Last updated: 2025-06-25 10:16:22