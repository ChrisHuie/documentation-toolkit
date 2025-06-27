"""
CLI entry point for alias mappings tool
"""

import json
from pathlib import Path

import click

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
    type=click.Choice(["js", "server"]),
    help="Extraction mode: 'js' for JavaScript files, 'server' for YAML files",
    show_default=True,
)
def main(repo: str, version: str, directory: str, limit: int | None, batch_size: int, delay: int, request_delay: float, output: str | None, start_from: int, mode: str) -> None:
    """Find bid adapter files with aliases in a GitHub repository."""
    try:
        finder = AliasFinder()
        
        if mode == "server":
            result = finder.find_server_aliases_from_yaml(
                repo, version, directory, limit, batch_size, delay, request_delay, start_from
            )
        else:
            result = finder.find_adapter_files_with_aliases_batch(
                repo, version, directory, limit, batch_size, delay, request_delay, start_from
            )
        
        if result["file_aliases"]:
            metadata = result["metadata"]
            total_files = metadata["total_files"]
            
            if mode == "server":
                files_with_aliases = metadata["files_with_aliases"]
                files_not_in_version = metadata["files_not_in_version"]
                files_with_empty_aliases = metadata["files_with_empty_aliases"]
                
                # Display results to console
                print(f"\nResults:")
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
                        print(f"  (no alias)")
            else:
                files_with_aliases = metadata["files_with_aliases"]
                files_with_commented_aliases = metadata["files_with_commented_aliases"]
                files_not_in_version = metadata["files_not_in_version"]
                files_with_empty_aliases = metadata["files_with_empty_aliases"]
                
                # Display results to console
                print(f"\nResults:")
                print(f"  Files with aliases: {files_with_aliases}")
                print(f"  Files with commented aliases only: {files_with_commented_aliases}")
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
                        print(f"  (aliases in comments only)")
                    elif not_in_version:
                        print(f"  (not in {version})")
                    else:
                        print(f"  (no aliases)")
            
            # Generate output file if specified
            if output:
                _generate_output_file(result, output, repo, version, mode)
                print(f"\n📄 Output saved to: {output}")
        else:
            if mode == "server":
                print("No YAML files with aliases found.")
            else:
                print("No BidAdapter.js files with aliases found.")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


def _generate_output_file(result: dict, output_path: str, repo: str, version: str, mode: str = "js") -> None:
    """Generate the formatted output file with alphabetical list and JSON structure."""
    
    # Collect all aliases with their source files
    all_aliases = []
    alias_objects = []
    metadata = result["metadata"]
    
    if mode == "server":
        for file_path, file_data in result["file_aliases"].items():
            alias_name = file_data["alias_name"]
            alias_of = file_data["alias_of"]
            if alias_name and alias_of:
                all_aliases.append(alias_name)
                alias_objects.append({
                    "name": alias_name,
                    "aliasOf": alias_of
                })
        
        title = "Prebid Server Alias Mappings"
        files_stat_line = f"# Files not in {version}: {metadata['files_not_in_version']}\n# Files with Empty Aliases: {metadata['files_with_empty_aliases']}"
    else:
        for file_path, file_data in result["file_aliases"].items():
            aliases = file_data["aliases"]
            if aliases:
                # Extract adapter name from file path (remove .js and BidAdapter suffix)
                adapter_name = Path(file_path).stem.replace("BidAdapter", "")
                
                for alias in aliases:
                    all_aliases.append(alias)
                    alias_objects.append({
                        "name": alias,
                        "aliasOf": adapter_name
                    })
        
        title = "Prebid.js Alias Mappings"
        files_stat_line = f"# Files with Commented Aliases: {metadata['files_with_commented_aliases']}\n# Files not in {version}: {metadata['files_not_in_version']}\n# Files with Empty Aliases: {metadata['files_with_empty_aliases']}"
    
    # Sort alphabetically
    all_aliases.sort()
    alias_objects.sort(key=lambda x: x["name"])
    
    # Generate output content
    lines = []
    lines.append(f"# {title}")
    lines.append(f"# Repository: {repo}")
    lines.append(f"# Version: {version}")
    lines.append(f"# Generated: {metadata['commit_sha']}")
    lines.append(f"# Total Files: {metadata['total_files']}")
    lines.append(f"# Files with Aliases: {metadata['files_with_aliases']}")
    lines.append(files_stat_line)
    lines.append(f"# Total Aliases: {len(all_aliases)}")
    lines.append("")
    lines.append("## Alphabetical List of All Aliases")
    lines.append("")
    
    for alias in all_aliases:
        lines.append(alias)
    
    lines.append("")
    lines.append("## JSON Structure")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(alias_objects, indent=2))
    lines.append("```")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == "__main__":
    main()