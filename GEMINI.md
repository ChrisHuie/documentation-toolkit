# Gemini Instructions

This file contains instructions and context for Gemini when working on this project.

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

### module-history
**Historical analysis tool** that tracks when modules were first introduced in Prebid.js:
- Analyze module introduction timeline across major versions
- Generate historical reports showing first appearance of each module
- Support multiple output formats (table, CSV, JSON)
- Cache results for performance and rate limit efficiency
- Filter by module type or major version

**Key Features:**
- **Comprehensive Analysis** - Tracks all module types (bid adapters, analytics, RTD, identity, etc.)
- **Version Timeline** - Shows exactly when each module was first introduced
- **Smart Caching** - Avoids repeated GitHub API calls with intelligent cache management
- **Flexible Output** - Table, CSV, or JSON formats with filtering options
- **Progress Tracking** - Real-time progress indicators for long-running analyses
- **Error Resilience** - Graceful handling of API limits, network issues, and missing data

**Architecture:**
- **Leverages Existing Infrastructure** - Uses repo-modules version cache and GitHub client
- **Semantic Version Sorting** - Properly orders versions for accurate historical analysis
- **Rate Limit Aware** - Respects GitHub API limits with intelligent delays
- **Robust Error Handling** - Continues analysis even when individual versions fail
- **Memory Efficient** - Processes large datasets without excessive memory usage

**Usage:**
```bash
# Show all modules in table format
module-history

# Show only bid adapters as CSV
module-history --type bid_adapters --format csv

# Show modules introduced in v2.x.x
module-history --major-version 2

# Save JSON output to file
module-history --format json -o module_history.json

# Force refresh of cached data
module-history --force-refresh

# Clear cache
module-history --clear-cache

# Show cache information
module-history --cache-info

# Quiet mode (no progress indicators)
module-history --quiet

# Use specific GitHub token
module-history --token your_github_token
```

**Output Example:**
```
📦 Bid Adapters (150 modules)
----------------------------------------
  33across
    First Version: v2.15.0
    Major Version: 2
    File Path: modules/33acrossBidAdapter.js

  appnexus
    First Version: v0.1.1
    Major Version: 0
    File Path: modules/appnexusBidAdapter.js
```

**Cache Management:**
- Cache stored in `cache/module_history/` directory
- Automatic cache validation and migration
- Supports force refresh to update with latest data
- Cache info command shows analysis metadata and statistics

## Dependencies
- Python 3.13+
- PyGitHub for GitHub API interactions
- python-dotenv for environment variable management
- click for enhanced CLI features
- mypy for type checking
- loguru for structured logging with OpenTelemetry integration
- pytest for testing
- ruff for fast linting and formatting
- black for code formatting
- opentelemetry for observability and tracing

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
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR) - defaults to INFO
- `ENABLE_FILE_LOGGING` - Enable file logging (true/false) - defaults to true
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint for distributed tracing (optional)
- `OTEL_SERVICE_NAME` - Service name for telemetry identification (optional)

## Logging and Observability

The toolkit uses structured logging with OpenTelemetry integration for comprehensive observability:

### Structured Logging
- **Framework**: Loguru with structured JSON output for production
- **Automatic Configuration**: Logging is auto-configured on import with environment-based settings
- **File Rotation**: Log files are automatically rotated at 10MB with 30-day retention
- **Contextual Information**: All logs include service name, component, operation context

### OpenTelemetry Integration
- **Distributed Tracing**: Track operations across components with spans
- **Metrics Collection**: Performance and business metrics
- **Automatic Instrumentation**: HTTP requests and database operations
- **OTLP Export**: Compatible with standard observability platforms

### Usage Example
```python
from src.shared_utilities import get_logger

logger = get_logger(__name__)

# Structured logging with context
logger.info(
    "Operation completed",
    operation="fetch_repository",
    repo="owner/repo",
    duration_seconds=1.23,
    files_processed=150,
)
```

### Log Configuration
```bash
# Environment-based configuration
export LOG_LEVEL=DEBUG
export ENABLE_FILE_LOGGING=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

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