# Agent Instructions

This file contains instructions and context for AI agents when working on this project.

## Project Overview
Collection of tools for working with documentation and repository analysis.

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
└── repo_modules_by_version/    # Configuration-driven GitHub repository analysis tool
    ├── __init__.py
    ├── main.py                 # CLI entry point with configuration-driven architecture
    ├── config.py              # Repository configuration system with new fields
    ├── github_client.py       # Generic GitHub API client (no hardcoded logic)
    ├── parser_factory.py      # Extensible parsing framework
    ├── repos.json             # Repository configurations with fetch strategies
    ├── parsers/               # Specialized parsers for different repository types
    └── version_cache.py       # Version caching system for performance
```

## Tools

### repo-modules-by-version
**Configuration-driven CLI tool** that allows users to:
- Extract data from GitHub repositories using configurable fetch strategies
- Parse through directories using specialized parsers
- Support interactive menus for preconfigured repositories
- Generate consistent output filenames with custom slugs
- Override versions per repository configuration

**Architecture:**
- **No hardcoded repository logic** - All behavior driven by `repos.json` configuration
- **Flexible fetch strategies** - `full_content`, `filenames_only`, `directory_names`
- **Version override system** - Force specific versions (e.g., master for documentation)
- **Configurable filename generation** - Custom output naming with fallback logic
- **Multi-path parsing** - Support for complex repository structures

**Supported Repositories (via configuration):**
- **Prebid.js** - Modules and adapters (filenames-only strategy, prebid.js output slug)
- **Prebid Server Go** - Bid adapters, analytics, modules (directory-names strategy, prebid.server.go slug)
- **Prebid Server Java** - Bidders, privacy, general modules (directory-names strategy, prebid.server.java slug)
- **Prebid Documentation** - Documentation site (filenames-only strategy, master override, prebid.github.io slug)

**Configuration Fields (repos.json):**
- `fetch_strategy` - How to fetch data: "full_content", "filenames_only", "directory_names" 
- `version_override` - Force specific version (e.g., "master" for docs)
- `output_filename_slug` - Custom filename prefix (e.g., "prebid.js")
- `parser_type` - Specialized parser: "prebid_js", "prebid_server_go", "prebid_server_java", "prebid_docs"
- `paths` - Multi-directory configurations for complex repositories

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

## Adding New Repositories (repo-modules-by-version)
The configuration-driven architecture makes adding new repositories simple:

1. **Add repository configuration to `repos.json`:**
```json
{
  "new-repo": {
    "repo": "owner/repository",
    "description": "Description of the repository",
    "versions": ["master"],
    "parser_type": "default",
    "fetch_strategy": "full_content",
    "output_filename_slug": "custom.name",
    "paths": {
      "Category Name": "path/to/directory"
    }
  }
}
```

2. **Configuration fields:**
   - `fetch_strategy`: "full_content" (files + content), "filenames_only" (just names), "directory_names" (folder structure)
   - `version_override`: Force specific version (optional)
   - `output_filename_slug`: Custom output filename prefix (optional)
   - `parser_type`: Specialized parser or "default"
   - `paths`: Multi-directory configuration (optional)

3. **Create specialized parser (if needed):**
   - Add parser class to `src/repo_modules_by_version/parsers/`
   - Update `parser_factory.py` to register new parser type

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