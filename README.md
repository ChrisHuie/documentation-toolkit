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

Extract and categorize modules/adapters from GitHub repositories using a **configuration-driven architecture** with specialized parsing for Prebid projects.

**Supported Repositories:**
- **prebid-js** - Prebid.js modules and adapters (filenames-only fetch strategy)
- **prebid-server** - Prebid Server Go implementation (directory structure analysis)
- **prebid-server-java** - Prebid Server Java implementation (directory structure analysis)
- **prebid-docs** - Prebid documentation site (filenames-only with master override)

**Key Features:**
- **Configuration-driven architecture** - No hardcoded repository logic
- **Flexible fetch strategies** - `full_content`, `filenames_only`, `directory_names`
- **Version override system** - Force specific versions (e.g., master for docs)
- **Smart filename generation** - Configurable output naming with fallbacks
- **Multi-path parsing** - Complex repository structures with multiple directories
- **Category-based organization** - Bid Adapters, Analytics Adapters, etc.
- **Extensible parser system** - Easy to add new repositories and parsers

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

### Adding New Repositories

The configuration-driven architecture makes adding new repositories simple:

1. **Add repository to `src/repo_modules_by_version/repos.json`:**
```json
{
  "new-repo": {
    "repo": "owner/repository",
    "description": "Description",
    "versions": ["master"],
    "parser_type": "default",
    "fetch_strategy": "full_content",
    "output_filename_slug": "custom.name"
  }
}
```

2. **Available fetch strategies:**
   - `full_content` - Download files and content (default)
   - `filenames_only` - Just get file names (fast)
   - `directory_names` - Just get folder structure

3. **Optional configurations:**
   - `version_override` - Force specific version
   - `output_filename_slug` - Custom output filename
   - `paths` - Multi-directory parsing

## Development

After making changes, run the validation script:

```bash
validate-project
```

This will:
- Format code with ruff and black
- Run linting with ruff
- Run type checking with mypy
- Run tests with pytest
- Update documentation timestamps
- Sync agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

**Note**: Automatic cleanup functionality has been removed for safety.

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
    ├── main.py                 # CLI entry point with configuration-driven architecture
    ├── config.py              # Repository configuration system with fetch strategies
    ├── github_client.py       # Generic GitHub API client (no hardcoded logic)
    ├── parser_factory.py      # Extensible parsing framework
    ├── repos.json             # Repository configurations with fetch strategies
    ├── parsers/               # Specialized parsers for different repository types
    └── version_cache.py       # Version caching system for performance
```

## Environment Variables

- `GITHUB_TOKEN` - GitHub Personal Access Token for API access (optional but recommended for higher rate limits)

Last updated: 2025-06-28 12:45:56