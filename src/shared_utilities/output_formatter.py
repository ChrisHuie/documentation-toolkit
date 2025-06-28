"""
Shared output formatting utilities for consistent output generation across tools
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AliasMapping:
    """Data class for alias mappings"""

    name: str
    alias_of: str


@dataclass
class OutputMetadata:
    """Data class for output metadata"""

    repository: str
    version: str
    commit_sha: str
    total_files: int
    files_with_aliases: int
    files_with_commented_aliases: int = 0
    files_not_in_version: int = 0
    files_with_empty_aliases: int = 0
    total_aliases: int = 0


class OutputFormatter:
    """Formatter for generating consistent output files across tools"""

    def generate_alias_output_file(
        self,
        output_path: str,
        aliases: list[AliasMapping],
        metadata: OutputMetadata,
        mode: str = "js",
    ) -> None:
        """
        Generate formatted output file with alias mappings and metadata.

        Args:
            output_path: Path where the output file should be written
            aliases: List of alias mappings
            metadata: Metadata about the processing run
            mode: Processing mode ("js", "server", "java-server")
        """
        # Sort aliases alphabetically
        sorted_aliases = sorted(aliases, key=lambda x: x.name)
        alias_names = [alias.name for alias in sorted_aliases]
        alias_objects = [
            {"name": alias.name, "aliasOf": alias.alias_of} for alias in sorted_aliases
        ]

        # Generate title based on mode
        titles = {
            "js": "Prebid.js Alias Mappings",
            "server": "Prebid Server Alias Mappings",
            "java-server": "Prebid Server Java Alias Mappings",
        }
        title = titles.get(mode, "Alias Mappings")

        # Generate statistics lines based on mode
        if mode == "js":
            stats_line = (
                f"# Files with Commented Aliases: {metadata.files_with_commented_aliases}\n"
                f"# Files not in {metadata.version}: {metadata.files_not_in_version}\n"
                f"# Files with Empty Aliases: {metadata.files_with_empty_aliases}"
            )
        else:
            stats_line = (
                f"# Files not in {metadata.version}: {metadata.files_not_in_version}\n"
                f"# Files with Empty Aliases: {metadata.files_with_empty_aliases}"
            )

        # Generate output content
        lines = [
            f"# {title}",
            f"# Repository: {metadata.repository}",
            f"# Version: {metadata.version}",
            f"# Generated: {metadata.commit_sha}",
            f"# Total Files: {metadata.total_files}",
            f"# Files with Aliases: {metadata.files_with_aliases}",
            stats_line,
            f"# Total Aliases: {len(alias_names)}",
            "",
            "## Alphabetical List of All Aliases",
            "",
        ]

        # Add alias names
        lines.extend(alias_names)

        # Add JSON structure
        lines.extend(
            [
                "",
                "## JSON Structure",
                "",
                "```json",
                json.dumps(alias_objects, indent=2),
                "```",
            ]
        )

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def generate_modules_output_file(
        self, output_path: str, modules_data: dict[str, Any], metadata: OutputMetadata
    ) -> None:
        """
        Generate formatted output file for module listings.

        Args:
            output_path: Path where the output file should be written
            modules_data: Dictionary of module data organized by category
            metadata: Metadata about the processing run
        """
        lines = [
            "# Repository Modules",
            f"# Repository: {metadata.repository}",
            f"# Version: {metadata.version}",
            f"# Generated: {metadata.commit_sha}",
            f"# Total Files: {metadata.total_files}",
            f"# Generated on: {datetime.now().isoformat()}",
            "",
        ]

        # Add modules organized by category
        for category, items in modules_data.items():
            lines.extend([f"## {category}", ""])

            if isinstance(items, list):
                for item in sorted(items):
                    lines.append(f"- {item}")
            elif isinstance(items, dict):
                for item_name, item_data in sorted(items.items()):
                    if isinstance(item_data, str):
                        lines.append(f"- {item_name}: {item_data}")
                    else:
                        lines.append(f"- {item_name}")

            lines.append("")

        # Add JSON structure
        lines.extend(
            [
                "## JSON Structure",
                "",
                "```json",
                json.dumps(modules_data, indent=2),
                "```",
            ]
        )

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def format_console_output(self, data: dict[str, Any], mode: str = "js") -> str:
        """
        Format data for console output display.

        Args:
            data: Data to format
            mode: Processing mode for context

        Returns:
            Formatted string for console display
        """
        lines = []
        metadata = data.get("metadata", {})

        # Add summary statistics
        lines.append("\nResults:")
        lines.append(f"  Files with aliases: {metadata.get('files_with_aliases', 0)}")

        if mode == "js":
            lines.append(
                f"  Files with commented aliases only: {metadata.get('files_with_commented_aliases', 0)}"
            )

        lines.append(
            f"  Files not in version: {metadata.get('files_not_in_version', 0)}"
        )
        lines.append(
            f"  Files with empty aliases: {metadata.get('files_with_empty_aliases', 0)}"
        )
        lines.append(f"  Total files: {metadata.get('total_files', 0)}")
        lines.append("=" * 60)

        return "\n".join(lines)


def extract_aliases_from_result_data(
    result_data: dict[str, Any], mode: str = "js"
) -> list[AliasMapping]:
    """
    Extract alias mappings from result data based on mode.

    Args:
        result_data: Raw result data from alias finder
        mode: Processing mode ("js", "server", "java-server")

    Returns:
        List of AliasMapping objects
    """
    aliases = []

    if mode == "server":
        for _file_path, file_data in result_data["file_aliases"].items():
            alias_name = file_data.get("alias_name")
            alias_of = file_data.get("alias_of")
            if alias_name and alias_of:
                aliases.append(AliasMapping(name=alias_name, alias_of=alias_of))

    elif mode == "java-server":
        for _file_path, file_data in result_data["file_aliases"].items():
            file_aliases = file_data.get("aliases", [])
            bidder_name = file_data.get("bidder_name")
            if file_aliases and bidder_name:
                for alias in file_aliases:
                    aliases.append(AliasMapping(name=alias, alias_of=bidder_name))

    else:  # js mode
        for file_path, file_data in result_data["file_aliases"].items():
            file_aliases = file_data.get("aliases", [])
            if file_aliases:
                # Extract adapter name from file path
                adapter_name = Path(file_path).stem.replace("BidAdapter", "")
                for alias in file_aliases:
                    aliases.append(AliasMapping(name=alias, alias_of=adapter_name))

    return aliases


def create_output_metadata_from_result(result_data: dict[str, Any]) -> OutputMetadata:
    """
    Create OutputMetadata from result data.

    Args:
        result_data: Raw result data from processing

    Returns:
        OutputMetadata object
    """
    metadata = result_data.get("metadata", {})

    return OutputMetadata(
        repository=result_data.get("repo", ""),
        version=result_data.get("version", ""),
        commit_sha=metadata.get("commit_sha", ""),
        total_files=metadata.get("total_files", 0),
        files_with_aliases=metadata.get("files_with_aliases", 0),
        files_with_commented_aliases=metadata.get("files_with_commented_aliases", 0),
        files_not_in_version=metadata.get("files_not_in_version", 0),
        files_with_empty_aliases=metadata.get("files_with_empty_aliases", 0),
    )
