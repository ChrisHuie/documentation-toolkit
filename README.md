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

### repo-modules

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
repo-modules

# Direct usage
repo-modules --repo owner/repo --version v1.0.0

# List available repos
repo-modules --list-repos

# Examples with preconfigured repos
repo-modules --repo prebid-js --version v9.51.0
repo-modules --repo prebid-server --version v3.8.0
repo-modules --repo prebid-server-java --version v3.27.0
repo-modules --repo prebid-docs  # Always uses master
```

### Adding New Repositories

The configuration-driven architecture makes adding new repositories simple:

1. **Add repository to `src/repo_modules/repos.json`:**
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

### module-history

Track when modules were first introduced in Prebid.js across all versions:

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
```

### alias-mappings

Extract and analyze bidder alias relationships from Prebid.js:

```bash
# Analyze current/latest version
alias-mappings

# Analyze specific version
alias-mappings --version v9.51.0

# Output as JSON
alias-mappings --format json

# Save to file
alias-mappings --output alias_report.txt
```

### supported-mediatypes

Extract and analyze supported media types (banner, video, native) from Prebid.js bid adapters:

```bash
# Analyze latest version
supported-mediatypes

# Analyze specific version
supported-mediatypes --version v9.51.0

# Analyze specific adapter
supported-mediatypes --adapter appnexus

# Show summary statistics
supported-mediatypes --summary

# Output as CSV (Excel-friendly)
supported-mediatypes --format csv

# Save to specific file
supported-mediatypes --format json --output media_types.json
```

**Features:**
- Smart detection of media type support from source code
- Multiple output formats (table, JSON, CSV, Markdown, YAML, HTML)
- Summary statistics showing media type adoption
- Per-adapter analysis capability

### module-compare

Compare modules between different versions or repositories to track changes and analyze differences:

```bash
# Interactive mode
module-compare

# Compare versions of same repository
module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0
module-compare --from prebid-js:v9.0.0 --to prebid-js:v9.51.0

# Compare different repositories
module-compare --from prebid-js:v9.51.0 --to prebid-server:v3.8.0
module-compare --from prebid-js --to prebid-server-java

# Show all modules including unchanged/common
module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0 --show-unchanged

# Output to different formats
module-compare --from prebid-js:v9.0.0 --to prebid-js:v9.51.0 --format json
module-compare --from prebid-js --to prebid-server --format csv --output comparison.csv

# Use direct comparison instead of cumulative (for same repo)
module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0 --no-cumulative

# Force cumulative comparison for cross-repo (normally disabled)
module-compare --from prebid-js:v9.0.0 --to prebid-js:master --cumulative
```

**Features:**
- Three comparison modes: direct, cumulative, and cross-repository
- Smart module matching by name and category
- Comprehensive statistics with category breakdowns
- Focus on changes by default (use --show-unchanged to see all)
- Multiple output formats with detailed change analysis
- Automatic cumulative tracking for same-repository comparisons

**Comparison Modes:**
- **Direct Comparison**: Shows modules added/removed between two specific versions (endpoint comparison)
- **Cumulative Comparison**: Tracks ALL module changes across intermediate versions (default for same repo)
- **Repository Comparison**: Shows modules unique to each repository and common modules (cross-repo)

**Cumulative vs Direct:**
- **Cumulative** (default for same repo): Shows all modules that were added/removed at any point between versions
- **Direct** (use --no-cumulative): Shows only the net difference between the two endpoints

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

## Architecture

The toolkit follows a highly modular architecture designed for extensibility:

### Shared Utilities
All tools leverage common infrastructure in `src/shared_utilities/`:

- **Output Formatting**: Three-layer system for consistent multi-format output
  - `BaseOutputFormatter` - Abstract base supporting 9 formats
  - `ReportFormatter` - Generic report patterns (headers, summaries, items)
  - Tool-specific formatters - Minimal code, only tool-specific logic

