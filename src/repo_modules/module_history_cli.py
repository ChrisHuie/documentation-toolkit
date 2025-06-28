"""
CLI interface for module history analysis.

Provides command-line access to module history tracking functionality.
"""

import json
import sys
from typing import Any

import click

from ..shared_utilities import get_logger
from .module_history import ModuleHistoryEntry, ModuleHistoryError, ModuleHistoryTracker


class ProgressIndicator:
    """Simple progress indicator for CLI operations."""

    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.current_message = ""

    def update(self, current: int, total: int, message: str):
        """Update progress display."""
        if not self.show_progress:
            return

        if message != self.current_message:
            if self.current_message:  # Not first message
                click.echo()  # New line after previous progress
            click.echo(f"📊 {message}...", nl=False)
            self.current_message = message

        if total > 0:
            percentage = (current / total) * 100
            if current == total:
                click.echo(f" ✅ Complete ({percentage:.0f}%)")
                self.current_message = ""  # Reset for next operation
            else:
                click.echo(f"\r📊 {message}... {percentage:.0f}%", nl=False)


def format_table_output(
    modules: dict[str, Any], module_type_filter: str | None = None
) -> str:
    """Format module history as a human-readable table."""
    if not modules:
        return "No modules found."

    # Filter by module type if specified
    filtered_modules = modules
    if module_type_filter:
        filtered_modules = {
            name: entry
            for name, entry in modules.items()
            if entry.module_type == module_type_filter
        }

    if not filtered_modules:
        return f"No modules found for type: {module_type_filter}"

    # Group by module type for better organization
    by_type: dict[str, list[tuple[str, ModuleHistoryEntry]]] = {}
    for name, entry in filtered_modules.items():
        module_type = entry.module_type
        if module_type not in by_type:
            by_type[module_type] = []
        by_type[module_type].append((name, entry))

    # Sort modules within each type
    for module_list in by_type.values():
        module_list.sort(key=lambda x: x[0])  # Sort by module name

    # Build output
    output = []
    output.append("Prebid.js Module History")
    output.append("=" * 50)
    output.append("")

    for module_type, module_list in sorted(by_type.items()):
        type_display = module_type.replace("_", " ").title()
        output.append(f"📦 {type_display} ({len(module_list)} modules)")
        output.append("-" * 40)

        for module_name, entry in module_list:
            output.append(f"  {module_name}")
            output.append(f"    First Version: v{entry.first_version}")
            output.append(f"    Major Version: {entry.first_major_version}")
            output.append(f"    File Path: {entry.file_path}")
            output.append("")

    # Summary
    total_modules = len(filtered_modules)
    total_types = len(by_type)
    output.append(f"📈 Summary: {total_modules} modules across {total_types} types")

    return "\n".join(output)


def format_csv_output(
    modules: dict[str, Any], module_type_filter: str | None = None
) -> str:
    """Format module history as CSV."""
    if not modules:
        return "module_name,module_type,first_version,first_major_version,file_path\n"

    # Filter by module type if specified
    filtered_modules = modules
    if module_type_filter:
        filtered_modules = {
            name: entry
            for name, entry in modules.items()
            if entry.module_type == module_type_filter
        }

    output = []
    output.append("module_name,module_type,first_version,first_major_version,file_path")

    # Sort by module name for consistent output
    for name, entry in sorted(filtered_modules.items()):
        output.append(
            f"{name},{entry.module_type},{entry.first_version},{entry.first_major_version},{entry.file_path}"
        )

    return "\n".join(output)


def format_json_output(
    modules: dict[str, Any], module_type_filter: str | None = None
) -> str:
    """Format module history as JSON."""
    # Filter by module type if specified
    filtered_modules = modules
    if module_type_filter:
        filtered_modules = {
            name: entry
            for name, entry in modules.items()
            if entry.module_type == module_type_filter
        }

    # Convert to serializable format
    serializable = {}
    for name, entry in filtered_modules.items():
        serializable[name] = {
            "module_name": entry.module_name,
            "module_type": entry.module_type,
            "first_version": entry.first_version,
            "first_major_version": entry.first_major_version,
            "file_path": entry.file_path,
        }

    return json.dumps(serializable, indent=2)


