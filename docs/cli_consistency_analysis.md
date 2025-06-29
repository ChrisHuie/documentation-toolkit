# CLI Consistency Analysis

## Current State Analysis

### 1. CLI Framework Usage
- **repo-modules**: Uses argparse
- **module-history**: Uses click with decorators
- **alias-mappings**: Uses click with decorators  
- **supported-mediatypes**: Uses argparse

**Issue**: Inconsistent use of CLI frameworks (argparse vs click)

### 2. Common Flags Across Tools

#### Output Flags
- **repo-modules**: `--output` (file path)
- **module-history**: `-o, --output` (supports both short and long form)
- **alias-mappings**: `--output` (file path)
- **supported-mediatypes**: `--output` (file path)

#### Format Flags
- **repo-modules**: No format flag (hardcoded text output)
- **module-history**: `--format` (table, csv, json)
- **alias-mappings**: No format flag (uses OutputFormatter)
- **supported-mediatypes**: `--format` (table, json, csv, markdown, yaml, html)

#### Version/Repository Flags
- **repo-modules**: `--repo`, `--version`
- **module-history**: `--repo` (defaults to prebid-js)
- **alias-mappings**: `--repo`, `--version`
- **supported-mediatypes**: `--version` (hardcoded to prebid-js)

#### Other Common Patterns
- **List functionality**: `--list-repos` (repo-modules, module-history)
- **Caching**: `--force-refresh`, `--clear-cache` (module-history)
- **Rate limiting**: `--delay`, `--batch-size` (alias-mappings)
- **Filtering**: `--limit` (alias-mappings), `--type` (module-history), `--adapter` (supported-mediatypes)
- **Quiet mode**: `--quiet` (module-history)

### 3. Inconsistencies Found

1. **Short form options**: Only module-history uses `-o` for output, others use `--output` only
2. **Default behaviors**: Some tools default to stdout (table), others generate filenames
3. **Format support**: Varies widely between tools
4. **Repository specification**: Some hardcode repos, others allow flexibility
5. **Rate limiting**: Only alias-mappings exposes rate limit controls
6. **Progress indicators**: Only module-history has quiet mode

## Proposed Modular CLI Architecture

### 1. Shared Base Arguments (all tools should support)
```python
# In shared_utilities/cli_base.py
COMMON_ARGUMENTS = {
    "output": {
        "flags": ["-o", "--output"],
        "help": "Output file path (default: stdout for human-readable formats)",
        "type": "path"
    },
    "format": {
        "flags": ["-f", "--format"],
        "choices": ["table", "json", "csv", "markdown", "yaml", "html"],
        "default": "table",
        "help": "Output format"
    },
    "quiet": {
        "flags": ["-q", "--quiet"],
        "action": "store_true",
        "help": "Suppress progress output"
    },
    "verbose": {
        "flags": ["-v", "--verbose"],
        "action": "store_true", 
        "help": "Enable verbose logging"
    }
}
```

### 2. Repository-Related Arguments (for tools that work with repos)
```python
REPO_ARGUMENTS = {
    "repo": {
        "flags": ["--repo"],
        "help": "Repository (format: owner/repo or predefined key)",
        "required": False  # Tools can override
    },
    "version": {
        "flags": ["--version"],
        "help": "Version/tag/branch to analyze",
        "default": None
    },
    "list_repos": {
        "flags": ["--list-repos"],
        "action": "store_true",
        "help": "List available repositories"
    }
}
```

### 3. Rate Limiting Arguments (for tools making API calls)
```python
RATE_LIMIT_ARGUMENTS = {
    "delay": {
        "flags": ["--delay"],
        "type": "float",
        "default": 2.0,
        "help": "Delay between batches (seconds)"
    },
    "batch_size": {
        "flags": ["--batch-size"],
        "type": "int",
        "default": 20,
        "help": "Number of items per batch"
    },
    "request_delay": {
        "flags": ["--request-delay"],
        "type": "float",
        "default": 0.6,
        "help": "Delay between requests (seconds)"
    }
}
```

### 4. Tool-Specific Extensions

#### supported-mediatypes (Prebid.js specific)
- Keep: `--adapter`, `--summary`, `--show-json`
- Add from common: `-o`, `-f`, `-q`, `-v`
- Consider: `--limit` for testing subsets

#### module-history
- Keep: `--type`, `--major-version`, cache controls
- Already has most common flags

#### alias-mappings  
- Keep: `--directory`, `--mode`, `--start-from`
- Add: `-f/--format` for output flexibility
- Standardize: Use common quiet/verbose instead of custom

#### repo-modules
- Add: `-f/--format` for different output types
- Add: `-o` short form for output
- Add: `--quiet` for progress suppression

## Implementation Plan

### Phase 1: Create Shared CLI Infrastructure
1. Create `shared_utilities/cli_base.py` with:
   - `BaseArgumentParser` class extending argparse/click
   - Common argument definitions
   - Standardized help formatting
   - Consistent default behaviors

### Phase 2: Create Specialized Mixins
1. `RepositoryArgumentsMixin` - for repo-based tools
2. `RateLimitArgumentsMixin` - for API-heavy tools  
3. `CacheArgumentsMixin` - for tools with caching
4. `FilterArgumentsMixin` - for tools with data filtering

### Phase 3: Refactor Tools
1. Start with one tool as proof of concept
2. Ensure backward compatibility
3. Add deprecation warnings for changed flags
4. Update all tools incrementally

### Phase 4: Testing & Documentation
1. Create CLI consistency tests
2. Update all documentation
3. Create migration guide for users

## Benefits

1. **Consistency**: Users learn one set of flags that work everywhere
2. **Modularity**: Easy to add new common functionality
3. **Maintainability**: Changes in one place affect all tools
4. **Extensibility**: Tools can still have specific flags
5. **Testing**: Can test CLI behavior centrally
6. **Documentation**: Can generate CLI docs programmatically

## Migration Strategy

1. **Backward Compatibility**: Support old flags with deprecation warnings
2. **Phased Rollout**: Update tools one at a time
3. **Clear Communication**: Document changes in CHANGELOG
4. **Version Planning**: Major version bump for breaking changes