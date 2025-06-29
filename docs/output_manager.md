# Output Manager Documentation

The Output Manager is a shared utility that provides hierarchical directory management for tool outputs, organizing files by tool, repository, and version.

## Overview

The Output Manager creates and maintains a consistent directory structure for all tool outputs:

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

## Key Features

- **Automatic Directory Creation** - Directories are created as needed when saving files
- **Path Normalization** - Repository owner prefixes and version 'v' prefixes are automatically removed
- **Empty Directory Cleanup** - Remove empty directories after processing to keep structure clean
- **File Discovery** - Find existing outputs by tool, repository, or version
- **Singleton Pattern** - Default manager instance for convenience functions

## Usage

### Basic Usage

```python
from src.shared_utilities import get_output_path, save_output, cleanup_empty_directories

# Get path for output file (creates directories automatically)
output_path = get_output_path(
    tool_name="supported-mediatypes",
    repo_name="prebid/Prebid.js",  # Owner prefix will be removed
    version="v9.51.0",              # 'v' prefix will be removed
    filename="media_types.json"
)
# Result: Path("output/supported-mediatypes/Prebid.js/9.51.0/media_types.json")

# Save content directly
save_output(
    content=json_content,
    tool_name="supported-mediatypes",
    repo_name="prebid/Prebid.js",
    version="v9.51.0",
    filename="media_types.json"
)

# Clean up empty directories for a specific tool
cleanup_empty_directories("supported-mediatypes")

# Clean up all empty directories
cleanup_empty_directories()
```

### Advanced Usage with OutputManager Class

```python
from src.shared_utilities import OutputManager

# Create custom manager with different base directory
manager = OutputManager(base_output_dir="custom_output")

# Get existing outputs for a tool
outputs = manager.get_existing_outputs(
    tool_name="module-history",
    repo_name="Prebid.js",
    version="9.51.0"
)

# Get all outputs for a repository (all versions)
all_versions = manager.get_existing_outputs(
    tool_name="module-history",
    repo_name="Prebid.js"
)

# Get directory structure as nested dictionary
structure = manager.get_output_structure()
# Returns:
# {
#     "module-history": {
#         "Prebid.js": {
#             "9.51.0": ["modules.json", "modules.csv"],
#             "9.50.0": ["modules.json"]
#         }
#     }
# }
```

## Integration with Tools

Tools should use the Output Manager instead of managing their own output directories:

```python
# In your tool's output formatter or main function
from src.shared_utilities import save_output

def save_results(data, format, repo_name, version):
    # Format your data
    if format == "json":
        content = json.dumps(data, indent=2)
        filename = "results.json"
    elif format == "csv":
        content = format_as_csv(data)
        filename = "results.csv"
    
    # Save using Output Manager
    output_path = save_output(
        content=content,
        tool_name="my-tool",
        repo_name=repo_name,
        version=version,
        filename=filename
    )
    
    print(f"Results saved to: {output_path}")
```

## Path Cleaning

The Output Manager automatically cleans paths for consistency:

- **Repository Names**: `"prebid/Prebid.js"` → `"Prebid.js"`
- **Version Strings**: `"v9.51.0"` → `"9.51.0"`

This ensures consistent directory naming regardless of input format.

## Directory Cleanup

Empty directories can accumulate as files are moved or deleted. Use the cleanup function to maintain a clean structure:

```python
# Clean up after your tool completes
removed_count = cleanup_empty_directories("my-tool")
if removed_count > 0:
    print(f"Cleaned up {removed_count} empty directories")
```

## Best Practices

1. **Use Tool Name Consistently** - Use the same tool name (matching your CLI command) for all outputs
2. **Let Output Manager Handle Paths** - Don't construct paths manually
3. **Clean Up When Done** - Call cleanup_empty_directories() after batch operations
4. **Check Existing Outputs** - Use get_existing_outputs() to avoid redundant processing

## Error Handling

The Output Manager handles common errors gracefully:

- Creates parent directories if they don't exist
- Handles permission errors during cleanup (logs warning, continues)
- Returns empty lists/structures when querying non-existent paths

## Testing

The Output Manager has comprehensive unit tests that use mocking to avoid filesystem operations. See `tests/test_shared_utilities/test_output_manager.py` for examples.