@click.command()
@click.option(
    "--repo",
    default="prebid/Prebid.js",
    help="Repository name (default: prebid/Prebid.js)",
    show_default=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "csv", "json"], case_sensitive=False),
    default="table",
    help="Output format",
    show_default=True,
)
@click.option(
    "--type",
    "module_type_filter",
    type=click.Choice(
        [
            "bid_adapters",
            "analytics_adapters",
            "rtd_modules",
            "identity_modules",
            "other_modules",
        ],
        case_sensitive=False,
    ),
    help="Filter by module type",
)
@click.option(
    "--major-version", type=int, help="Filter by major version (e.g., 2 for v2.x.x)"
)
@click.option(
    "--output", "-o", type=click.File("w"), help="Output file (default: stdout)"
)
@click.option(
    "--force-refresh", is_flag=True, help="Force refresh even if cache exists"
)
@click.option("--clear-cache", is_flag=True, help="Clear cache and exit")
@click.option("--cache-info", is_flag=True, help="Show cache information and exit")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress indicators")
@click.option(
    "--token", envvar="GITHUB_TOKEN", help="GitHub token (or set GITHUB_TOKEN env var)"
)
def main(
    repo: str,
    output_format: str,
    module_type_filter: str | None,
    major_version: int | None,
    output: Any,
    force_refresh: bool,
    clear_cache: bool,
    cache_info: bool,
    quiet: bool,
    token: str | None,
):
    """
    Generate historical reports for Prebid.js modules.

    This tool analyzes when each module was first introduced in Prebid.js
    by examining module files across different major versions.

    Examples:

    \b
        # Show all modules in table format
        module-history

        # Show only bid adapters as CSV
        module-history --type bid_adapters --format csv

        # Show modules introduced in v2.x.x
        module-history --major-version 2

        # Save JSON output to file
        module-history --format json -o module_history.json

        # Force refresh of cached data
        module-history --force-refresh
    """
    logger = get_logger(__name__)

    try:
        tracker = ModuleHistoryTracker(token=token)

        # Handle cache operations
        if clear_cache:
            click.echo("🗑️  Clearing module history cache...")
            tracker.clear_cache(repo)
            click.echo("✅ Cache cleared successfully")
            return

        if cache_info:
            cache_info_data = tracker.get_cache_info(repo)
            if cache_info_data:
                click.echo("📋 Cache Information:")
                click.echo(f"  Repository: {cache_info_data['repo_name']}")
                click.echo(
                    f"  Last Analyzed: {cache_info_data['last_analyzed_version']}"
                )
                click.echo(f"  Module Count: {cache_info_data['module_count']}")
                click.echo(f"  Cache File: {cache_info_data['cache_file']}")
                click.echo(
                    f"  Analysis Date: {cache_info_data['metadata'].get('analysis_date', 'Unknown')}"
                )
            else:
                click.echo("❌ No cache found for repository")
            return

        # Set up progress indicator
        progress = ProgressIndicator(show_progress=not quiet)

        # Get module history
        try:
            if major_version is not None:
                modules = tracker.get_modules_by_version(repo, major_version)
                if not quiet:
                    click.echo(
                        f"📊 Retrieved modules for major version {major_version}"
                    )
            else:
                # Full analysis with progress callback
                history_cache = tracker.analyze_module_history(
                    repo, force_refresh=force_refresh, progress_callback=progress.update
                )
                modules = history_cache.modules

        except ModuleHistoryError as e:
            click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            logger.error("Unexpected error during analysis", error=str(e))
            click.echo(f"❌ Unexpected error: {e}", err=True)
            sys.exit(1)

        # Format output
        try:
            if output_format.lower() == "csv":
                formatted_output = format_csv_output(modules, module_type_filter)
            elif output_format.lower() == "json":
                formatted_output = format_json_output(modules, module_type_filter)
            else:  # table
                formatted_output = format_table_output(modules, module_type_filter)

            # Write output
            if output:
                output.write(formatted_output)
                if not quiet:
                    click.echo(f"✅ Output written to {output.name}")
            else:
                click.echo(formatted_output)

        except Exception as e:
            logger.error("Failed to format or write output", error=str(e))
            click.echo(f"❌ Failed to generate output: {e}", err=True)
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n⏹️  Operation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error in CLI", error=str(e))
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
