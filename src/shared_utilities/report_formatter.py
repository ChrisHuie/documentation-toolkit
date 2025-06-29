"""
Generic report formatting utilities for creating consistent reports across tools.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

from .base_output_formatter import BaseOutputFormatter
from .data_normalizer import DataNormalizer


class ReportFormatter(BaseOutputFormatter):
    """
    Generic report formatter that handles common report patterns.

    This formatter provides standard implementations for:
    - Reports with headers and metadata
    - Summary statistics with counts and percentages
    - Item listings with properties
    - Multiple output formats (table, CSV, JSON, Markdown)
    """

    def __init__(self, report_title: str = "Report"):
        """Initialize with report title."""
        super().__init__()
        self.report_title = report_title

    def format(self, data: dict[str, Any], format_type: str = "table", **kwargs) -> str:
        """
        Format data according to the specified format type.

        Normalizes data before formatting.
        """
        # Normalize data if it has summary statistics
        if "summary" in data:
            normalized_data = DataNormalizer.normalize_with_percentages(data)
        else:
            normalized_data = data

        return super().format(normalized_data, format_type, **kwargs)

    def save(
        self,
        data: dict[str, Any],
        output_path: str | Path,
        format_type: str = "json",
        **kwargs,
    ) -> None:
        """
        Save formatted data to a file.

        Normalizes data before saving.
        """
        # Normalize data if it has summary statistics
        if "summary" in data:
            normalized_data = DataNormalizer.normalize_with_percentages(data)
        else:
            normalized_data = data

        super().save(normalized_data, output_path, format_type, **kwargs)

    def _format_table(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as a human-readable table."""
        show_summary = kwargs.get("show_summary", False)
        show_json = kwargs.get("show_json", False)
        item_formatter = kwargs.get("item_formatter", self._default_item_formatter)
        lines = []

        # Header
        lines.extend(self._format_header(data))

        # Summary section if requested
        if show_summary and data.get("summary"):
            lines.extend(self._format_summary(data["summary"]))

        # Items section
        items_key = self._get_items_key(data)
        if items_key and data.get(items_key):
            lines.extend(self._format_items(data[items_key], item_formatter))

        # JSON representation if requested
        if show_json:
            lines.append("")
            lines.append("JSON Representation:")
            lines.append("-" * 40)
            lines.append(self._format_json(data))

        return "\n".join(lines)

    def _format_header(self, data: dict[str, Any]) -> list[str]:
        """Format report header."""
        lines = []
        lines.append(self.report_title)

        # Add metadata fields
        if "version" in data:
            lines.append(f"Version: {data['version']}")
        if "total_adapters" in data:
            lines.append(f"Total Adapters: {data['total_adapters']}")
        if "adapters_with_media_types" in data:
            lines.append(
                f"Adapters with Media Types: {data['adapters_with_media_types']}"
            )

        lines.append("=" * 60)
        lines.append("")
        return lines

    def _format_summary(self, summary: dict[str, Any]) -> list[str]:
        """Format summary statistics."""
        lines = []
        lines.append("Summary Statistics:")
        lines.append("-" * 40)

        # Format by_media_type if present
        if "by_media_type" in summary:
            lines.append("Media Type Usage:")
            for mt, stats in summary["by_media_type"].items():
                formatted = DataNormalizer.get_formatted_percentage(stats)
                lines.append(f"  {mt.capitalize()}: {formatted}")
            lines.append("")

        # Format by_combination if present
        if "by_combination" in summary:
            lines.append("Media Type Combinations:")
            for combo, stats in summary["by_combination"].items():
                formatted = DataNormalizer.get_formatted_percentage(stats)
                lines.append(f"  {combo}: {formatted}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("")
        return lines

    def _get_items_key(self, data: dict[str, Any]) -> str | None:
        """Get the key for items in the data (e.g., 'adapters', 'modules')."""
        # Common keys for items
        for key in ["adapters", "modules", "items", "entries"]:
            if key in data and isinstance(data[key], dict):
                return key
        return None

    def _format_items(self, items: dict[str, Any], item_formatter) -> list[str]:
        """Format items section."""
        lines = []
        lines.append(f"{self._get_items_title()}:")
        lines.append("=" * 60)
        lines.append("")

        for name, item_data in sorted(items.items()):
            lines.append(item_formatter(name, item_data))

        lines.append("")
        lines.append("=" * 60)
        return lines

    def _get_items_title(self) -> str:
        """Get title for items section."""
        return "Items"

    def _default_item_formatter(self, name: str, data: dict[str, Any]) -> str:
        """Default formatter for items."""
        return f"{name}: {data}"

    def _format_csv(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write metadata
        writer.writerow([self.report_title])
        if "version" in data:
            writer.writerow([f"Version: {data['version']}"])
        writer.writerow([f"Generated: {data.get('timestamp', 'N/A')}"])
        writer.writerow([])  # Empty row

        # Write items if present
        items_key = self._get_items_key(data)
        if items_key and data.get(items_key):
            self._write_csv_items(writer, data[items_key])

        # Add summary section if available
        if data.get("summary"):
            self._write_csv_summary(writer, data["summary"])

        return output.getvalue()

    def _write_csv_items(self, writer, items: dict[str, Any]) -> None:
        """Write items to CSV. Override in subclasses for specific formats."""
        # Default implementation - subclasses should override
        writer.writerow(["Name", "Data"])
        for name, item_data in sorted(items.items()):
            writer.writerow([name, str(item_data)])

    def _write_csv_summary(self, writer, summary: dict[str, Any]) -> None:
        """Write summary statistics to CSV."""
        writer.writerow([])  # Empty row
        writer.writerow(["Summary Statistics"])

        if "by_media_type" in summary:
            writer.writerow(["Media Type", "Count", "Percentage"])
            for mt, stats in summary["by_media_type"].items():
                writer.writerow(
                    [mt.capitalize(), stats["count"], f"{stats['percentage']:.1f}%"]
                )

        if "by_combination" in summary:
            writer.writerow([])  # Empty row
            writer.writerow(["Media Type Combinations", "Count", "Percentage"])
            for combo, stats in summary["by_combination"].items():
                writer.writerow([combo, stats["count"], f"{stats['percentage']:.1f}%"])

    def _format_markdown(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as Markdown."""
        lines = []

        # Header
        lines.append(f"# {self.report_title}")
        lines.append("")

        # Metadata
        if "version" in data:
            lines.append(f"**Version**: {data['version']}")
        if "total_adapters" in data:
            lines.append(f"**Total Adapters**: {data['total_adapters']}")
        if "adapters_with_media_types" in data:
            lines.append(
                f"**Adapters with Media Types**: {data['adapters_with_media_types']}"
            )
        lines.append("")

        # Summary statistics
        if data.get("summary"):
            lines.extend(self._format_markdown_summary(data["summary"]))

        # Items
        items_key = self._get_items_key(data)
        if items_key and data.get(items_key):
            lines.extend(self._format_markdown_items(data[items_key]))

        return "\n".join(lines)

    def _format_markdown_summary(self, summary: dict[str, Any]) -> list[str]:
        """Format summary as Markdown."""
        lines = []
        lines.append("## Summary Statistics")
        lines.append("")

        if "by_media_type" in summary:
            lines.append("### Media Type Usage")
            lines.append("")
            lines.append("| Media Type | Count | Percentage |")
            lines.append("|------------|-------|------------|")
            for mt, stats in summary["by_media_type"].items():
                lines.append(
                    f"| {mt.capitalize()} | {stats['count']} | {stats['percentage']:.1f}% |"
                )
            lines.append("")

        if "by_combination" in summary:
            lines.append("### Media Type Combinations")
            lines.append("")
            lines.append("| Combination | Count | Percentage |")
            lines.append("|-------------|-------|------------|")
            for combo, stats in summary["by_combination"].items():
                lines.append(
                    f"| {combo} | {stats['count']} | {stats['percentage']:.1f}% |"
                )
            lines.append("")

        return lines

    def _format_json(self, data: dict[str, Any], **kwargs) -> str:
        """Format as JSON with metadata structure."""
        # Create output with metadata structure
        output = {
            "version": data.get("version"),
            "metadata": {
                "total_adapters": data.get("total_adapters"),
                "adapters_with_media_types": data.get("adapters_with_media_types"),
            },
            "summary": data.get("summary", {}),
        }

        # Add items under the appropriate key
        items_key = self._get_items_key(data)
        if items_key:
            output[items_key] = data.get(items_key, {})

        return json.dumps(output, indent=2, sort_keys=True, default=str)

    def _format_markdown_items(self, items: dict[str, Any]) -> list[str]:
        """Format items as Markdown. Override in subclasses."""
        lines = []
        lines.append("## Items")
        lines.append("")
        for name, data in sorted(items.items()):
            lines.append(f"- **{name}**: {data}")
        return lines
