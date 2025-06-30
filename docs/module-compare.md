# Module Compare Tool Documentation

## Overview

The `module-compare` tool analyzes differences between module sets, supporting two distinct comparison modes:

1. **Version Comparison**: Compare modules between two versions of the same repository
2. **Repository Comparison**: Compare modules between different repositories

## Architecture

### Core Components

```
src/module_compare/
├── main.py                 # CLI entry point using click
├── comparator.py          # Core comparison logic
├── data_models.py         # Data models for comparison results
└── output_formatter.py    # Extends ReportFormatter for output
```

### Data Models

#### ComparisonMode Enum
- `VERSION_COMPARISON`: Same repository, different versions
- `REPOSITORY_COMPARISON`: Different repositories

#### ChangeType Enum
For version comparisons:
- `ADDED`: Module added in target version
- `REMOVED`: Module removed from source version
- `UNCHANGED`: Module exists in both versions

For repository comparisons:
- `ONLY_IN_SOURCE`: Module exists only in source repository
- `ONLY_IN_TARGET`: Module exists only in target repository  
- `IN_BOTH`: Module exists in both repositories

#### Key Classes

**ModuleInfo**: Represents a module with name, path, category, and repository
- Equality based on name and category (path ignored for cross-repo matching)

**CategoryComparison**: Comparison results for a specific category
- Tracks modules by change type
- Calculates statistics (counts, percentages, net changes)

**ComparisonResult**: Complete comparison result
- Contains category comparisons
- Generates comprehensive statistics
- Supports filtering changes vs unchanged/common

**ComparisonStatistics**: Detailed statistics
- Overall counts and percentages
- Category breakdowns
- Growth rates and change analysis

### Comparison Logic

#### Version Comparison (Same Repository)
1. Fetch modules from both versions
2. Group by category
3. For each category:
   - Added = modules in target but not source
   - Removed = modules in source but not target
   - Unchanged = modules in both

#### Repository Comparison (Different Repositories)
1. Fetch modules from both repositories
2. Group by category
3. Match modules by name within each category
4. For each category:
   - Only in source = unmatched source modules
   - Only in target = unmatched target modules
   - In both = matched modules

## Usage

### Command Line Interface

```bash
# Interactive mode - prompts for selections
module-compare

# Version comparison
module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0
module-compare --from prebid-js:v9.0.0 --to prebid-js:v9.51.0

# Repository comparison  
module-compare --from prebid-js:v9.51.0 --to prebid-server:v3.8.0
module-compare --from prebid-js --to prebid-server-java

# Options
--show-unchanged      # Include unchanged/common modules (default: false)
--format FORMAT      # Output format: table, json, csv, markdown, yaml, html
--output FILE        # Save to file instead of stdout
--quiet             # Suppress progress messages
--list-repos        # List available repositories
```

### Output Formats

All standard formats are supported through the shared ReportFormatter:
- **table**: Human-readable console output (default)
- **json**: Machine-readable JSON
- **csv**: Excel-compatible CSV  
- **markdown**: Documentation-ready Markdown
- **yaml**: YAML configuration format
- **html**: HTML report with styling

## Statistics and Analysis

### Version Comparison Statistics
- Total modules in each version
- Added/removed/unchanged counts
- Net change and growth percentage
- Category-level breakdowns
- Categories ranked by:
  - Most changes (added + removed)
  - Highest growth rate

### Repository Comparison Statistics  
- Total modules in each repository
- Unique and common module counts
- Overlap percentage
- Category distribution analysis
- Repository specialization insights

### Example Statistics Output

```
DETAILED STATISTICS
----------------------------------------
Changes by Category:
Category               Added   Removed    Net    Change
Bid Adapters             20         2     +18    +12.5%
Analytics                 3         0      +3    +25.0%
RTD Modules               2         1      +1     +8.3%

Categories with Most Changes:
1. Bid Adapters: 22 changes
2. Analytics: 3 changes
3. RTD Modules: 3 changes

Categories by Growth Rate:
1. Analytics: +25.0%
2. Bid Adapters: +12.5%
3. RTD Modules: +8.3%
```

## Integration with Shared Infrastructure

### Leverages Shared Utilities
- **GitHubClient**: API interactions with rate limiting
- **RepositoryConfigManager**: Repository configurations
- **ReportFormatter**: Base formatting functionality
- **DataNormalizer**: Consistent data preparation
- **OutputManager**: Hierarchical output directory management
- **Logging & Telemetry**: Structured logging and tracing

### Follows Project Patterns
- Configuration-driven repository access
- Minimal tool-specific code
- Extensible output formatting
- Consistent CLI interface
- Comprehensive error handling

## Testing

The tool includes comprehensive tests covering:
- Data model functionality
- Comparison logic for both modes
- Output formatting
- Edge cases and error conditions

Run tests with:
```bash
pytest tests/test_module_compare/
```

## Future Enhancements

Potential improvements:
- Caching comparison results
- Batch comparisons across multiple versions
- Detailed change tracking (e.g., module renames)
- Export to comparison reports
- Integration with CI/CD pipelines