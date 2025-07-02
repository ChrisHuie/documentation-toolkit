#!/usr/bin/env python3
"""Test script to debug module history issues."""

from src.module_history.core import ModuleHistoryTracker
from src.module_history.config import HistoryConfigManager
from src.shared_utilities.github_client import GitHubClient

# Initialize components
tracker = ModuleHistoryTracker()
config_manager = HistoryConfigManager()
client = GitHubClient()

# Get config for prebid-js
config = config_manager.get_config("prebid-js")
print(f"Config: {config}")

# Test fetching raw data first
try:
    print("\nFetching raw data...")
    data = client.fetch_repository_data(
        repo_name=config.repo_name,
        version="master",
        directory="modules",
        fetch_strategy=config.fetch_strategy,
    )
    print(f"Data keys: {data.keys()}")
    print(f"Files type: {type(data['files'])}")
    print(f"Number of files: {len(data['files'])}")
    
    # Show first few files
    if isinstance(data['files'], dict):
        files_list = list(data['files'].items())[:5]
        print(f"First few files: {files_list}")
    
except Exception as e:
    print(f"Error fetching raw data: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50 + "\n")

# Test fetching modules
try:
    modules = tracker._get_modules_for_version(config, "master", "analytics_adapters")
    print(f"\nModules fetched: {modules}")
    print(f"Total modules: {sum(len(m) for m in modules.values())}")
except Exception as e:
    print(f"Error fetching modules: {e}")
    import traceback
    traceback.print_exc()