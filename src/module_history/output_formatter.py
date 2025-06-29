"""
Output formatting for module history results.
"""

import csv
import json
from io import StringIO
from typing import Any

from ..shared_utilities.output_formatter import OutputFormatter as BaseOutputFormatter
from .data_models import ModuleHistoryEntry, ModuleHistoryResult


class ModuleHistoryFormatter:
    """Specialized formatter for module history output."""

    def __init__(self):
        """Initialize formatter."""
        self.base_formatter = BaseOutputFormatter()

    def format_table_output(
        self,
        result: ModuleHistoryResult,
        module_type: str | None = None,
        major_version: int | None = None,
    ) -> str:
        """Format result as table for console display."""
        lines = []

        # Filter modules based on criteria
        if module_type:
            if module_type not in result.modules_by_type:
                return f"No modules found for type: {module_type}"
            modules_to_show = {module_type: result.modules_by_type[module_type]}
        elif major_version is not None:
            if major_version not in result.modules_by_version:
                return f"No modules found for major version: {major_version}"
            # Group by type for display
            modules_to_show = {}
            for entry in result.modules_by_version[major_version]:
                if entry.module_type not in modules_to_show:
                    modules_to_show[entry.module_type] = []
                modules_to_show[entry.module_type].append(entry)
        else:
            modules_to_show = result.modules_by_type

        # Generate header
        lines.append(f"📦 Module History: {result.repo_name}")
        lines.append(f"Total Modules: {result.total_modules}")
        if module_type:
            lines.append(f"Filtered by Type: {module_type}")
        if major_version is not None:
            lines.append(f"Filtered by Major Version: {major_version}")
        lines.append("=" * 60)
        lines.append("")

        # Generate sections by type
        for category, entries in modules_to_show.items():
            lines.append(
                f"📦 {category.replace('_', ' ').title()} ({len(entries)} modules)"
            )
            lines.append("-" * 40)

            for entry in entries:
                lines.append(f"  {entry.module_name}")
                lines.append(f"    First Version: v{entry.first_version}")
                lines.append(f"    Major Version: {entry.first_major_version}")
                lines.append(f"    File Path: {entry.file_path}")
                if entry.first_commit_date:
                    lines.append(f"    First Commit: {entry.first_commit_date}")
                lines.append("")

        return "\n".join(lines)

    def format_csv_output(
        self,
        result: ModuleHistoryResult,
        module_type: str | None = None,
        major_version: int | None = None,
    ) -> str:
        """Format result as CSV."""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "module_name",
                "module_type",
                "first_version",
                "first_major_version",
                "file_path",
                "first_commit_date",
                "first_commit_sha",
            ]
        )

        # Get modules to export
        modules_to_export = self._get_filtered_modules(
            result, module_type, major_version
        )

        # Write data rows
        for entry in modules_to_export:
            writer.writerow(
                [
                    entry.module_name,
                    entry.module_type,
                    entry.first_version,
                    entry.first_major_version,
                    entry.file_path,
                    entry.first_commit_date or "",
                    entry.first_commit_sha or "",
                ]
            )

        return output.getvalue()

    def format_json_output(
        self,
        result: ModuleHistoryResult,
        module_type: str | None = None,
        major_version: int | None = None,
    ) -> str:
        """Format result as JSON."""
        modules_to_export = self._get_filtered_modules(
            result, module_type, major_version
        )

        # Convert to dictionaries
        modules_data = []
        for entry in modules_to_export:
            module_dict = {
                "module_name": entry.module_name,
                "module_type": entry.module_type,
                "first_version": entry.first_version,
                "first_major_version": entry.first_major_version,
                "file_path": entry.file_path,
            }

            if entry.first_commit_date:
                module_dict["first_commit_date"] = entry.first_commit_date
            if entry.first_commit_sha:
                module_dict["first_commit_sha"] = entry.first_commit_sha

            modules_data.append(module_dict)

        # Create full structure
        output_data = {
            "repository": result.repo_name,
            "total_modules": len(modules_data),
            "metadata": result.metadata,
            "modules": modules_data,
        }

        if module_type:
            output_data["filter"] = {"module_type": module_type}
        if major_version is not None:
            output_data["filter"] = {"major_version": major_version}

        return json.dumps(output_data, indent=2)

    def _get_filtered_modules(
        self,
        result: ModuleHistoryResult,
        module_type: str | None = None,
        major_version: int | None = None,
    ) -> list[ModuleHistoryEntry]:
        """Get filtered list of modules based on criteria."""
        if module_type:
            return result.modules_by_type.get(module_type, [])
        elif major_version is not None:
            return result.modules_by_version.get(major_version, [])
        else:
            # Return all modules, flattened and sorted
            all_modules = []
            for entries in result.modules_by_type.values():
                all_modules.extend(entries)
            return sorted(all_modules, key=lambda e: e.module_name)

    def save_to_file(
        self,
        result: ModuleHistoryResult,
        output_path: str,
        format_type: str = "json",
        module_type: str | None = None,
        major_version: int | None = None,
    ) -> None:
        """Save formatted output to file."""
        if format_type == "csv":
            content = self.format_csv_output(result, module_type, major_version)
        elif format_type == "json":
            content = self.format_json_output(result, module_type, major_version)
        elif format_type == "table":
            content = self.format_table_output(result, module_type, major_version)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def format_cache_info(self, cache_info: dict[str, Any]) -> str:
        """Format cache information for display."""
        if not cache_info:
            return "No cache information available."

        lines = [
            "Cache Information:",
            f"  Repository: {cache_info.get('repo_name', 'Unknown')}",
            f"  Cache File: {cache_info.get('cache_file', 'Unknown')}",
            f"  Last Analyzed Version: {cache_info.get('last_analyzed_version', 'Unknown')}",
            f"  Module Count: {cache_info.get('module_count', 0)}",
        ]

        metadata = cache_info.get("metadata", {})
        if metadata:
            lines.append("  Metadata:")
            for key, value in metadata.items():
                lines.append(f"    {key}: {value}")

        return "\n".join(lines)
