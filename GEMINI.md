# Gemini Instructions

This file contains instructions and context for Gemini when working on this project.

This file contains comprehensive instructions and context for Claude when working on the documentation-toolkit project.

## Project Overview

The **Documentation Toolkit** is a sophisticated Python toolkit for analyzing GitHub repositories and extracting structured data about modules, adapters, and documentation. It's specifically optimized for Prebid ecosystem projects but designed to be extensible to any repository.

### Core Philosophy
- **Configuration-Driven Architecture**: No hardcoded repository logic - all behavior defined in configuration
- **Intelligent Rate Limiting**: Sophisticated GitHub API rate management to prevent exhaustion
- **Historical Analysis**: Track when modules were introduced and in which versions
- **Professional Quality**: Type safety, comprehensive testing, validation workflows

## Project Structure

```
documentation-toolkit/
├── src/
│   ├── repo_modules/           # Primary tool for repository analysis
│   │   ├── main.py            # CLI entry point with interactive menu
│   │   ├── config.py          # Repository configuration management
│   │   ├── github_client.py   # GitHub API client with caching
│   │   ├── parser_factory.py  # Extensible parser framework
│   │   ├── module_history.py  # Historical data tracking system
│   │   ├── build_history_cli.py # Historical data builder CLI
│   │   ├── version_cache.py   # Version discovery caching
│   │   └── repos.json         # Repository configurations
│   ├── alias_mappings/         # Alias discovery tool
│   │   ├── main.py            # CLI for alias extraction
│   │   └── alias_finder.py    # Core alias extraction logic
│   ├── shared_utilities/       # Common functionality across tools
│   │   ├── rate_limit_manager.py # Centralized GitHub API rate limiting
│   │   ├── output_formatter.py   # Consistent file generation
│   │   ├── filename_generator.py # Standardized naming conventions
│   │   └── telemetry.py          # OpenTelemetry instrumentation
│   └── dev_tools/              # Development and validation tools
│       ├── cli.py             # Project validation CLI
│       ├── validator.py       # Code quality validation
│       └── docs_sync.py       # Documentation synchronization
├── tests/                      # Comprehensive test suite
├── cache/                      # Performance optimization caching
│   ├── versions/              # Version discovery cache
│   └── history/               # Historical data cache
└── pyproject.toml             # Project configuration
```

## Available Tools

### 1. repo-modules (Primary Tool)
**Entry Point**: `repo-modules` command  
**Location**: `src/repo_modules/main.py`

**Purpose**: Extract and categorize modules/adapters from GitHub repositories

**Key Commands**:
```bash
# Interactive mode with guided repository selection
repo-modules

# Direct usage with specific repository
repo-modules --repo prebid-js --version v9.51.0

# With historical data enrichment
repo-modules --repo prebid-js --version v9.51.0 --use-cached-history

# List available preconfigured repositories
repo-modules --list-repos

# Custom repository
repo-modules --repo owner/custom-repo --version main
```

**Configuration**: Driven by `src/repo_modules/repos.json`

**Supported Repositories**:
- **prebid-js**: Prebid.js modules (bid adapters, analytics, RTD, identity modules)
- **prebid-server**: Prebid Server Go (adapters, analytics, modules)  
- **prebid-server-java**: Prebid Server Java (bidders, privacy, modules)
- **prebid-docs**: Prebid documentation site

### 2. build-module-history (Historical Data Builder)
**Entry Point**: `build-module-history` command  
**Location**: `src/repo_modules/build_history_cli.py`

**Purpose**: Build comprehensive historical data cache showing when each module was first introduced

**Key Commands**:
```bash
# Build complete historical cache
build-module-history --repo prebid-js

# Incremental updates (only process uncached modules)
build-module-history --repo prebid-js --incremental

# Custom batch processing with rate limiting
build-module-history --repo prebid-js --batch-size 10 --incremental

# Check current cache status
build-module-history --repo prebid-js --status
```

