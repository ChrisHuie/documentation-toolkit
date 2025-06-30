# Gemini Instructions

This file contains instructions and context for Gemini when working on this project.

## Project Overview
Collection of tools for working with documentation and repository analysis.

## Project Structure
```
src/
├── __init__.py
├── shared_utilities/           # Shared infrastructure for all tools
│   ├── __init__.py
│   ├── filename_generator.py  # Consistent filename generation across tools
│   ├── github_client.py       # Generic GitHub API client with caching
│   ├── logging_config.py      # Structured logging with OpenTelemetry
│   ├── base_output_formatter.py # Base class for extensible multi-format output
│   ├── cli_base.py            # Modular CLI components for consistency
│   ├── data_normalizer.py     # Data normalization for consistent output across formats
│   ├── report_formatter.py    # Generic report formatting for common patterns
│   ├── rate_limit_manager.py  # Global rate limiting for API calls
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
├── supported_mediatypes/      # Media type extraction tool for Prebid.js adapters
│   ├── __init__.py
│   ├── main.py                # CLI entry point for media type analysis
│   ├── extractor.py           # Logic for extracting media types from JavaScript
│   └── output_formatter.py    # Specialized formatting for media type data
└── module_compare/            # Module comparison tool for versions and repositories
    ├── __init__.py
    ├── main.py                # CLI entry point for module comparison
    ├── comparator.py          # Core comparison logic
    ├── data_models.py         # Data models for comparison results
    └── output_formatter.py    # Extends ReportFormatter for comparison output

Other project directories:
├── docs/                      # Additional documentation
│   ├── cli_consistency_analysis.md  # Analysis of CLI patterns across tools
│   └── cli_implementation_plan.md   # Plan for CLI standardization
├── tests/                     # Test suite for all tools
├── cache/                     # Cached data for performance
├── logs/                      # Application logs
└── output/                    # Generated output files
```

## Tools

### repo-modules
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

### supported-mediatypes
**Media type extraction tool** for Prebid.js bid adapters:
- Extract supported media types (banner, video, native) from bid adapter source code
- Analyze individual adapters or all adapters in a version
- Generate summary statistics and combination analysis
- Multiple output formats with consistent data across all formats

**Key Features:**
- **Smart Detection** - Multiple patterns to detect media type support
- **Summary Statistics** - Percentages and counts for media types and combinations
- **Flexible Output** - Table (with optional JSON), CSV, JSON, Markdown, YAML, HTML
- **Modular Architecture** - Minimal tool-specific code, leverages shared utilities
- **ANSI Formatting** - Bold adapter names in terminal output
- **Order-Independent** - Normalizes media type combinations regardless of import order

**Architecture:**
- **MediaTypeExtractor** - Extracts media types using regex patterns
- **MediaTypeOutputFormatter** - Minimal formatter extending ReportFormatter
- **Uses shared utilities** - DataNormalizer, ReportFormatter, BaseOutputFormatter

**Usage:**
```bash
# Show all adapters with default table output
supported-mediatypes

# Specific version with JSON at bottom
supported-mediatypes --version v9.51.0 --show-json

# Analyze specific adapter
supported-mediatypes --adapter appnexus

# Show summary statistics
supported-mediatypes --summary

# Output to file in different formats
supported-mediatypes --format csv --output media_types.csv
supported-mediatypes --format json --output media_types.json
supported-mediatypes --format markdown --output media_types.md
```

**Output Example:**
```
Prebid.js Supported Media Types Report
Version: v9.51.0
Total Adapters: 5
Adapters with Media Types: 5
============================================================

Adapters and Supported Media Types:
============================================================

**appnexus**: [banner, native, video]
**criteo**: [banner, video]
**pubmatic**: [banner, native, video]
**rubicon**: [banner, video]

============================================================
```

### alias-mappings
**Prebid.js alias mapping analysis tool** that identifies and analyzes bidder alias relationships:
- Extract alias mappings from Prebid.js source code
- Generate comprehensive reports showing alias-to-bidder relationships
- Support multiple output formats (table, CSV, JSON)
- Track alias evolution across different versions

**Key Features:**
- **Alias Discovery** - Automatically finds all bidder aliases in Prebid.js
- **Relationship Mapping** - Shows which aliases map to which core bidders
- **Version Tracking** - Analyze alias changes across Prebid.js versions
- **Multiple Formats** - Output as human-readable tables or machine-readable JSON/CSV
- **Leverages Shared Infrastructure** - Uses common GitHub client and configuration

**Usage:**
```bash
# Analyze current/latest version
alias-mappings

# Analyze specific version
alias-mappings --version v9.51.0

# Output as JSON
alias-mappings --format json

# Output as CSV
alias-mappings --format csv

# Save to file
alias-mappings --output alias_report.txt
```

### supported-mediatypes
**Media type extraction tool** for Prebid.js bid adapters that analyzes supported ad formats:
- Extract media types (banner, video, native) from bid adapter source code
- Generate comprehensive reports showing media type support across adapters
- Support multiple output formats (table, CSV, JSON, Markdown, YAML, HTML)
- Analyze specific adapters or entire repository
- Provide summary statistics on media type usage

