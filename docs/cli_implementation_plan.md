# CLI Modular Implementation Plan

## Overview

This document outlines the implementation plan for creating a consistent, modular CLI system across all tools in the documentation-toolkit.

## Goals

1. **Consistency**: All tools use the same flags for common functionality
2. **Modularity**: Shared CLI components reduce duplication
3. **Extensibility**: Easy to add new common features
4. **Backward Compatibility**: Existing scripts continue to work
5. **User Experience**: Predictable behavior across tools

## Implementation Phases

### Phase 1: Infrastructure (Created)
✅ Created `src/shared_utilities/cli_base.py` with:
- Common argument definitions
- Repository-related arguments
- Rate limiting arguments
- Filter arguments
- Cache arguments
- Helper classes for both argparse and click

### Phase 2: Tool Updates (Prioritized by impact)

#### 1. supported-mediatypes (Prebid.js specific)
**Changes needed:**
- [x] Add `-o` short form for `--output`
- [x] Add `-f` short form for `--format`
- [x] Add `-q/--quiet` for progress suppression
- [x] Add `-v/--verbose` for debug logging
- [x] Add `--limit` for testing subsets
- [ ] Update extractor to support limit parameter
- [ ] Use shared CLI base classes

**Notes:** Tool is Prebid.js specific, so no need for --repo flexibility

#### 2. repo-modules (Most divergent)
**Changes needed:**
- [ ] Add `-o` short form for `--output`
- [ ] Add `-f/--format` for output formats (currently only text)
- [ ] Add `-q/--quiet` for progress suppression
- [ ] Add `-v/--verbose` for debug logging
- [ ] Standardize rate limiting flags
- [ ] Use shared CLI base classes

**Notes:** Core tool, needs careful migration

#### 3. alias-mappings (Uses click)
**Changes needed:**
- [ ] Add `-f/--format` for output flexibility
- [ ] Standardize to use common quiet/verbose
- [ ] Consider migrating from click to argparse for consistency
- [ ] Use shared CLI base classes

**Notes:** Already has most features, mainly needs standardization

#### 4. module-history (Most complete)
**Changes needed:**
- [ ] Already has most common flags
- [ ] Consider adding rate limit controls
- [ ] Use shared CLI base classes for consistency

**Notes:** Good example of complete CLI, can serve as reference

### Phase 3: Additional Enhancements

#### A. Smart Defaults
- Output filenames should follow consistent pattern
- Format defaults based on output destination (table for stdout, json for files)
- Quiet mode when piping output

#### B. Help Text Standardization
- Consistent formatting for help messages
- Group related options together
- Show examples in help text

#### C. Error Handling
- Consistent error messages
- Proper exit codes
- Helpful suggestions on errors

### Phase 4: Testing & Documentation

#### Testing Strategy
1. **Unit Tests**: Test individual argument parsing
2. **Integration Tests**: Test CLI behavior end-to-end
3. **Compatibility Tests**: Ensure old flags still work
4. **Consistency Tests**: Verify same flags work same way

#### Documentation Updates
1. Update README with standardized examples
2. Create CLI reference guide
3. Update CLAUDE.md with new patterns
4. Add migration guide for users

## Technical Decisions

### 1. Framework Choice
**Decision**: Keep existing frameworks (argparse/click) but provide adapters
**Rationale**: Minimize disruption while achieving consistency

### 2. Backward Compatibility
**Strategy**: 
- Keep old flags working with deprecation warnings
- Document migration path
- Major version bump when removing old flags

### 3. Repository-Specific Tools
**Approach**: Tools like supported-mediatypes that are repository-specific should:
- Hide --repo flag or make it no-op
- Document their repository focus clearly
- Still use common flags for other functionality

## Example Migration

Here's how supported-mediatypes would be migrated:

```python
# Before
parser = argparse.ArgumentParser(description="...")
parser.add_argument("--output", help="...")
parser.add_argument("--format", choices=[...], help="...")

# After
from shared_utilities.cli_base import create_standard_parser

parser = create_standard_parser(
    description="Extract media types from Prebid.js",
    tool_name="supported-mediatypes",
    include_sets=["common", "filter"],
    exclude_args=["repo"]  # Tool is Prebid.js specific
)

# Add tool-specific arguments
parser.add_argument("--adapter", help="...")
parser.add_argument("--summary", action="store_true", help="...")
```

## Success Metrics

1. **Consistency**: 90% of common flags work identically across tools
2. **Code Reduction**: 30% less CLI-related code per tool
3. **User Satisfaction**: No breaking changes for existing users
4. **Developer Experience**: New tools can be created faster

## Next Steps

1. Get approval on this plan
2. Implement Phase 2 starting with supported-mediatypes
3. Create migration guide
4. Update one tool at a time with testing
5. Document lessons learned

## Open Questions

1. Should we standardize on argparse or support both?
2. How long should deprecation period be?
3. Should we add shell completion support?
4. Do we need a --config file option?