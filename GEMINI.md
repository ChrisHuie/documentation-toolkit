# Gemini Instructions

This file contains instructions and context for Gemini when working on this project.

This file contains instructions and context for Claude when working on this project.

This file contains instructions and context for Gemini when working on this project.

This file contains instructions and context for Claude when working on this project.

## Project Overview
Collection of tools for working with documentation and repository analysis.

## Project Structure
```
src/
├── __init__.py
└── repo_modules_by_version/    # Tool for extracting data from GitHub repos by version
    ├── __init__.py
    ├── main.py                 # CLI entry point
    ├── config.py              # Repository configuration system
    ├── github_client.py       # GitHub API client
    └── parser_factory.py      # Extensible parsing framework
```

## Tools

### repo-modules-by-version
CLI tool that allows users to:
- Pass in a GitHub repository and version
- Parse through specified directories in the repo
- Extract data using configurable parsers
- Supports interactive menus for preconfigured repos
- Extensible parsing system (default, markdown, OpenAPI)

**Usage:**
```bash
# Interactive mode
repo-modules-by-version

# Direct usage
repo-modules-by-version --repo owner/repo --version v1.0.0

# List available repos
repo-modules-by-version --list-repos
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

## Setup
```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN
```

## Development
- The project uses uv for dependency management
- Each tool is organized as a subpackage under src/
- Use relative imports within tool packages
- Type hints are required throughout
- CLI entry points are defined in pyproject.toml

## Environment Variables
- `GITHUB_TOKEN` - GitHub Personal Access Token for API access (optional but recommended for higher rate limits)

## Adding New Tools
1. Create new directory under `src/your_tool_name/`
2. Add CLI entry point to `pyproject.toml`: `your-tool = "src.your_tool_name.main:main"`
3. Follow the existing pattern for structure and imports

## Post-Change Validation Workflow

**IMPORTANT**: After completing any changes to the codebase, you MUST run the validation script:

```bash
validate-project
```

Or alternatively:
```bash
uv run validate-project
```

This script performs the following steps automatically:
1. **Cleanup artifacts** - Removes build files, cache, and temporary files
2. **Format code** - Runs ruff and black formatting
3. **Lint code** - Runs ruff linting checks
4. **Type checking** - Runs mypy type checking
5. **Run tests** - Executes pytest test suite
6. **Update README** - Updates timestamp and ensures README exists
7. **Sync docs** - Syncs all agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

### When to Run Validation
- After completing ALL file changes for a task
- Before committing code changes
- Before creating pull requests
- After adding new features or fixing bugs

### Validation Requirements
- **Critical**: Formatting and linting must pass
- **Non-critical**: Type checking and tests (warnings only)
- **Always**: Documentation sync and README update

This ensures consistent code quality and keeps all documentation in sync across different AI agents.