**Critical Features**:
- **Intelligent Rate Limiting**: Uses shared rate limit manager to prevent API exhaustion
- **File Path Collision Prevention**: Uses full file paths as cache keys to prevent conflicts between module types
- **Enhanced File Path Detection**: Handles case sensitivity and component type mismatches
- **Incremental Processing**: Only processes modules not already cached

### 3. alias-mappings (Alias Discovery Tool)
**Entry Point**: `alias-mappings` command  
**Location**: `src/alias_mappings/main.py`

**Purpose**: Find and extract bid adapter aliases from repository files

**Key Commands**:
```bash
# JavaScript mode (Prebid.js)
alias-mappings --mode js --repo prebid-js --version v9.51.0

# YAML mode (Prebid Server Go)
alias-mappings --mode server --repo prebid-server --version v3.8.0

# Java YAML mode (Prebid Server Java)
alias-mappings --mode java-server --repo prebid-server-java --version v3.27.0
```

### 4. validate-project (Development Tool)
**Entry Point**: `validate-project` command  
**Location**: `src/dev_tools/cli.py`

**Purpose**: Comprehensive project validation and maintenance

**Validation Pipeline**:
1. **Code Formatting**: ruff format + black
2. **Linting**: ruff check for code quality
3. **Type Checking**: mypy for type safety
4. **Testing**: pytest for functionality
5. **Documentation**: README timestamp updates
6. **Synchronization**: Agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

## Key Architectural Components

### Configuration System (`src/repo_modules/config.py`)

**Repository Configuration Schema**:
```json
{
  "repository-key": {
    "repo": "owner/repository-name",
    "description": "Human-readable description",
    "versions": ["master", "v1.0.0", "v2.0.0"],
    "parser_type": "specialized_parser",
    "fetch_strategy": "filenames_only",
    "output_filename_slug": "custom.name",
    "version_override": "master",
    "paths": {
      "Category Name": "path/to/directory"
    }
  }
}
```

**Configuration Fields**:
- `repo`: GitHub repository in "owner/name" format (Required)
- `description`: Human-readable description (Required)
- `versions`: Available versions for this repository (Required)
- `parser_type`: Parser to use (`default`, `prebid_js`, `prebid_server_go`, `prebid_server_java`, `prebid_docs`)
- `fetch_strategy`: Data fetching approach (`full_content`, `filenames_only`, `directory_names`)
- `output_filename_slug`: Custom prefix for output files (Optional)
- `version_override`: Force specific version regardless of user input (Optional)
- `paths`: Multi-directory parsing configuration (Optional)

### Rate Limiting System (`src/shared_utilities/rate_limit_manager.py`)

**Critical Component**: Centralized GitHub API rate limiting to prevent exhaustion

**Key Features**:
- **Adaptive Throttling**: Adjusts delays based on remaining GitHub API quota
- **Cross-Tool Awareness**: Single global instance shared across all tools
- **Safety Buffers**: Keeps requests in reserve to prevent exhaustion
- **Intelligent Batch Sizing**: Dynamically adjusts batch sizes based on available quota

**Usage Pattern**:
```python
from src.shared_utilities import global_rate_limit_manager

# Check if safe to make requests
is_safe, reason = global_rate_limit_manager.check_rate_limit_safety(10)

# Make rate-limited request
response = global_rate_limit_manager.make_rate_limited_request(
    requests.get, "tool_name", url, params=params, headers=headers
)
```

**Rate Limiting Strategy**:
- **< 50% usage**: Minimal delay (0.5s)
- **50-80% usage**: Moderate scaling (1-2.2s)
- **> 80% usage**: Aggressive throttling (2-4s)
- **Near exhaustion**: Spread remaining requests over time window

### Historical Data System (`src/repo_modules/module_history.py`)

**Purpose**: Track when modules were first introduced to repositories

**Key Components**:
- **ModuleHistoryInfo**: Data structure for historical information
- **ModuleHistoryTracker**: Core tracking and caching logic
- **File Path-Based Caching**: Prevents collisions between module types

