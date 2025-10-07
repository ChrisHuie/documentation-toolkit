#!/usr/bin/env python3
"""
Fetch media types for the 110 specific missing adapters and append to CSV.
"""
import sys
import csv
import re
import datetime
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.shared_utilities.github_client import GitHubClient

# The exact 110 missing adapters we identified earlier
MISSING_ADAPTERS = [
    'ringieraxelspringer', 'rise', 'risemediatech', 'rixengine', 'robustApps', 'robusta',
    'rocketlab', 'rtbhouse', 'rtbsape', 'rubicon', 'rumble', 'scattered', 'screencore',
    'seedingAlliance', 'seedtag', 'setupad', 'sevio', 'sharethrough', 'shinez', 'shinezRtb',
    'showheroes-bs', 'silvermob', 'silverpush', 'slimcut', 'smaato', 'smartadserver',
    'smarthub', 'smartico', 'smartx', 'smartyads', 'smartytech', 'smilewanted', 'smoot',
    'snigel', 'sonarads', 'sonobi', 'sovrn', 'sparteo', 'ssmas', 'sspBC', 'ssp_geniee',
    'stackadapt', 'startio', 'stn', 'stroeerCore', 'stv', 'sublime', 'suim', 'taboola',
    'tadvertising', 'tagoras', 'talkads', 'tapnative', 'tappx', 'targetVideo', 'teads',
    'teal', 'temedya', 'theAdx', 'themoneytizer', 'tpmn', 'trafficgate', 'trion',
    'triplelift', 'truereach', 'ttd', 'twistDigital', 'ucfunnel', 'underdogmedia',
    'undertone', 'unicorn', 'uniquest', 'unruly', 'valuad', 'vdoai', 'ventes', 'viant',
    'vibrantmedia', 'vidazoo', 'videobyte', 'videoheroes', 'videonow', 'videoreach',
    'vidoomy', 'viewdeosDX', 'viously', 'viqeo', 'visiblemeasures', 'vistars', 'visx',
    'vlyby', 'vox', 'vrtcal', 'vuukle', 'waardex', 'welect', 'widespace', 'winr', 'wipes',
    'xe', 'yahooAds', 'yandex', 'yieldlab', 'yieldlift', 'yieldlove', 'yieldmo',
    'yieldone', 'zeta_global', 'zeta_global_ssp', 'zmaticoo'
]

print(f"Fetching media types for {len(MISSING_ADAPTERS)} missing adapters...\n")

# Initialize
client = GitHubClient()

# Check rate limit first
print("Checking GitHub API rate limit...")
rate_limit = client.github.get_rate_limit()
remaining = rate_limit.core.remaining
reset_time = rate_limit.core.reset
now = datetime.datetime.now(datetime.timezone.utc)
minutes_until_reset = (reset_time - now).total_seconds() / 60

print(f"Rate limit: {remaining} remaining")

