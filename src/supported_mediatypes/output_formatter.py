"""
Media type specific output formatting
"""

from typing import Any

from ..shared_utilities.data_normalizer import DataNormalizer
from ..shared_utilities.report_formatter import ReportFormatter


class MediaTypeOutputFormatter(ReportFormatter):
    """Formatter specifically for media type reports."""

    def __init__(self):
        """Initialize with media type specific title."""
        super().__init__(report_title="Prebid.js Supported Media Types Report")

    def _get_items_title(self) -> str:
        """Override to provide media type specific title."""
        return "Adapters and Supported Media Types"

    def _default_item_formatter(self, name: str, data: dict[str, Any]) -> str:
        """Format adapter with media types."""
        media_types = data.get("mediaTypes", [])
        media_types_str = DataNormalizer.get_media_types_display(media_types, "array")
        # Use ANSI bold for adapter name
        return f"\033[1m{name}\033[0m: {media_types_str}"

    def _write_csv_items(self, writer, items: dict[str, Any]) -> None:
        """Write adapter data to CSV with media type columns."""
        # Write headers
        writer.writerow(
            [
                "Adapter Name",
                "Banner",
                "Video",
                "Native",
                "File Path",
            ]
        )

        # Write adapter data
        for adapter_name, adapter_data in sorted(items.items()):
            media_types = adapter_data.get("mediaTypes", [])

            # Create boolean columns for each media type
            has_banner = "Yes" if "banner" in media_types else "No"
            has_video = "Yes" if "video" in media_types else "No"
            has_native = "Yes" if "native" in media_types else "No"

            writer.writerow(
                [
                    adapter_name,
                    has_banner,
                    has_video,
                    has_native,
                    adapter_data.get("file", ""),
                ]
            )

    def _format_markdown_items(self, items: dict[str, Any]) -> list[str]:
        """Format adapters as Markdown table."""
        lines = []
        lines.append("## Adapter Details")
        lines.append("")
        lines.append("| Adapter | Media Types | File |")
        lines.append("|---------|-------------|------|")

        for adapter_name, adapter_data in sorted(items.items()):
            media_types = adapter_data.get("mediaTypes", [])
            media_types_str = DataNormalizer.get_media_types_display(media_types, "csv")
            if not media_types_str:
                media_types_str = "_none_"
            file_name = adapter_data.get("file", "").split("/")[-1]
            lines.append(f"| {adapter_name} | {media_types_str} | {file_name} |")

        return lines

    # Legacy methods for backward compatibility
    def format_table(self, data: dict[str, Any], show_summary: bool = False) -> str:
        """Legacy method for backward compatibility."""
        return self.format(data, "table", show_summary=show_summary)

    def format_json(self, data: dict[str, Any]) -> str:
        """Legacy method for backward compatibility."""
        return self.format(data, "json")

    def format_csv(self, data: dict[str, Any]) -> str:
        """Legacy method for backward compatibility."""
        return self.format(data, "csv")