- **Data Normalization**: `DataNormalizer` ensures consistent data across formats
  - Adds percentage calculations automatically
  - Handles raw and pre-normalized data
  - Sorts combinations for consistent ordering

- **CLI Infrastructure**: `cli_base.py` provides modular CLI components
  - Common argument definitions for consistency
  - Support for both argparse and click
  - Reusable argument sets (output, format, repository, rate limiting)
  - See `docs/cli_consistency_analysis.md` and `docs/cli_implementation_plan.md`

- **Other Utilities**:
  - `github_client.py` - Shared GitHub API client with caching
  - `repository_config.py` - Configuration management
  - `version_cache.py` - Performance optimization
  - `logging_config.py` - Structured logging with OpenTelemetry
  - `output_manager.py` - Hierarchical directory management for tool outputs

### Benefits
- **DRY Principle**: Common logic shared, not duplicated
- **Consistency**: All tools output in same formats
- **Extensibility**: New tools leverage existing infrastructure
- **Maintainability**: Changes happen in one place
- **Testing**: Comprehensive test coverage for shared utilities

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
├── shared_utilities/           # Shared infrastructure for all tools
│   ├── __init__.py
│   ├── base_output_formatter.py # Base class for output formatting
│   ├── cli_base.py            # Modular CLI components for consistency
│   ├── data_normalizer.py     # Data normalization for consistent output
│   ├── filename_generator.py  # Consistent filename generation across tools
│   ├── github_client.py       # Generic GitHub API client with caching
│   ├── logging_config.py      # Structured logging with OpenTelemetry
│   ├── output_formatter.py    # Common output formatting utilities
│   ├── rate_limit_manager.py  # Global rate limiting for API calls
│   ├── report_formatter.py    # Generic report formatting for tools
│   ├── repository_config.py   # Shared repository configuration management
│   ├── telemetry.py          # OpenTelemetry instrumentation
│   └── version_cache.py       # Version caching system for performance
├── dev_tools/                  # Development and validation tools
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point for validation
│   ├── validator.py           # Project validation logic
│   └── docs_sync.py          # Documentation synchronization
├── repo_modules/              # Configuration-driven GitHub repository analysis tool
│   ├── __init__.py
│   ├── main.py                # CLI entry point with configuration-driven architecture
│   ├── config.py              # Repository configuration system with new fields
│   ├── parser_factory.py      # Extensible parsing framework with specialized parsers
│   └── repos.json             # Repository configurations with fetch strategies
├── module_history/            # Historical module analysis tool
│   ├── __init__.py
│   ├── main.py                # CLI entry point for historical analysis
│   ├── config.py              # Configuration for module history analysis
│   ├── core.py                # Core analysis logic
│   ├── data_models.py         # Data models for module history
│   └── output_formatter.py    # Specialized output formatting
├── alias_mappings/            # Prebid.js alias mapping tool
│   ├── __init__.py
│   ├── main.py                # CLI entry point for alias mappings
│   └── alias_finder.py        # Logic for finding and mapping aliases
└── supported_mediatypes/      # Media type extraction tool for Prebid.js adapters
    ├── __init__.py
    ├── main.py                # CLI entry point for media type analysis
    ├── extractor.py           # Logic for extracting media types from JavaScript
    └── output_formatter.py    # Specialized formatting for media type data

Other project directories:
├── docs/                      # Additional documentation
│   ├── cli_consistency_analysis.md  # Analysis of CLI patterns
│   └── cli_implementation_plan.md   # Plan for CLI standardization
├── tests/                     # Test suite for all tools
├── cache/                     # Cached data for performance
├── logs/                      # Application logs
└── output/                    # Generated output files
```

## Environment Variables

- `GITHUB_TOKEN` - GitHub Personal Access Token for API access (optional but recommended for higher rate limits)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR) - defaults to INFO
- `ENABLE_FILE_LOGGING` - Enable file logging (true/false) - defaults to true
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint for distributed tracing (optional)
- `OTEL_SERVICE_NAME` - Service name for telemetry identification (optional)

Last updated: 2025-06-30 11:27:54