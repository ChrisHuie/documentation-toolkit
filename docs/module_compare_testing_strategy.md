# Module Compare Testing Strategy

## Current Issues

### 1. Data Structure Mismatch
The tests are using an incorrect mock data structure that doesn't match what the GitHub client actually returns.

**Expected by tests:**
```json
{
  "Bid Adapters": [
    {"name": "file.js", "path": "path/to/file.js"}
  ]
}
```

**Actually returned by GitHub client:**
```json
{
  "repo": "owner/repo",
  "version": "v1.0.0", 
  "paths": {
    "modules": {
      "modules/file1.js": "",
      "modules/file2.js": ""
    }
  },
  "files": [...],
  "metadata": {...}
}
```

### 2. Testing Gaps

1. **No Contract Tests**: No tests verify the contract between GitHub client and comparator
2. **Mock Data Issues**: Mock data doesn't reflect real API responses
3. **Integration Test Gaps**: Integration tests also use incorrect mock data
4. **No End-to-End Tests**: No tests that actually hit the GitHub API (even in a controlled way)
5. **Missing Edge Cases**: 
   - Empty repositories
   - Repositories with no matching files
   - Version resolution failures
   - API rate limiting
   - Network errors
   - Malformed repository configurations

## Proposed Testing Strategy

### 1. Test Utilities Module
Create `tests/test_module_compare/test_utils.py`:
```python
def create_github_response(repo_name, version, paths_data):
    """Create a properly structured GitHub API response."""
    return {
        "repo": repo_name,
        "version": version,
        "paths": paths_data,
        "files": [],
        "metadata": {"commit_sha": "abc123", "total_files": 0}
    }

def create_module_files(path, filenames):
    """Create file structure for a given path."""
    return {f"{path}/{name}": "" for name in filenames}
```

### 2. Fix Unit Tests
Update all unit tests to use the correct data structure:
- Use the test utilities to create proper mock responses
- Test both multi-path and legacy single-directory structures
- Verify the comparator handles the "paths" key correctly

### 3. Contract Tests
Create `tests/test_module_compare/test_contracts.py`:
- Test that GitHub client output matches comparator expectations
- Use schema validation to ensure data structures remain consistent
- Test transformation from GitHub response to internal module structure

### 4. Integration Tests with Fixtures
Create `tests/test_module_compare/fixtures/`:
- Store sample GitHub API responses as JSON files
- Create fixtures for different repository types
- Test with real-world data structures

### 5. End-to-End Tests (Optional)
Create `tests/test_module_compare/test_e2e.py`:
- Mark with `@pytest.mark.e2e` 
- Skip by default, run with `pytest -m e2e`
- Test against a controlled test repository
- Verify complete flow from API call to formatted output

### 6. Error Handling Tests
Enhance error scenario testing:
- API failures (404, 500, rate limiting)
- Malformed responses
- Invalid repository configurations
- Network timeouts

### 7. Regression Tests
Create specific tests for issues we've encountered:
- Directory-to-paths conversion
- Module name extraction for different parser types
- Cross-repository comparison with different structures

## Implementation Priority

1. **Immediate (Critical)**:
   - Fix existing unit tests to use correct data structure
   - Create test utilities module
   - Fix integration tests

2. **Short-term (High)**:
   - Add contract tests
   - Create fixture-based integration tests
   - Add comprehensive error handling tests

3. **Medium-term (Medium)**:
   - Implement end-to-end tests
   - Add performance tests
   - Create property-based tests for edge cases

## Testing Best Practices

1. **Use Factories**: Create factory functions for common test data
2. **Fixture Management**: Store complex test data as fixtures
3. **Clear Test Names**: Use descriptive test names that explain the scenario
4. **Isolated Tests**: Each test should be independent
5. **Mock at Boundaries**: Mock external dependencies (GitHub API) at the boundary
6. **Test the Contract**: Verify data structures between components
7. **Document Assumptions**: Clearly document what each test assumes

## Example Test Structure

```python
class TestModuleComparator:
    """Unit tests for ModuleComparator."""
    
    def test_compare_versions_with_paths_structure(self):
        """Test comparison with proper GitHub API response structure."""
        # Arrange
        source_data = create_github_response(
            "prebid-js", 
            "v9.0.0",
            {"modules": create_module_files("modules", ["a.js", "b.js"])}
        )
        
        # Act
        result = comparator.compare(...)
        
        # Assert
        assert "modules" in result.categories
        
    def test_compare_handles_legacy_structure(self):
        """Test backward compatibility with legacy structure."""
        # Test the fallback behavior
```

## Monitoring and Maintenance

1. **Coverage Targets**: Maintain >90% test coverage
2. **CI Integration**: All tests run on every PR
3. **Performance Benchmarks**: Track test execution time
4. **Regular Reviews**: Review test effectiveness quarterly
5. **Documentation**: Keep test documentation up to date