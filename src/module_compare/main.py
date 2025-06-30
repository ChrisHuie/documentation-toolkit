"""CLI entry point for module comparison tool."""

import sys

import click

from src.shared_utilities import cleanup_active_tools, get_logger, get_output_path
from src.shared_utilities.filename_generator import generate_comparison_filename
from src.shared_utilities.github_client import GitHubClient
from src.shared_utilities.repository_config import RepositoryConfigManager

from .comparator import ModuleComparator
from .output_formatter import ModuleCompareOutputFormatter

logger = get_logger(__name__)


def parse_repo_version(spec: str) -> tuple[str, str]:
    """Parse a repo:version specification.

    Args:
        spec: String in format "repo:version" or just "repo"

    Returns:
        tuple of (repo, version)
    """
    if ":" in spec:
        repo, version = spec.split(":", 1)
        return repo, version
    else:
        return spec, "latest"


@click.command()
@click.option(
    "--from",
    "source_spec",
    help="Source repository and version (e.g., 'prebid-js:v9.0.0' or just 'prebid-js')",
)
@click.option(
    "--to",
    "target_spec",
    help="Target repository and version (e.g., 'prebid-js:v9.51.0' or 'prebid-server:v3.8.0')",
)
@click.option(
    "--repo",
    help="Repository to compare versions (alternative to --from/--to for same repo)",
)
@click.option(
    "--from-version",
    help="Source version (use with --repo)",
)
@click.option(
    "--to-version",
    help="Target version (use with --repo)",
)
@click.option(
    "-o",
    "--output",
    help="Custom output file path (default: auto-generated filename)",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["table", "json", "csv", "markdown", "yaml", "html", "all"]),
    default="table",
    help="Output format (default: table, 'all' generates all formats)",
)
@click.option(
    "--show-unchanged",
    is_flag=True,
    help="Include unchanged/common modules in output (default: changes only)",
)
@click.option(
    "--cumulative/--no-cumulative",
    default=None,
    help="Track all module changes across intermediate versions (default: True for same repo, False for cross-repo)",
)
@click.option(
    "--list-repos",
    is_flag=True,
    help="List available repositories",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress progress messages",
)
@click.option(
    "--stdout",
    is_flag=True,
    help="Print to stdout instead of saving to file",
)
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub personal access token (or set GITHUB_TOKEN env var)",
)
def main(
    source_spec: str | None,
    target_spec: str | None,
    repo: str | None,
    from_version: str | None,
    to_version: str | None,
    output: str | None,
    format: str,
    show_unchanged: bool,
    cumulative: bool | None,
    list_repos: bool,
    quiet: bool,
    stdout: bool,
    token: str | None,
) -> None:
    """Compare modules between different versions or repositories.

    This tool supports two comparison modes:

    1. Version comparison (same repository):
       Shows modules added/removed between versions

       Examples:
       module-compare --repo prebid-js --from-version v9.0.0 --to-version v9.51.0
       module-compare --from prebid-js:v9.0.0 --to prebid-js:v9.51.0

    2. Repository comparison (different repositories):
       Shows modules unique to each repository

       Examples:
       module-compare --from prebid-js:v9.51.0 --to prebid-server:v3.8.0
       module-compare --from prebid-js --to prebid-server-java

    By default, only changes are shown. Use --show-unchanged to see all modules.
    """
    try:
        # Initialize configuration manager
        config_manager = RepositoryConfigManager()

        # Handle --list-repos
        if list_repos:
            repos = config_manager.list_repositories()
            click.echo("Available repositories:")
            for repo_name in sorted(repos):
                config = config_manager.get_config(repo_name)
                click.echo(f"  {repo_name}: {config['description']}")
            return

        # Parse repository and version specifications
        if repo and from_version and to_version:
            # Using --repo with version flags
            source_repo = repo
            source_version = from_version
            target_repo = repo
            target_version = to_version
        elif source_spec and target_spec:
            # Using --from and --to
            source_repo, source_version = parse_repo_version(source_spec)
            target_repo, target_version = parse_repo_version(target_spec)
        else:
            # Interactive mode - show menu
            repos = config_manager.list_repositories()

            click.echo("Select source repository:")
            for i, repo_name in enumerate(sorted(repos), 1):
                config = config_manager.get_config(repo_name)
                click.echo(f"  {i}. {repo_name}: {config['description']}")

            choice = click.prompt("Enter number", type=int)
            if choice < 1 or choice > len(repos):
                click.echo("Invalid selection", err=True)
                sys.exit(1)
            source_repo = sorted(repos)[choice - 1]
            source_version = click.prompt(
                "Enter source version (or 'latest')", default="latest"
            )

            click.echo("\nSelect target repository:")
            for i, repo_name in enumerate(sorted(repos), 1):
                config = config_manager.get_config(repo_name)
                click.echo(f"  {i}. {repo_name}: {config['description']}")

            choice = click.prompt("Enter number", type=int)
            if choice < 1 or choice > len(repos):
                click.echo("Invalid selection", err=True)
                sys.exit(1)
            target_repo = sorted(repos)[choice - 1]
            target_version = click.prompt(
                "Enter target version (or 'latest')", default="latest"
            )

        # Validate repositories
        if not config_manager.is_configured(source_repo):
            click.echo(f"Unknown repository: {source_repo}", err=True)
            click.echo("Use --list-repos to see available repositories", err=True)
            sys.exit(1)

        if not config_manager.is_configured(target_repo):
            click.echo(f"Unknown repository: {target_repo}", err=True)
            click.echo("Use --list-repos to see available repositories", err=True)
            sys.exit(1)

        # Initialize GitHub client
        github_client = GitHubClient(token)

        # Determine cumulative default based on comparison type
        is_same_repo = source_repo == target_repo
        use_cumulative = cumulative if cumulative is not None else is_same_repo

        # Initialize comparator
        comparator = ModuleComparator(github_client, config_manager)

        # Define progress callback
        def progress_callback(message: str) -> None:
            if not quiet:
                click.echo(message)

        # Perform comparison
        if not quiet:
            if source_repo == target_repo:
                mode_str = " (cumulative)" if use_cumulative else " (direct)"
                click.echo(
                    f"Comparing {source_repo}: {source_version} → {target_version}{mode_str}"
                )
            else:
                click.echo(
                    f"Comparing {source_repo} @ {source_version} vs {target_repo} @ {target_version}"
                )

        result = comparator.compare(
            source_repo,
            source_version,
            target_repo,
            target_version,
            cumulative=use_cumulative,
            progress_callback=progress_callback,
        )

        # Handle stdout flag - print to console instead of file
        if stdout:
            # Format output for stdout
            formatter = ModuleCompareOutputFormatter()
            formatted_output = formatter.format_output(
                result,
                format if format != "all" else "table",
                show_unchanged=show_unchanged,
            )
            click.echo(formatted_output)

            # Print summary statistics if not quiet and format is not table
            if not quiet and format != "table":
                stats = result.get_statistics()
                click.echo("\n" + "-" * 40)

                if result.comparison_mode.value == "version":
                    click.echo(
                        f"Total changes: {stats.total_added + stats.total_removed}"
                    )
                    click.echo(f"Net change: {stats.net_change:+d} modules")
                else:
                    click.echo(f"Common modules: {stats.total_in_both}")
                    click.echo(f"Unique to {source_repo}: {stats.total_only_in_source}")
                    click.echo(f"Unique to {target_repo}: {stats.total_only_in_target}")
            return

        # Handle "all" format - generate all supported formats
        if format == "all":
            formats_to_generate = ["table", "json", "csv", "markdown", "yaml", "html"]
        else:
            formats_to_generate = [format]

        # Get repository configs for filename generation
        config_manager = RepositoryConfigManager()
        source_config = config_manager.get_config(source_repo)
        target_config = (
            config_manager.get_config(target_repo)
            if target_repo != source_repo
            else source_config
        )

        # Get full repo names from configs
        source_repo_full = source_config.get("repo", source_repo)
        target_repo_full = (
            target_config.get("repo", target_repo)
            if target_repo != source_repo
            else None
        )

        # Get custom slugs if available
        source_slug = source_config.get("output_filename_slug")
        target_slug = (
            target_config.get("output_filename_slug")
            if target_repo != source_repo
            else None
        )

        # Generate outputs for each format
        formatter = ModuleCompareOutputFormatter()
        output_paths = []

        for fmt in formats_to_generate:
            # Format output
            formatted_output = formatter.format_output(
                result, fmt, show_unchanged=show_unchanged
            )

            # Determine extension
            extension = fmt if fmt != "table" else "txt"

            if output:
                # User provided custom filename/path
                import os

                if os.path.dirname(output):
                    # User provided a path with directories - use as-is
                    if len(formats_to_generate) == 1:
                        output_path = output
                    else:
                        # Multiple formats - append format to base filename
                        base, ext = (
                            output.rsplit(".", 1) if "." in output else (output, "")
                        )
                        output_path = f"{base}.{extension}"

                    # Ensure directory exists
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                else:
                    # User provided just a filename - use with standard directory structure
                    if len(formats_to_generate) == 1:
                        filename = output
                    else:
                        # Multiple formats - append format to base filename
                        base, ext = (
                            output.rsplit(".", 1) if "." in output else (output, "")
                        )
                        filename = f"{base}.{extension}"

                    output_path = str(
                        get_output_path(
                            tool_name="module-compare",
                            repo_name=source_repo,
                            version=source_version,
                            filename=filename,
                        )
                    )
            else:
                # Generate standard filename and path
                filename = generate_comparison_filename(
                    source_repo=source_repo_full,
                    source_version=source_version,
                    target_repo=(
                        target_repo_full if target_repo != source_repo else None
                    ),
                    target_version=(
                        target_version if target_repo != source_repo else target_version
                    ),
                    custom_source_slug=source_slug,
                    custom_target_slug=target_slug,
                    extension=extension,
                )

                output_path = str(
                    get_output_path(
                        tool_name="module-compare",
                        repo_name=source_repo,
                        version=source_version,
                        filename=filename,
                    )
                )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(formatted_output)

            output_paths.append(output_path)

        # Show output paths
        if not quiet:
            if len(output_paths) == 1:
                click.echo(f"\nOutput saved to: {output_paths[0]}")
            else:
                click.echo("\nOutputs saved to:")
                for path in output_paths:
                    click.echo(f"  - {path}")

        # Print summary statistics if not quiet
        if not quiet and format != "table":
            stats = result.get_statistics()
            click.echo("\n" + "-" * 40)

            if result.comparison_mode.value == "version":
                click.echo(f"Total changes: {stats.total_added + stats.total_removed}")
                click.echo(f"Net change: {stats.net_change:+d} modules")
            else:
                click.echo(f"Common modules: {stats.total_in_both}")
                click.echo(f"Unique to {source_repo}: {stats.total_only_in_source}")
                click.echo(f"Unique to {target_repo}: {stats.total_only_in_target}")

    except click.Abort:
        sys.exit(130)  # User interrupted
    except Exception as e:
        logger.error(f"Error during comparison: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Clean up empty directories for tools used in this session
        cleanup_active_tools()


if __name__ == "__main__":
    main()
