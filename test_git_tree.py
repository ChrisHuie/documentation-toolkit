#!/usr/bin/env python3
"""Test GitHub Git Tree API to get all files."""

import os
import requests
from github import Github

def test_git_tree_api():
    """Use Git Tree API to get all files recursively."""
    token = os.environ.get('GITHUB_TOKEN')
    github = Github(token) if token else Github()
    
    try:
        repo = github.get_repo('prebid/Prebid.js')
        
        # Get the current commit SHA
        master_branch = repo.get_branch('master')
        commit_sha = master_branch.commit.sha
        print(f'Using commit SHA: {commit_sha}')
        
        # Get the tree for this commit
        tree = repo.get_git_tree(commit_sha, recursive=True)
        print(f'Total tree elements: {len(tree.tree)}')
        
        # Filter for files in the modules directory
        modules_files = []
        for element in tree.tree:
            if element.path.startswith('modules/') and element.type == 'blob':
                modules_files.append(element.path)
        
        print(f'Files in modules directory: {len(modules_files)}')
        
        # Filter for JS files in root of modules
        root_js_files = []
        for path in modules_files:
            # Remove 'modules/' prefix
            relative_path = path[8:]  # len('modules/') = 8
            
            # Check if it's a root-level JS file (no subdirectories)
            if '/' not in relative_path and relative_path.endswith('.js'):
                root_js_files.append(relative_path)
        
        print(f'JS files in root of modules: {len(root_js_files)}')
        
        # Filter for bid adapters
        bid_adapters = []
        for filename in root_js_files:
            if filename.endswith('BidAdapter.js'):
                adapter_name = filename.replace('BidAdapter.js', '')
                bid_adapters.append(adapter_name)
        
        bid_adapters.sort()
        print(f'Total bid adapters found: {len(bid_adapters)}')
        print(f'First 10: {bid_adapters[:10]}')
        print(f'Last 10: {bid_adapters[-10:]}')
        
        # Find richaudience and show what comes after
        if 'richaudience' in bid_adapters:
            rich_idx = bid_adapters.index('richaudience')
            after_rich = bid_adapters[rich_idx+1:]
            print(f'Adapters after richaudience: {len(after_rich)}')
            if after_rich:
                print(f'First 10 after richaudience: {after_rich[:10]}')
        
        # Check for specific missing adapters
        missing = ['rubicon', 'smartadserver', 'unruly', 'yieldmo']
        found = [m for m in missing if m in bid_adapters]
        print(f'Previously missing adapters now found: {found}')
        
        return bid_adapters
        
    except Exception as e:
        import traceback
        print('Error with Git Tree API:')
        traceback.print_exc()
        return []

if __name__ == '__main__':
    test_git_tree_api()