**Key Features:**
- **Smart Detection** - Multiple patterns to identify media type support
- **Comprehensive Analysis** - Checks imports, declarations, and usage patterns
- **Flexible Output** - Multiple formats for different use cases
- **Summary Statistics** - Overview of media type adoption across adapters
- **Extensible Architecture** - Built on shared base output formatter

**Usage:**
```bash
# Analyze latest version
supported-mediatypes

# Analyze specific version
supported-mediatypes --version v9.51.0

# Analyze specific adapter
supported-mediatypes --adapter appnexus

# Show summary statistics
supported-mediatypes --summary

# Output as JSON
supported-mediatypes --format json

# Output as CSV (Excel-friendly)
supported-mediatypes --format csv

# Output as Markdown
supported-mediatypes --format markdown

# Save to specific file
supported-mediatypes --format csv --output media_types_report.csv
```

**Output Formats:**
- **table** - Human-readable console output (default)
- **json** - Machine-readable JSON format
- **csv** - Excel-compatible CSV with Yes/No columns
- **markdown** - Documentation-ready Markdown tables
- **yaml** - YAML format for configuration files
- **html** - HTML report with basic styling

### module-compare
**Module comparison tool** for analyzing differences between versions and repositories:
- Compare modules between two versions of the same repository (version comparison)
- Compare modules between different repositories (cross-repository comparison)
- Track cumulative changes across intermediate versions (cumulative comparison)
- Show comprehensive statistics by module type/category
- Support for unchanged/common module visibility via --show-unchanged flag
- Multiple output formats with detailed change analysis

**Key Features:**
- **Three Comparison Modes** - Direct, cumulative, and cross-repository
- **Smart Matching** - Matches modules by name and category for accurate comparison
- **Change Focus** - By default shows only changes, not unchanged/common modules
- **Comprehensive Statistics** - Category breakdowns, overlap analysis
- **Flexible Output** - All standard formats (table, JSON, CSV, Markdown, YAML, HTML)
- **Automatic Defaults** - Cumulative mode defaults to true for same-repo comparisons

**Comparison Modes:**
1. **Direct Comparison** - Shows modules added/removed between two specific versions (endpoint comparison)
2. **Cumulative Comparison** - Tracks ALL module changes across intermediate versions (default for same repo)
3. **Repository Comparison** - Shows modules unique to each repo and common modules

**Usage:**
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

# Use direct comparison instead of cumulative
module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0 --no-cumulative

# Output to different formats
module-compare --from prebid-js:v9.0.0 --to prebid-js:v9.51.0 --format json
module-compare --from prebid-js --to prebid-server --format csv --output comparison.csv

# List available repositories
module-compare --list-repos
```

**Output Examples:**

Version Comparison (changes only):
```
Module Comparison: prebid-js (v9.0.0 → v9.51.0)
================================================

SUMMARY
- Added: 25 modules
- Removed: 3 modules  
- Net Change: +22 modules

DETAILED STATISTICS
Changes by Category:
Category               Added   Removed    Net
Bid Adapters             20         2     +18
Analytics                 3         0      +3
RTD Modules               2         1      +1

MODULE CHANGES
Bid Adapters - Added (20 modules):
  newBidder1              newBidder2
  anotherBidder           yetAnotherBidder
  ...
```

Cumulative Comparison (tracking all changes):
```
Cumulative Module Comparison: prebid-js (v9.0.0 → v9.51.0)
=========================================================

SUMMARY
- Total Changes: 28 modules
- Permanently Added: 25 modules
- Removed: 3 modules  
- Transient: 3 modules

DETAILED STATISTICS
Changes by Category:
Category            Total Added  Still Present  Removed
Bid Adapters                 23             20        3
Analytics                     3              3        0
RTD Modules                   2              2        0

Versions Analyzed: 52 versions from v9.0.0 to v9.51.0

MODULE CHANGES
Bid Adapters - Added (still present):
  adapter1 (added in v9.2.0)
  adapter2 (added in v9.5.0)
  ...

Bid Adapters - Added then removed:
  tempAdapter (added: v9.10.0, removed: v9.25.0)
  ...
```

Repository Comparison (differences only):
```
Module Comparison: prebid-js vs prebid-server
==============================================

SUMMARY  
- Only in prebid-js: 122 modules
- Only in prebid-server: 45 modules
- Common modules: 50

DETAILED STATISTICS
Category Distribution:
Unique to prebid-js: Analytics, RTD Modules, ID Systems
Unique to prebid-server: Exchange Modules
Common categories: Bid Adapters

MODULE CHANGES
Bid Adapters - Only in prebid-js (95 modules):
  clientOnlyAdapter1      clientOnlyAdapter2
  browserSpecific         ...
