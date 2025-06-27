#!/usr/bin/env python3
"""Test GitHub API pagination for the modules directory."""

import os
import requests
from github import Github

def test_pagination():
    """Test GitHub API pagination to get all files."""
    token = os.environ.get('GITHUB_TOKEN')
    headers = {'Authorization': f'token {token}'} if token else {}
    
    all_files = []
    page = 1
    per_page = 100
    
    while True:
        url = 'https://api.github.com/repos/prebid/Prebid.js/contents/modules'
        params = {'per_page': per_page, 'page': page}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f'Error on page {page}: {response.status_code}')
            if response.status_code == 404:
                print('No more pages')
                break
        
        data = response.json()
        if not data:  # Empty page means we're done
            print(f'Page {page}: Empty response, stopping')
            break
            
        print(f'Page {page}: {len(data)} items')
        all_files.extend(data)
        
        # Check if we got fewer items than requested (indicates last page)
        if len(data) < per_page:
            print(f'Got {len(data)} < {per_page}, this is the last page')
            break
            
        page += 1
        
        # Safety limit
        if page > 50:
            print('Safety limit reached')
            break
    
    print(f'Total files found via direct API: {len(all_files)}')
    
    # Filter for bid adapters
    bid_adapters = []
    for f in all_files:
        if f['type'] == 'file' and f['name'].endswith('BidAdapter.js'):
            adapter_name = f['name'].replace('BidAdapter.js', '')
            bid_adapters.append(adapter_name)
    
    bid_adapters.sort()
    print(f'Total bid adapters: {len(bid_adapters)}')
    
    # Find richaudience and show what comes after
    if 'richaudience' in bid_adapters:
        rich_idx = bid_adapters.index('richaudience')
        after_rich = bid_adapters[rich_idx+1:]
        print(f'Adapters after richaudience: {len(after_rich)}')
        if after_rich:
            print(f'First 10 after richaudience: {after_rich[:10]}')
        print(f'Last 10 overall: {bid_adapters[-10:]}')
    
    # Check for specific missing adapters
    missing = ['rubicon', 'smartadserver', 'unruly', 'yieldmo']
    found = [m for m in missing if m in bid_adapters]
    print(f'Previously missing adapters now found: {found}')
    
    return all_files, bid_adapters

if __name__ == '__main__':
    test_pagination()