**Critical Implementation Details**:
- **Cache Keys**: Uses full file paths (e.g., `modules/exampleBidAdapter.js`) to prevent conflicts
- **Component Type Awareness**: Handles different module types (bidder, analytics, rtd, userId)
- **Case Sensitivity**: Applies corrections for known problematic module names
- **File Existence Validation**: Verifies paths before making API calls

**Cache Structure**:
```json
{
  "modules/exampleBidAdapter.js": {
    "name": "example",
    "first_commit_date": "2018-03-15T10:30:00Z",
    "first_commit_sha": "abc123...",
    "first_release_version": "v1.5.0",
    "first_release_date": "2018-04-01T00:00:00Z",
    "file_path": "modules/exampleBidAdapter.js"
  }
}
```

### Parser Framework (`src/repo_modules/parser_factory.py`)

**Extensible System**: Factory pattern for repository-specific parsing logic

**Available Parsers**:
- **DefaultParser**: Basic file listing for generic repositories
- **PrebidJSParser**: Specialized for Prebid.js with metadata-driven parsing
- **PrebidServerGoParser**: Directory structure analysis for Go implementation
- **PrebidServerJavaParser**: Java package parsing for Java implementation
- **PrebidDocsParser**: Markdown analysis for documentation sites

**Adding New Parsers**:
```python
class CustomParser(BaseParser):
    def parse(self, data: dict[str, Any]) -> str:
        # Custom parsing logic
        return formatted_output

# Register in factory
_parsers = {
    "custom_parser": CustomParser,
    # ... existing parsers
}
```

### GitHub Client (`src/repo_modules/github_client.py`)

**Features**:
- **Multiple Fetch Strategies**: full_content, filenames_only, directory_names
- **Version Caching**: Intelligent caching of version discovery
- **Rate Limit Integration**: Uses shared rate limit manager
- **Multi-Path Support**: Complex repository structures
- **Authentication**: Supports GitHub tokens for higher rate limits

## Important Development Patterns

### Rate Limiting Best Practices

**Always Use Shared Rate Limit Manager**:
```python
# Correct - uses shared rate limiting
response = global_rate_limit_manager.make_rate_limited_request(
    requests.get, "tool_name", url, params=params, headers=headers
)

# Incorrect - bypasses rate limiting
response = requests.get(url, params=params, headers=headers)
```

**Check Safety Before Large Operations**:
```python
is_safe, reason = global_rate_limit_manager.check_rate_limit_safety(batch_size)
if not is_safe:
    logger.warning(f"Rate limit issue: {reason}")
    return
```

### Historical Data Best Practices

**Use File Paths as Cache Keys**:
```python
# Correct - prevents module type collisions
cache_key = file_path  # e.g., "modules/exampleBidAdapter.js"

# Incorrect - causes collisions between bid adapters and analytics adapters
cache_key = module_name  # e.g., "example"
```

**Apply Component Type Detection**:
```python
def _guess_file_path(self, module_name: str, component_type: str | None = None) -> str:
    if component_type == "bidder":
        return f"modules/{module_name}BidAdapter.js"
    elif component_type == "analytics":
        return f"modules/{module_name}AnalyticsAdapter.js"
    # ... handle other types
```

### Error Handling Patterns

**Graceful Degradation**:
```python
try:
    # Primary operation
    result = primary_operation()
except Exception as e:
    logger.warning(f"Primary operation failed: {e}")
    # Fallback operation
    result = fallback_operation()
```

**Comprehensive Logging**:
```python
from loguru import logger

logger.info("Starting operation")
logger.debug(f"Processing {item_count} items")
logger.warning("Non-critical issue occurred")
logger.error("Critical error occurred")
```

## Testing Guidelines

### Test Structure
- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component functionality
- **Mock-Based**: GitHub API interaction simulation
- **Fixture-Driven**: Reusable test data

### Key Test Areas
- Parser functionality across repository types
- Rate limiting behavior under various conditions
- Historical data accuracy and collision prevention
- Configuration loading and validation
- Output format consistency