```

## Shared Infrastructure

The project follows a shared utilities pattern where common functionality is centralized in `src/shared_utilities/`:

- **GitHub Client** - Unified API client with rate limiting and caching
- **Repository Configuration** - Centralized configuration management for all repository types
- **Filename Generation** - Consistent naming conventions across all tools
- **Output Formatting** - Common formatting utilities for reports
- **Base Output Formatter** - Extensible formatter supporting multiple output formats (JSON, CSV, YAML, HTML, etc.)
- **Output Manager** - Hierarchical directory management for tool outputs organized by tool/repo/version
- **Logging & Telemetry** - Structured logging with OpenTelemetry integration
- **Version Caching** - Performance optimization for repository version queries
- **Rate Limit Manager** - Global rate limiting for API calls

This architecture allows tools to focus on their core functionality while leveraging shared components for common operations.

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

## CLI Consistency

The project uses a modular CLI infrastructure to ensure consistency across all tools:

### Shared CLI Components (cli_base.py)
- **Common Arguments**: Standard flags like `-o/--output`, `-f/--format`, `-q/--quiet`, `-v/--verbose`
- **Repository Arguments**: Shared flags for tools working with GitHub repos
- **Rate Limit Arguments**: Consistent rate limiting controls across API-heavy tools
- **Filter Arguments**: Common filtering options like `--limit`
- **Cache Arguments**: Standardized cache management flags

### Benefits
- Users learn one set of flags that work everywhere
- New tools automatically get common functionality
- Consistent behavior and error handling
- Easy to maintain and extend

### Implementation Status
- Infrastructure created in `shared_utilities/cli_base.py`
- Supports both argparse and click frameworks
- Migration plan documented in `docs/cli_implementation_plan.md`
- Tools will be migrated incrementally to maintain compatibility

For detailed analysis and implementation plans, see:
- `docs/cli_consistency_analysis.md` - Current state analysis
- `docs/cli_implementation_plan.md` - Migration strategy

## Modular Architecture

The project follows a highly modular architecture designed for extensibility and code reuse:

### Output Formatting Architecture
All tools use a three-layer formatting system:

1. **BaseOutputFormatter** (shared_utilities/base_output_formatter.py)
   - Abstract base class defining the interface for all formatters
   - Supports 9 output formats: table, json, csv, yaml, markdown, html, xml, tsv, excel
   - Handles file I/O operations

2. **ReportFormatter** (shared_utilities/report_formatter.py)
   - Generic report formatter for common report patterns
   - Handles headers, metadata, summary statistics, and item listings
   - Automatically normalizes data using DataNormalizer
   - Provides consistent structure across all tools

3. **Tool-specific formatters** (e.g., supported_mediatypes/output_formatter.py)
   - Minimal code - only tool-specific formatting logic
   - Extends ReportFormatter
   - Overrides only what's needed for the specific tool

### Data Normalization
**DataNormalizer** (shared_utilities/data_normalizer.py) ensures all output formats receive the same enriched data:
- Adds percentage calculations to counts
- Handles both raw and pre-normalized data
- Sorts combinations for consistent ordering
- Provides formatting utilities for display

### Benefits of This Architecture
- **DRY Principle**: Common logic is shared, not duplicated
- **Consistency**: All tools output data in the same formats
- **Extensibility**: New tools can leverage existing infrastructure
- **Maintainability**: Changes to formatting logic happen in one place
- **Testing**: Shared utilities have comprehensive test coverage

## Adding New Repositories (repo-modules)
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
   - Add parser class to `src/repo_modules/parsers/`
   - Update `parser_factory.py` to register new parser type

## Output Directory Management

The toolkit uses a hierarchical output directory structure managed by the `OutputManager` utility:

### Directory Structure
```
output/
├── tool-name/
│   ├── repository-name/
│   │   ├── version/
│   │   │   ├── output-file.json
│   │   │   ├── output-file.csv
│   │   │   └── ...
│   │   └── another-version/
│   │       └── ...
│   └── another-repo/
│       └── ...
└── another-tool/
    └── ...
```

### Using OutputManager
```python
from src.shared_utilities import OutputManager, get_output_path, save_output

# Get path for output file (creates directories automatically)
output_path = get_output_path(
    tool_name="supported-mediatypes",
    repo_name="prebid/Prebid.js",
    version="v9.51.0",
    filename="media_types.json"
)
# Result: output/supported-mediatypes/Prebid.js/9.51.0/media_types.json

# Save content directly
save_output(
    content=json_content,
    tool_name="supported-mediatypes",
    repo_name="prebid/Prebid.js",
    version="v9.51.0",
    filename="media_types.json"
)

# Clean up empty directories
cleanup_empty_directories("supported-mediatypes")
```

### Key Features
- **Automatic directory creation** - Directories are created as needed
- **Clean paths** - Repository owner prefixes and version 'v' prefixes are automatically removed
- **Empty directory cleanup** - Remove empty directories after processing
- **File discovery** - Find existing outputs by tool, repo, or version
- **Singleton pattern** - Default manager instance for convenience

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