if remaining < 20:  # Need at least 20 requests (tree + ~110 blobs)
    print(f"⚠️  WARNING: Only {remaining} API calls remaining!")
    print(f"Rate limit resets in {minutes_until_reset:.1f} minutes at {reset_time}")
    if remaining == 0:
        print(f"\n❌ Cannot proceed - rate limit exhausted.")
        print(f"Please wait {minutes_until_reset:.1f} minutes and try again.")
        sys.exit(1)
    else:
        response = input(f"\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

repo = client.github.get_repo("prebid/Prebid.js")

# Get tree to get file SHAs
print("\nFetching repository tree...")
ref = repo.get_git_ref("tags/10.12.0")
commit = repo.get_git_commit(ref.object.sha)
tree = repo.get_git_tree(commit.tree.sha, recursive=True)

# Build SHA map for our missing adapters
adapter_shas = {}
for element in tree.tree:
    if element.path.startswith("modules/") and element.path.endswith("BidAdapter.js"):
        filename = element.path.split("/")[-1]
        adapter_name = filename.replace("BidAdapter.js", "")
        if adapter_name in MISSING_ADAPTERS:
            adapter_shas[adapter_name] = {
                'sha': element.sha,
                'path': element.path
            }

print(f"Found {len(adapter_shas)} adapter files in tree\n")

# Fetch and process each missing adapter
new_rows = []
count = 0
total = len(MISSING_ADAPTERS)

for adapter_name in MISSING_ADAPTERS:
    count += 1
    print(f"[{count}/{total}] Processing {adapter_name}...", end=' ')

    if adapter_name not in adapter_shas:
        print(f"✗ NOT FOUND in tree")
        continue

    try:
        # Use blob API to get content
        blob = repo.get_git_blob(adapter_shas[adapter_name]['sha'])
        # Decode base64 content
        import base64
        code = base64.b64decode(blob.content).decode('utf-8')

        # Extract media types
        media_types = set()

        # Pattern 1: supportedMediaTypes array
        if re.search(r'supportedMediaTypes.*BANNER', code, re.DOTALL):
            media_types.add("banner")
        if re.search(r'supportedMediaTypes.*VIDEO', code, re.DOTALL):
            media_types.add("video")
        if re.search(r'supportedMediaTypes.*NATIVE', code, re.DOTALL):
            media_types.add("native")
        if re.search(r'supportedMediaTypes.*AUDIO', code, re.DOTALL):
            media_types.add("audio")

        # Pattern 2: Import from mediaTypes
        import_match = re.search(r"import\s*\{([^}]+)\}\s*from\s*['\"](?:\.\./)*src/mediaTypes", code)
        if import_match:
            imports = import_match.group(1)
            if "BANNER" in imports:
                media_types.add("banner")
            if "VIDEO" in imports:
                media_types.add("video")
            if "NATIVE" in imports:
                media_types.add("native")
            if "AUDIO" in imports:
                media_types.add("audio")

        # Pattern 3: Direct references
        if re.search(r"mediaTypes\s*\.\s*banner", code, re.IGNORECASE):
            media_types.add("banner")
        if re.search(r"mediaTypes\s*\.\s*video", code, re.IGNORECASE):
            media_types.add("video")
        if re.search(r"mediaTypes\s*\.\s*native", code, re.IGNORECASE):
            media_types.add("native")
        if re.search(r"mediaTypes\s*\.\s*audio", code, re.IGNORECASE):
            media_types.add("audio")

        # Default to banner if nothing found but has width/height
        if not media_types and re.search(r"\b(width|height|sizes)\b", code, re.IGNORECASE):
            media_types.add("banner")

        has_banner = "Yes" if "banner" in media_types else "No"
        has_video = "Yes" if "video" in media_types else "No"
        has_native = "Yes" if "native" in media_types else "No"
        has_audio = "Yes" if "audio" in media_types else "No"

        new_rows.append({
            'Adapter Name': adapter_name,
            'Banner': has_banner,
            'Video': has_video,
            'Native': has_native,
            'Audio': has_audio,
            'File Path': adapter_shas[adapter_name]['path']
        })

        types_str = ", ".join(sorted(media_types)) if media_types else "none"
        print(f"✓ [{types_str}]")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        new_rows.append({
            'Adapter Name': adapter_name,
            'Banner': 'No',
            'Video': 'No',
            'Native': 'No',
            'Audio': 'No',
            'File Path': f'modules/{adapter_name}BidAdapter.js'
        })

# Read existing CSV
csv_file = 'output/supported-mediatypes/Prebid.js/10.12.0/prebid.js_supported_mediatypes_10.12.0.csv'
print(f"\nReading existing CSV: {csv_file}")
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    existing_rows = list(reader)

print(f"Existing adapters: {len(existing_rows)}")

# Combine and sort
all_rows = existing_rows + new_rows
all_rows.sort(key=lambda x: x['Adapter Name'])

# Write back
print(f"Writing updated CSV...")
with open(csv_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Adapter Name', 'Banner', 'Video', 'Native', 'Audio', 'File Path'])
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\n✅ DONE! Updated CSV with {len(all_rows)} total adapters")
print(f"   - Existing: {len(existing_rows)}")
print(f"   - Added: {len(new_rows)}")
