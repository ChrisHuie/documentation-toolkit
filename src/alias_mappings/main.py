"""
CLI entry point for alias mappings tool
"""

import click

from ..shared_utilities import cleanup_active_tools
from ..shared_utilities.output_formatter import (
    OutputFormatter,
    create_output_metadata_from_result,
    extract_aliases_from_result_data,
)
from ..shared_utilities.telemetry import trace_function, trace_operation
from .alias_finder import AliasFinder


@click.command()
@click.option(
    "--repo",
    default="prebid/Prebid.js",
    help="GitHub repository in format 'owner/repo'",
    show_default=True,
)
@click.option(
    "--version",
    default="master",
    help="Git reference (branch, tag, or commit SHA)",
    show_default=True,
)
@click.option(
    "--directory",
    default="modules",
    help="Directory path within repository to search",
    show_default=True,
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Limit number of files to process (for testing)",
)
@click.option(
    "--batch-size",
    default=20,
    type=int,
    help="Number of files to process per batch",
    show_default=True,
)
@click.option(
    "--delay",
    default=2,
    type=int,
    help="Delay in seconds between batches",
    show_default=True,
)
@click.option(
    "--request-delay",
    default=0.6,
    type=float,
    help="Delay in seconds between individual requests",
    show_default=True,
)
@click.option(
    "--output",
    default=None,
    type=str,
    help="Output file path (e.g., 'prebid.js_alias_mappings.txt')",
)
@click.option(
    "--start-from",
    default=0,
    type=int,
    help="Start processing from file index (for resuming)",
    show_default=True,
)
@click.option(
    "--mode",
    default="js",
    type=click.Choice(["js", "server", "java-server"]),
    help="Extraction mode: 'js' for JavaScript files, 'server' for YAML files (Go), 'java-server' for YAML files (Java)",
    show_default=True,
)
@trace_function("alias_mappings_main", include_args=True)
def main(
    repo: str,
    version: str,
    directory: str,
    limit: int | None,
    batch_size: int,
    delay: int,
    request_delay: float,
    output: str | None,
    start_from: int,
    mode: str,
) -> None:
    """Find bid adapter files with aliases in a GitHub repository."""
    try:
        finder = AliasFinder()

        if mode == "server":
            result = finder.find_server_aliases_from_yaml(
                repo,
                version,
                directory,
                limit,
                batch_size,
                delay,
                request_delay,
                start_from,
            )
        elif mode == "java-server":
            result = finder.find_java_server_aliases_from_yaml(
                repo,
                version,
                directory,
                limit,
                batch_size,
                delay,
                request_delay,
                start_from,
            )
        else:
            result = finder.find_adapter_files_with_aliases_batch(
                repo,
                version,
                directory,
                limit,
                batch_size,
                delay,
                request_delay,
                start_from,
            )

        if result["file_aliases"]:
            metadata = result["metadata"]
            total_files = metadata["total_files"]

            if mode == "server":
                files_with_aliases = metadata["files_with_aliases"]
                files_not_in_version = metadata["files_not_in_version"]
                files_with_empty_aliases = metadata["files_with_empty_aliases"]

                # Display results to console
                print("\nResults:")
                print(f"  Files with aliases: {files_with_aliases}")
                print(f"  Files not in {version}: {files_not_in_version}")
                print(f"  Files with empty aliases: {files_with_empty_aliases}")
                print(f"  Total files: {total_files}")
                print("=" * 60)

                for file_path in sorted(result["file_aliases"].keys()):
                    file_data = result["file_aliases"][file_path]
                    alias_name = file_data["alias_name"]
                    alias_of = file_data["alias_of"]
                    not_in_version = file_data.get("not_in_version", False)
                    print(f"\n{file_path}")
                    if alias_name and alias_of:
                        print(f"  • {alias_name} -> {alias_of}")
                    elif not_in_version:
                        print(f"  (not in {version})")
                    else:
                        print("  (no alias)")
            elif mode == "java-server":
                files_with_aliases = metadata["files_with_aliases"]
                files_not_in_version = metadata["files_not_in_version"]
                files_with_empty_aliases = metadata["files_with_empty_aliases"]

                # Display results to console
                print("\nResults:")
                print(f"  Files with aliases: {files_with_aliases}")
                print(f"  Files not in {version}: {files_not_in_version}")
                print(f"  Files with empty aliases: {files_with_empty_aliases}")
                print(f"  Total files: {total_files}")
                print("=" * 60)

                for file_path in sorted(result["file_aliases"].keys()):
                    file_data = result["file_aliases"][file_path]
                    aliases = file_data["aliases"]
                    bidder_name = file_data["bidder_name"]
                    not_in_version = file_data.get("not_in_version", False)
                    print(f"\n{file_path}")
                    if aliases and bidder_name:
                        for alias in sorted(aliases):
                            print(f"  • {alias} -> {bidder_name}")
                    elif not_in_version:
                        print(f"  (not in {version})")
                    else:
                        print("  (no aliases)")
            else:
                files_with_aliases = metadata["files_with_aliases"]
                files_with_commented_aliases = metadata["files_with_commented_aliases"]
                files_not_in_version = metadata["files_not_in_version"]
                files_with_empty_aliases = metadata["files_with_empty_aliases"]

                # Display results to console
                print("\nResults:")
                print(f"  Files with aliases: {files_with_aliases}")
                print(
                    f"  Files with commented aliases only: {files_with_commented_aliases}"
                )
                print(f"  Files not in {version}: {files_not_in_version}")
                print(f"  Files with empty aliases: {files_with_empty_aliases}")
                print(f"  Total files: {total_files}")
                print("=" * 60)

                for file_path in sorted(result["file_aliases"].keys()):
                    file_data = result["file_aliases"][file_path]
                    aliases = file_data["aliases"]
                    not_in_version = file_data.get("not_in_version", False)
                    print(f"\n{file_path}")
                    if aliases:
                        for alias in sorted(aliases):
                            print(f"  • {alias}")
                    elif file_data["commented_only"]:
                        print("  (aliases in comments only)")
                    elif not_in_version:
                        print(f"  (not in {version})")
                    else:
                        print("  (no aliases)")

            # Generate output file if specified
            if output:
                _generate_output_file_with_shared_utilities(result, output, mode)
                print(f"\n📄 Output saved to: {output}")
        else:
            if mode == "server":
                print("No YAML files with aliases found.")
            else:
                print("No BidAdapter.js files with aliases found.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
    finally:
        # Clean up empty directories for tools used in this session
        cleanup_active_tools()


def _generate_output_file_with_shared_utilities(
    result: dict, output_path: str, mode: str = "js"
) -> None:
    """Generate output file using shared utilities."""
    with trace_operation(
        "generate_output_file", {"mode": mode, "output_path": output_path}
    ):
        # Extract aliases and metadata using shared utilities
        aliases = extract_aliases_from_result_data(result, mode)
        metadata = create_output_metadata_from_result(result)

        # Create formatter and generate output
        formatter = OutputFormatter()
        formatter.generate_alias_output_file(output_path, aliases, metadata, mode)


if __name__ == "__main__":
    main()
