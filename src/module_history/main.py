"""
Main CLI entry point for module history analysis.
"""

import click
from dotenv import load_dotenv

from ..shared_utilities import cleanup_active_tools, get_logger
from ..shared_utilities.telemetry import trace_function
from .core import ModuleHistoryError, ModuleHistoryTracker
from .output_formatter import ModuleHistoryFormatter

# Load environment variables from .env file
load_dotenv()


class ProgressIndicator:
    """Simple progress indicator for CLI operations."""

    def __init__(self, quiet: bool = False):
        """Initialize progress indicator.

        Args:
            quiet: If True, suppress progress output
        """
        self.quiet = quiet

    def update(self, current: int, total: int, message: str) -> None:
        """Update progress display."""
        if self.quiet:
            return

        if total > 0:
            percentage = (current / total) * 100
            click.echo(f"[{percentage:6.1f}%] {message}", err=True)
        else:
            click.echo(f"[  ---  ] {message}", err=True)


@click.command()
@click.option(
    "--repo",
    default="prebid-js",
    help="Repository ID or owner/repo format",
    show_default=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "csv", "json"]),
    default="table",
    help="Output format",
    show_default=True,
)
@click.option(
    "--type",
    "module_type",
    type=click.Choice(
        [
            "bid_adapters",
            "analytics_adapters",
            "rtd_modules",
            "identity_modules",
            "other_modules",
        ]
    ),
    help="Filter by module type",
)
@click.option(
    "--version",
    help="Version to analyze (e.g., v9.51.0, master). Default: master",
)
@click.option(
    "--major-version",
    type=int,
    help="Filter by major version (e.g., 2 for v2.x.x)",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.Path(),
    help="Output file (default: stdout)",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Force refresh even if cache exists",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear cache and exit",
)
@click.option(
    "--cache-info",
    is_flag=True,
    help="Show cache information and exit",
)
@click.option(
    "--list-repos",
    is_flag=True,
    help="List available repositories and exit",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress progress indicators",
)
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub token (or set GITHUB_TOKEN env var)",
)
@trace_function("module_history_main", include_args=True)
def main(
    repo: str,
    output_format: str,
    module_type: str | None,
    version: str | None,
    major_version: int | None,
    output_file: str | None,
    force_refresh: bool,
    clear_cache: bool,
    cache_info: bool,
    list_repos: bool,
    quiet: bool,
    token: str | None,
) -> None:
    """
    Generate historical reports for repository modules.

    Configuration-driven tool that analyzes when modules were first introduced
    across different repositories by examining module files across major versions.

    Examples:

        # Show all modules in table format (default: Prebid.js)
        module-history

        # Show only bid adapters as CSV
        module-history --type bid_adapters --format csv

        # Show modules introduced in v2.x.x
        module-history --major-version 2

        # Save JSON output to file
        module-history --format json -o module_history.json

        # Force refresh of cached data
        module-history --force-refresh

        # Use different repository
        module-history --repo prebid-server

        # List available repositories
        module-history --list-repos
    """
    logger = get_logger(__name__)

    try:
        tracker = ModuleHistoryTracker(token=token)
        formatter = ModuleHistoryFormatter()

        # Handle utility commands
        if list_repos:
            repos = tracker.get_available_repositories()
            if repos:
                click.echo("Available repositories:")
                for repo_id in sorted(repos):
                    click.echo(f"  {repo_id}")
            else:
                click.echo("No repositories configured.")
            return

        # Determine repository name for cache operations
        repo_name = repo
        if "/" not in repo:
            # It's a repo ID, need to get the actual repo name
            config = tracker.config_manager.get_config(repo)
            if config:
                repo_name = config.repo_name
            else:
                click.echo(
                    f"Error: Repository '{repo}' not found in configuration.", err=True
                )
                available_repos = tracker.get_available_repositories()
                if available_repos:
                    click.echo("Available repositories:", err=True)
                    for repo_id in sorted(available_repos):
                        click.echo(f"  {repo_id}", err=True)
                raise click.Abort()

        if clear_cache:
            tracker.clear_cache(repo_name)
            click.echo(f"Cache cleared for {repo_name}")
            return

        if cache_info:
            info = tracker.get_cache_info(repo_name)
            if info is None:
                click.echo("No cache information available.")
            else:
                output = formatter.format_cache_info(info)
                click.echo(output)
            return

        # Perform analysis
        progress = ProgressIndicator(quiet=quiet)

        try:
            result = tracker.analyze_module_history(
                repo_id=repo,
                version=version,
                module_type=module_type,
                force_refresh=force_refresh,
                progress_callback=progress.update,
            )
        except ModuleHistoryError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort() from e

        # Generate output
        if output_format == "table":
            output = formatter.format_table_output(result, module_type, major_version)
        elif output_format == "csv":
            output = formatter.format_csv_output(result, module_type, major_version)
        elif output_format == "json":
            output = formatter.format_json_output(result, module_type, major_version)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

        # Output to file or stdout
        if output_file:
            formatter.save_to_file(
                result, output_file, output_format, module_type, major_version
            )
            click.echo(f"Output saved to {output_file}")
        else:
            click.echo(output)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
    finally:
        # Clean up empty directories for tools used in this session
        cleanup_active_tools()


if __name__ == "__main__":
    main()