### Running Tests
```bash
# All tests
uv run pytest -v

# Specific module
uv run pytest tests/test_repo_modules/ -v

# Pattern matching
uv run pytest -k "test_parser" -v

# With coverage
uv run pytest --cov=src/ -v
```

## Common Issues and Solutions

### Rate Limiting Issues

**Problem**: Hitting GitHub API rate limits despite rate limiting
**Symptoms**: 403 errors with "rate limit exceeded" messages
**Solutions**:
1. Check if all API calls use `global_rate_limit_manager.make_rate_limited_request()`
2. Verify GitHub token is properly configured in `.env`
3. Reduce batch sizes for operations with high API usage
4. Temporarily disable features like version detection or file existence checking

### File Path Issues

**Problem**: "No commits found" errors for valid modules
**Symptoms**: Modules exist in repository but historical tracking fails
**Solutions**:
1. Check component type mapping in metadata vs actual file names
2. Apply case corrections for problematic module names
3. Verify file path generation logic matches actual repository structure
4. Use file existence validation before attempting commit history requests

### Module Type Collisions

**Problem**: Different module types with same name overwriting each other
**Symptoms**: Historical data showing wrong dates for modules
**Solutions**:
1. Ensure cache uses full file paths as keys, not module names
2. Verify component type detection is working correctly
3. Check that different module types are processed separately

### Configuration Issues

**Problem**: Repository not found or parser errors
**Symptoms**: Configuration loading failures or parser selection errors
**Solutions**:
1. Verify repository configuration in `repos.json` is valid
2. Check that all required fields are present
3. Ensure parser type matches available parsers in factory
4. Validate fetch strategy is appropriate for repository structure

## Post-Change Validation Workflow

**🚨 MANDATORY**: After completing ANY changes to the codebase, you **MUST** run:

```bash
validate-project
```

**❌ NEVER skip validation** - this is the most critical step in the development process!

**Validation Steps**:
1. **Format code**: Runs ruff and black formatting
2. **Lint code**: Runs ruff linting checks  
3. **Type checking**: Runs mypy type checking
4. **Run tests**: Executes pytest test suite
5. **Update README**: Updates timestamp and ensures README exists
6. **📄 Sync docs**: Syncs all agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

### 🔄 Documentation Sync is Critical
The validation process automatically keeps CLAUDE.md, AGENTS.md, and GEMINI.md synchronized:
- **Uses most recent file** as the source of truth
- **Preserves agent-specific headers** while syncing content
- **Prevents documentation drift** between AI agent platforms
- **Ensures consistency** across all instruction files

### When to Run Validation
- **ALWAYS** after completing ALL file changes for a task
- **ALWAYS** before committing code changes  
- **ALWAYS** before creating pull requests
- **ALWAYS** after adding new features or fixing bugs
- **NEVER SKIP** validation regardless of how small the change

### Validation Requirements
- **CRITICAL**: Formatting and linting must pass (blocks development)
- **CRITICAL**: Documentation sync must pass (prevents agent instruction drift)  
- **Important**: Type checking should pass (warnings acceptable)
- **Important**: Tests should pass (warnings acceptable)
- **Always**: README timestamp update

## Environment Setup

### Required Environment Variables
```bash
# .env file
GITHUB_TOKEN=your_github_token_here  # Optional but recommended
OTEL_EXPORTER_OTLP_ENDPOINT=your_otel_endpoint  # Optional
```

### Dependencies
- **Python 3.13+** (required for modern type features)
- **uv** (recommended for dependency management)
- **GitHub Token** (optional but provides 5000 requests/hour vs 60)

### Installation
```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN

# Verify installation
repo-modules --help
validate-project
```

## Working with Repository Configurations

### Adding New Repository Support

1. **Add to repos.json**:
```json
{
  "new-repo": {
    "repo": "owner/repository",
    "description": "New repository description",
    "versions": ["main", "v1.0.0"],
    "parser_type": "default",
    "fetch_strategy": "filenames_only"
  }
}
```

