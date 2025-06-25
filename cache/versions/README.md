# Version Cache

This directory contains cached version information for repositories to minimize GitHub API calls.

## How it works

- **First run**: Fetches all tags and caches first/last versions of each major release
- **Subsequent runs**: Uses cached data and only checks for new major versions
- **Auto-update**: Rebuilds cache when new major versions are detected

## Cache format

Each repository has a JSON file containing:
- Repository name and default branch
- Latest 5 semantic versions
- First and last version of each major release
- Last updated timestamp

## Benefits

- **Shared cache**: All users benefit from cached data
- **Fast performance**: Subsequent runs are lightning fast
- **Minimal API usage**: Reduces GitHub rate limit usage
- **Version control**: Cache changes are tracked in git

## Files

- `prebid_Prebid.js.json` - Prebid.js version cache
- `prebid_prebid-server-java.json` - Prebid Server Java version cache  
- `prebid_prebid-server.json` - Prebid Server Go version cache