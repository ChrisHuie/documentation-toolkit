#!/usr/bin/env python3
"""
Standalone CLI tool for building module historical data cache.
Separated from regular module extraction for better performance.
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from ..shared_utilities import global_rate_limit_manager
from .config import get_available_repos
from .module_history import ModuleHistoryTracker

# Initialize environment and logging
load_dotenv()
logger.remove()  # Remove default handler
logger.add(
    sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {message}", level="INFO"
)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the build-history command."""
    parser = argparse.ArgumentParser(
        prog="build-module-history",
        description="Build historical data cache for repository modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build complete historical cache for Prebid.js
  build-module-history --repo prebid-js

  # Build for custom repository
  build-module-history --repo owner/repo-name

  # Incremental update (only process new modules)
  build-module-history --repo prebid-js --incremental

  # Process in smaller batches with longer delays
  build-module-history --repo prebid-js --batch-size 20 --delay 2.0

  # Resume from interruption
  build-module-history --repo prebid-js --resume
""",
    )

    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="Repository name (e.g., 'prebid-js' or 'owner/repo')",
    )

    parser.add_argument(
        "--version",
        type=str,
        default="extract-metadata",
        help="Repository version to analyze (default: extract-metadata for Prebid.js)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of modules to process per batch (default: 20)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between API calls (default: 2.0)",
    )

    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process modules not already in cache",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous interruption",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Custom cache directory (default: cache/history)",
    )

    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="List available preconfigured repositories",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current cache status for repository",
    )

    return parser


def show_repo_list() -> None:
    """Display available repositories."""
    repos = get_available_repos()

    if not repos:
        print("No preconfigured repositories found.")
        return

    print("Available Repositories:")
    print("=" * 50)

    for name, config in repos.items():
        print(f"📦 {name}")
        print(f"   Repository: {config.repo}")
        print(f"   Description: {config.description}")
        print(f"   Parser: {config.parser_type}")
        print()


def show_cache_status(repo_name: str, cache_dir: Path | None = None) -> None:
    """Show current cache status for a repository."""
    try:
        # Resolve repository name
        if "/" not in repo_name:
            repos = get_available_repos()
            if repo_name not in repos:
                print(
                    f"❌ Repository '{repo_name}' not found in available configurations"
                )
                return
            config = repos[repo_name]
            actual_repo = config.repo
        else:
            actual_repo = repo_name

        # Initialize tracker to check cache
        tracker = ModuleHistoryTracker(actual_repo, cache_dir)

        print(f"📊 Cache Status for {actual_repo}")
        print("=" * 50)
        print(f"Cache file: {tracker.cache_file}")

        if tracker.cache_file.exists():
            cached_count = len(tracker._cache)
            file_size = tracker.cache_file.stat().st_size
            modified_time = tracker.cache_file.stat().st_mtime

            print("✅ Cache exists")
            print(f"📈 Modules cached: {cached_count}")
            print(f"💾 File size: {file_size:,} bytes")
            print(f"🕐 Last updated: {time.ctime(modified_time)}")

            if cached_count > 0:
                print("\n📋 Sample cached modules:")
                sample_file_paths = list(tracker._cache.keys())[:5]
                for file_path in sample_file_paths:
                    info = tracker._cache[file_path]
                    date = (
                        info.first_commit_date[:10]
                        if info.first_commit_date
                        else "unknown"
                    )
                    # Show both file path and module name for clarity
                    print(f"   • {info.name} ({file_path}): {date}")

                if len(tracker._cache) > 5:
                    print(f"   ... and {len(tracker._cache) - 5} more")
        else:
            print("❌ No cache found - run build command to create")

    except Exception as e:
        print(f"❌ Error checking cache status: {e}")


def get_current_modules(repo_name: str, version: str) -> tuple[list[str], list[str]]:
    """Get current modules from repository without historical data."""
    try:
        # Resolve repository configuration
        if "/" not in repo_name:
            repos = get_available_repos()
            if repo_name not in repos:
                raise ValueError(f"Repository '{repo_name}' not found")
            config = repos[repo_name]
        else:
            # Create minimal config for custom repo
            from .config import RepoConfig

            config = RepoConfig(
                repo=repo_name,
                description="Custom repository",
                versions=[version],
                parser_type="prebid_js",  # Assume prebid_js for now
            )

        # Use GitHub client to get modules via metadata

        if config.parser_type == "prebid_js" and version in [
            "extract-metadata",
            "master",
        ]:
            # Use metadata approach for Prebid.js
            import requests

            metadata_url = f"https://raw.githubusercontent.com/{config.repo}/{version}/metadata/modules.json"
            response = requests.get(metadata_url, timeout=30)

            if response.status_code == 200:
                metadata = response.json()
                components = metadata.get("components", [])

                # Extract unique module names and types, skip aliases
                modules = []
                component_types = []
                for component in components:
                    component_name = component.get("componentName")
                    component_type = component.get("componentType")
                    alias_of = component.get("aliasOf")

                    if component_name and not alias_of:
                        modules.append(component_name)
                        component_types.append(component_type or "other")

                # Sort both lists by module name
                sorted_data = sorted(zip(modules, component_types, strict=False))
                sorted_modules, sorted_types = (
                    zip(*sorted_data, strict=False) if sorted_data else ([], [])
                )
                return list(sorted_modules), list(sorted_types)

        # Fallback: would need to implement other extraction methods
        logger.warning(f"Metadata extraction not available for {config.parser_type}")
        return [], []

    except Exception as e:
        logger.error(f"Failed to get current modules: {e}")
        return [], []


def build_history(
    repo_name: str,
    version: str = "extract-metadata",
    batch_size: int = 20,
    delay: float = 2.0,
    incremental: bool = False,
    cache_dir: Path | None = None,
) -> None:
    """Build historical data cache for repository modules."""

    # Resolve repository name to actual repo path
    if "/" not in repo_name:
        repos = get_available_repos()
        if repo_name not in repos:
            logger.error(
                f"Repository '{repo_name}' not found in available configurations"
            )
            return
        config = repos[repo_name]
        actual_repo = config.repo
    else:
        actual_repo = repo_name

    print("🏗️  Building Historical Data Cache")
    print("=" * 50)
    print(f"Repository: {actual_repo}")
    print(f"Version: {version}")
    print(f"Batch size: {batch_size}")
    print("Delay: intelligent rate limiting")
    print(f"Incremental: {incremental}")
    print(f"Rate limit status: {global_rate_limit_manager.format_status_summary()}")
    print()

    # Initialize tracker (now uses shared rate limiting)
    tracker = ModuleHistoryTracker(actual_repo, cache_dir)

    # Check if we have enough rate limit quota for the operation
    is_safe, reason = global_rate_limit_manager.check_rate_limit_safety(batch_size)
    if not is_safe:
        print(f"⚠️  {reason}")
        print("💡 Consider using --incremental mode or waiting for rate limit reset")
        return

    # Get current modules with component types
    print("📋 Getting current modules...")
    current_modules, component_types = get_current_modules(repo_name, version)

    if not current_modules:
        logger.error("No modules found - check repository and version")
        return

    print(f"Found {len(current_modules)} total modules")

    # Filter for incremental processing
    if incremental:
        modules_to_process = []
        types_to_process = []
        for i, module in enumerate(current_modules):
            if module not in tracker._cache:
                modules_to_process.append(module)
                types_to_process.append(component_types[i])
        print(f"Incremental mode: {len(modules_to_process)} new modules to process")
    else:
        modules_to_process = current_modules
        types_to_process = component_types
        print(f"Full mode: processing all {len(modules_to_process)} modules")

    if not modules_to_process:
        print("✅ All modules already cached!")
        return

    # Process in batches
    print("\n🚀 Starting batch processing...")
    print(f"Processing {len(modules_to_process)} modules in batches of {batch_size}")

    start_time = time.time()
    processed_count = 0
    success_count = 0

    try:
        for i in range(0, len(modules_to_process), batch_size):
            # Get adaptive batch size based on current rate limit
            adaptive_batch_size = global_rate_limit_manager.get_recommended_batch_size(
                batch_size
            )
            batch = modules_to_process[i : i + adaptive_batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(modules_to_process) + batch_size - 1) // batch_size

            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} modules)")
            print(f"   📊 {global_rate_limit_manager.format_status_summary()}")

            # Process batch with component types
            batch_types = types_to_process[i : i + batch_size]
            batch_results = tracker.get_module_history(
                batch, component_types=batch_types
            )
            batch_success = len(batch_results)

            processed_count += len(batch)
            success_count += batch_success

            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0

            print(f"   ✅ {batch_success}/{len(batch)} successful")
            print(
                f"   📊 Overall: {success_count}/{processed_count} ({rate:.1f} modules/min)"
            )

            # Show ETA
            remaining = len(modules_to_process) - processed_count
            if rate > 0:
                eta_minutes = remaining / rate
                print(f"   ⏱️  ETA: {eta_minutes:.1f} minutes")

            # Break if we're hitting too many rate limits
            if batch_success == 0 and batch_num > 1:
                print("⚠️  Multiple failed batches - likely hitting rate limits")
                print("💡 Try running again later or increase --delay")
                break

    except KeyboardInterrupt:
        print("\n⏸️  Interrupted by user")
        print(f"📊 Progress saved: {success_count} modules cached")
        print("💡 Run with --resume to continue later")

    # Final summary
    elapsed = time.time() - start_time
    print("\n📊 Final Results:")
    print("=" * 30)
    print(f"✅ Successfully processed: {success_count}")
    print(f"⏱️  Total time: {elapsed / 60:.1f} minutes")
    print(f"💾 Cache location: {tracker.cache_file}")

    if success_count > 0:
        print("🎉 Historical data cache updated!")
        print("💡 Use --use-cached-history flag in regular module extraction")


def main() -> None:
    """Main entry point for build-module-history command."""
    parser = create_parser()
    args = parser.parse_args()

    if args.list_repos:
        show_repo_list()
        return

    if args.status:
        show_cache_status(args.repo, args.cache_dir)
        return

    if not args.repo:
        print("❌ Repository name is required")
        parser.print_help()
        return

    # Build historical data cache
    build_history(
        repo_name=args.repo,
        version=args.version,
        batch_size=args.batch_size,
        delay=args.delay,
        incremental=args.incremental,
        cache_dir=args.cache_dir,
    )


if __name__ == "__main__":
    main()
