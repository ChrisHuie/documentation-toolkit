# Gemini Instructions

This file contains instructions and context for Gemini when working on this project.

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
- Extensible parsing system with specialized parsers for Prebid repositories
- Multi-path parsing for complex repository structures
- Automatic filename generation with consistent naming conventions

**Supported Repositories:**
- **Prebid.js** - JavaScript ad serving framework modules and adapters
- **Prebid Server Go** - Go implementation with bid adapters, analytics, and modules
- **Prebid Server Java** - Java implementation with bidders, privacy, and general modules  
- **Prebid Documentation** - Documentation site with adapter and module documentation

**Features:**
- Underscore to space conversion for better readability
- Category-based organization (Bid Adapters, Analytics Adapters, etc.)
- Master version override for documentation repository
- Special suffix handling (RtdProvider, AnalyticsAdapter, VideoProvider)
- JSON output for programmatic access

**Usage:**
```bash
# Interactive mode
repo-modules-by-version

# Direct usage
repo-modules-by-version --repo owner/repo --version v1.0.0

# List available repos
repo-modules-by-version --list-repos

# Examples with preconfigured repos
repo-modules-by-version --repo prebid-js --version v9.51.0
repo-modules-by-version --repo prebid-server --version v3.8.0
repo-modules-by-version --repo prebid-server-java --version v3.27.0
repo-modules-by-version --repo prebid-docs  # Always uses master
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
1. **Format code** - Runs ruff and black formatting
2. **Lint code** - Runs ruff linting checks
3. **Type checking** - Runs mypy type checking
4. **Run tests** - Executes pytest test suite
5. **Update README** - Updates timestamp and ensures README exists
6. **Sync docs** - Syncs all agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

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