2. **Create Custom Parser (if needed)**:
```python
class NewRepoParser(BaseParser):
    def parse(self, data: dict[str, Any]) -> str:
        # Custom parsing logic
        return formatted_output
```

3. **Register Parser**:
```python
_parsers = {
    "new_repo_parser": NewRepoParser,
    # ... existing parsers
}
```

4. **Add Tests**:
```python
def test_new_repo_parser():
    # Test functionality
    pass
```

## Output File Patterns

### Standard Naming Conventions
- **Repository modules**: `{slug}_modules_version_{version}.txt`
- **Alias mappings**: `{slug}_alias_mappings_{version}.txt`
- **Historical data**: `{repo}_full_historical_data.txt`

### Example Outputs
```
prebid.js_modules_version_v9.51.0.txt
prebid.server.go_modules_version_v3.8.0.txt
prebid.js_alias_mappings_v9.51.0.txt
prebid_js_full_historical_data.txt
```

## Performance Considerations

### Caching Strategy
- **Version Cache**: `cache/versions/` - Repository version discovery
- **History Cache**: `cache/history/` - Module historical data
- **File-Based**: JSON files for persistence across runs

### Rate Limiting Strategy
- **Conservative Defaults**: Keep safety buffers to prevent exhaustion
- **Adaptive Batching**: Adjust batch sizes based on available quota
- **Cross-Tool Awareness**: Share rate limit status across all tools

### Memory Optimization
- **Streaming**: Process large repositories in chunks
- **Incremental**: Only process new or changed data
- **Cleanup**: Regular cache maintenance and artifact cleanup

## Troubleshooting Guide

### Common Error Patterns

**403 Rate Limit Exceeded**:
- Check GitHub token configuration
- Verify rate limit manager is being used
- Reduce batch sizes or add delays

**404 Not Found**:
- Verify repository name and version are correct
- Check if file paths match actual repository structure
- Ensure branch/tag exists

**No Commits Found**:
- Check file path generation logic
- Verify component type mapping
- Apply case corrections for module names

**Parser Not Found**:
- Verify parser type in configuration
- Check parser registration in factory
- Ensure parser class is properly defined

### Debugging Tools

**Check Rate Limit Status**:
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

**Check Cache Status**:
```bash
build-module-history --repo prebid-js --status
```

**Validate Configuration**:
```bash
repo-modules --list-repos
```

**Run Specific Tests**:
```bash
uv run pytest tests/test_repo_modules/test_github_client.py -v
```

## Important Implementation Notes

### File Path Handling
- **Always use full file paths** as cache keys to prevent module type collisions
- **Apply case corrections** for known problematic module names
- **Validate file existence** before making API calls when possible

### Rate Limiting
- **Use shared rate limit manager** for all GitHub API calls
- **Check safety** before large batch operations
- **Monitor quota usage** and adapt batch sizes accordingly

### Error Handling
- **Graceful degradation** with fallback mechanisms
- **Comprehensive logging** with appropriate levels
- **Clear error messages** with actionable guidance

### Type Safety
- **Full type annotations** for all public APIs
- **mypy compliance** for type checking
- **Generic types** where appropriate for flexibility

## Future Development Guidelines

### Extensibility
- **Configuration-driven** behavior to avoid hardcoding
- **Factory patterns** for easy addition of new components
- **Plugin architecture** for custom parsers and formatters

### Performance
- **Intelligent caching** for expensive operations
- **Batch processing** for API efficiency
- **Incremental updates** to minimize redundant work

### Reliability
- **Comprehensive testing** with high coverage
- **Validation workflows** to ensure code quality
- **Error handling** with graceful degradation

### Observability
- **Structured logging** with loguru
- **OpenTelemetry integration** for tracing
- **Metrics collection** for performance monitoring

---

**Last updated**: 2025-06-28 09:00:00

This documentation provides comprehensive guidance for working with the documentation-toolkit project. Always run `validate-project` after making changes to ensure code quality and consistency.