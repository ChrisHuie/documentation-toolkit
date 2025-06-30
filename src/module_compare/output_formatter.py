"""Output formatting for module comparison results."""

import csv
import io
import json
from typing import Any

from src.shared_utilities.base_output_formatter import BaseOutputFormatter

from .data_models import (
    ComparisonMode,
    ComparisonResult,
    ComparisonStatistics,
    CumulativeComparisonResult,
)


class ModuleCompareOutputFormatter(BaseOutputFormatter):
    """Formatter for module comparison output."""

    def __init__(self):
        """Initialize the formatter."""
        super().__init__()

    def format_output(
        self, result: ComparisonResult, format_type: str, show_unchanged: bool = False
    ) -> str:
        """Format the comparison result for output.

        Args:
            result: The comparison result to format
            format_type: The output format type
            show_unchanged: Whether to include unchanged/common modules

        Returns:
            Formatted string output
        """
        data = self.prepare_data(result, show_unchanged)
        return self.format(data, format_type)

    def prepare_data(
        self, result: ComparisonResult, show_unchanged: bool = False
    ) -> dict[str, Any]:
        """Prepare comparison data for formatting.

        Args:
            result: The comparison result
            show_unchanged: Whether to include unchanged/common modules

        Returns:
            Dictionary with prepared data for formatting
        """
        # Handle cumulative comparison results differently
        if isinstance(result, CumulativeComparisonResult):
            return self._prepare_cumulative_data(result)

        stats = result.get_statistics()

        # Build header based on comparison mode
        if result.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            header = f"Module Comparison: {result.source_repo} ({result.source_version} → {result.target_version})"
        else:
            header = f"Module Comparison: {result.source_repo} vs {result.target_repo}"

        # Build metadata
        metadata = {
            "Source": f"{result.source_repo} @ {result.source_version}",
            "Target": f"{result.target_repo} @ {result.target_version}",
            "Comparison Type": result.comparison_mode.value.title(),
        }

        # Build summary based on comparison mode
        summary = self._build_summary(stats)

        # Build items (changes only by default)
        items = self._build_items(result, stats, show_unchanged)

        # Add statistics section
        statistics = self._build_statistics(stats)

        return {
            "header": header,
            "metadata": metadata,
            "summary": summary,
            "items": items,
            "statistics": statistics,
        }

    def _build_summary(self, stats: ComparisonStatistics) -> dict[str, Any]:
        """Build summary statistics."""
        summary = {
            "source_total": {"value": stats.source_total, "percentage": None},
            "target_total": {"value": stats.target_total, "percentage": None},
            "categories": {"value": stats.categories_count, "percentage": None},
        }

        if stats.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            summary.update(
                {
                    "added": {"value": stats.total_added, "percentage": None},
                    "removed": {"value": stats.total_removed, "percentage": None},
                    "net_change": {"value": stats.net_change, "percentage": None},
                }
            )
        else:
            summary.update(
                {
                    "only_in_source": {
                        "value": stats.total_only_in_source,
                        "percentage": None,
                    },
                    "only_in_target": {
                        "value": stats.total_only_in_target,
                        "percentage": None,
                    },
                    "in_both": {"value": stats.total_in_both, "percentage": None},
                }
            )

        return summary

    def _build_items(
        self,
        result: ComparisonResult,
        stats: ComparisonStatistics,
        show_unchanged: bool,
    ) -> list[dict[str, Any]]:
        """Build item list for output."""
        items = []

        if result.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            # Version comparison items
            for cat_name, category in result.categories.items():
                if category.added:
                    items.append(
                        {
                            "category": f"{cat_name} - Added",
                            "modules": [mod.name for mod in category.added],
                            "count": len(category.added),
                        }
                    )

                if category.removed:
                    items.append(
                        {
                            "category": f"{cat_name} - Removed",
                            "modules": [mod.name for mod in category.removed],
                            "count": len(category.removed),
                        }
                    )

                if show_unchanged and category.unchanged:
                    items.append(
                        {
                            "category": f"{cat_name} - Unchanged",
                            "modules": [mod.name for mod in category.unchanged],
                            "count": len(category.unchanged),
                        }
                    )
        else:
            # Repository comparison items
            for cat_name, category in result.categories.items():
                if category.only_in_source:
                    items.append(
                        {
                            "category": f"{cat_name} - Only in {result.source_repo}",
                            "modules": [mod.name for mod in category.only_in_source],
                            "count": len(category.only_in_source),
                        }
                    )

                if category.only_in_target:
                    items.append(
                        {
                            "category": f"{cat_name} - Only in {result.target_repo}",
                            "modules": [mod.name for mod in category.only_in_target],
                            "count": len(category.only_in_target),
                        }
                    )

                if show_unchanged and category.in_both:
                    items.append(
                        {
                            "category": f"{cat_name} - In Both",
                            "modules": [mod.name for mod in category.in_both],
                            "count": len(category.in_both),
                        }
                    )

        return items

    def _build_statistics(self, stats: ComparisonStatistics) -> dict[str, Any]:
        """Build detailed statistics section."""
        statistics: dict[str, Any] = {
            "overall": {
                "source_total": stats.source_total,
                "target_total": stats.target_total,
                "categories": stats.categories_count,
            },
            "by_category": [],
        }

        if stats.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            statistics["overall"].update(
                {
                    "total_changes": stats.total_added + stats.total_removed,
                    "net_change": stats.net_change,
                }
            )

            # Add category statistics
            for cat_stat in stats.category_stats:
                statistics["by_category"].append(
                    {
                        "category": cat_stat["category"],
                        "added": cat_stat["added"],
                        "removed": cat_stat["removed"],
                        "net": cat_stat["net_change"],
                    }
                )

            # Add top changes
            statistics["top_changes"] = [
                {"category": cat, "changes": changes}
                for cat, changes in stats.categories_with_most_changes[:5]
            ]

        else:
            statistics["overall"].update(
                {
                    "unique_modules": stats.total_only_in_source
                    + stats.total_only_in_target,
                    "common_modules": stats.total_in_both,
                }
            )

            # Add category statistics
            for cat_stat in stats.category_stats:
                statistics["by_category"].append(
                    {
                        "category": cat_stat["category"],
                        "only_in_source": cat_stat["only_in_source"],
                        "only_in_target": cat_stat["only_in_target"],
                        "in_both": cat_stat["in_both"],
                    }
                )

            # Add unique categories
            statistics["unique_categories"] = {
                "source_only": stats.unique_categories_source,
                "target_only": stats.unique_categories_target,
                "common": stats.common_categories,
            }

        return statistics

    def _prepare_cumulative_data(
        self, result: CumulativeComparisonResult
    ) -> dict[str, Any]:
        """Prepare cumulative comparison data for formatting."""
        header = f"Cumulative Module Comparison: {result.source_repo} ({result.source_version} → {result.target_version})"

        metadata = {
            "Repository": result.source_repo,
            "From Version": result.source_version,
            "To Version": result.target_version,
            "Comparison Type": "Cumulative",
            "Versions Analyzed": len(result.versions_analyzed),
        }

        # Calculate summary statistics
        all_changes = result.all_added_modules
        total_added = len(all_changes)
        permanently_added = len(result.permanently_added_modules)
        removed = len(result.removed_modules)
        transient = len(result.transient_modules)

        summary = {
            "total_changes": {"value": total_added, "percentage": None},
            "permanently_added": {"value": permanently_added, "percentage": None},
            "removed": {"value": removed, "percentage": None},
            "transient": {"value": transient, "percentage": None},
        }

        # Build items for each category
        items = []

        for category, changes in result.cumulative_changes.items():
            if not changes:
                continue

            # Group by status
            added_and_present = [
                c for c in changes if c.is_present_in_target and not c.was_removed
            ]
            added_and_removed = [c for c in changes if c.was_removed]

            if added_and_present:
                items.append(
                    {
                        "category": f"{category} - Added (still present)",
                        "modules": [
                            f"{c.module.name} (added in {c.added_in_version})"
                            for c in sorted(
                                added_and_present, key=lambda x: x.module.name
                            )
                        ],
                        "count": len(added_and_present),
                    }
                )

            if added_and_removed:
                items.append(
                    {
                        "category": f"{category} - Added then removed",
                        "modules": [
                            f"{c.module.name} (added: {c.added_in_version}, removed: {c.removed_in_version})"
                            for c in sorted(
                                added_and_removed, key=lambda x: x.module.name
                            )
                        ],
                        "count": len(added_and_removed),
                    }
                )

        # Build statistics
        statistics: dict[str, Any] = {
            "overall": {
                "total_modules_added": total_added,
                "still_present": permanently_added,
                "removed": removed,
                "transient": transient,
            },
            "versions_analyzed": result.versions_analyzed,
            "by_category": [],
        }

        # Category breakdown
        for category, changes in result.cumulative_changes.items():
            if changes:
                cat_stat = {
                    "category": category,
                    "total_added": len(changes),
                    "still_present": len(
                        [c for c in changes if c.is_present_in_target]
                    ),
                    "removed": len([c for c in changes if c.was_removed]),
                }
                statistics["by_category"].append(cat_stat)

        return {
            "header": header,
            "metadata": metadata,
            "summary": summary,
            "items": items,
            "statistics": statistics,
        }

    def _format_table(self, data: dict[str, Any], **kwargs) -> str:
        """Format comparison as a table."""
        lines = []

        # Header
        lines.append(data["header"])
        lines.append("=" * len(data["header"]))
        lines.append("")

        # Metadata
        for key, value in data["metadata"].items():
            lines.append(f"{key}: {value}")
        lines.append("")

        # Summary statistics
        lines.append("SUMMARY")
        lines.append("-" * 40)
        for key, value in data["summary"].items():
            label = key.replace("_", " ").title()
            # Handle nested value structure
            if isinstance(value, dict) and "value" in value:
                lines.append(f"{label}: {value['value']}")
            else:
                lines.append(f"{label}: {value}")
        lines.append("")

        # Detailed statistics
        stats = data.get("statistics", {})
        if stats:
            lines.append("DETAILED STATISTICS")
            lines.append("-" * 40)

            # Category breakdown
            if stats.get("by_category"):
                lines.append("\nChanges by Category:")

                if data["metadata"]["Comparison Type"] == "Version":
                    # Version comparison table
                    lines.append(
                        f"{'Category':<30} {'Added':>8} {'Removed':>8} {'Net':>8}"
                    )
                    lines.append("-" * 56)
                    for cat in stats["by_category"]:
                        lines.append(
                            f"{cat['category']:<30} {cat['added']:>8} {cat['removed']:>8} "
                            f"{cat['net']:>8}"
                        )
                elif data["metadata"]["Comparison Type"] == "Cumulative":
                    # Cumulative comparison table
                    lines.append(
                        f"{'Category':<30} {'Total Added':>12} {'Still Present':>14} {'Removed':>8}"
                    )
                    lines.append("-" * 66)
                    for cat in stats["by_category"]:
                        lines.append(
                            f"{cat['category']:<30} {cat['total_added']:>12} "
                            f"{cat['still_present']:>14} {cat['removed']:>8}"
                        )
                else:
                    # Repository comparison table
                    lines.append(
                        f"{'Category':<30} {'Source Only':>12} {'Target Only':>12} {'Both':>8}"
                    )
                    lines.append("-" * 64)
                    for cat in stats["by_category"]:
                        lines.append(
                            f"{cat['category']:<30} {cat['only_in_source']:>12} "
                            f"{cat['only_in_target']:>12} {cat['in_both']:>8}"
                        )

            # Top changes or unique categories
            if stats.get("top_changes"):
                lines.append("\nCategories with Most Changes:")
                for i, item in enumerate(stats["top_changes"], 1):
                    lines.append(f"{i}. {item['category']}: {item['changes']} changes")

            if stats.get("unique_categories"):
                lines.append("\nCategory Distribution:")
                lines.append(
                    f"Unique to {data['metadata']['Source'].split('@')[0]}: {', '.join(stats['unique_categories']['source_only']) or 'None'}"
                )
                lines.append(
                    f"Unique to {data['metadata']['Target'].split('@')[0]}: {', '.join(stats['unique_categories']['target_only']) or 'None'}"
                )
                lines.append(
                    f"Common categories: {', '.join(stats['unique_categories']['common'])}"
                )

            # Versions analyzed for cumulative comparison
            if stats.get("versions_analyzed") and isinstance(
                stats["versions_analyzed"], list
            ):
                lines.append("\nVersions Analyzed:")
                lines.append(f"Total: {len(stats['versions_analyzed'])} versions")
                if len(stats["versions_analyzed"]) <= 10:
                    lines.append(f"Versions: {', '.join(stats['versions_analyzed'])}")
                else:
                    lines.append(
                        f"From {stats['versions_analyzed'][0]} to {stats['versions_analyzed'][-1]}"
                    )

        lines.append("")

        # Module listings
        if data["items"]:
            lines.append("MODULE CHANGES")
            lines.append("-" * 40)

            for item in data["items"]:
                lines.append(f"\n{item['category']} ({item['count']} modules):")
                # Format modules in columns
                modules = item["modules"]
                if modules:
                    # Sort modules for consistent output
                    modules = sorted(modules)
                    # Display in 2 columns for better readability
                    for i in range(0, len(modules), 2):
                        if i + 1 < len(modules):
                            lines.append(f"  {modules[i]:<40} {modules[i + 1]}")
                        else:
                            lines.append(f"  {modules[i]}")

        return "\n".join(lines)

    def _format_csv(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as CSV with rows for each module change."""
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["category", "module", "change_type"]
        )
        writer.writeheader()

        # Determine comparison mode
        is_version_comparison = data["metadata"]["Comparison Type"] == "Version"

        # Write rows for each module
        for item in data["items"]:
            category_name = item["category"]

            # Extract change type from category name
            if is_version_comparison:
                if "Added" in category_name:
                    change_type = "added"
                elif "Removed" in category_name:
                    change_type = "removed"
                else:
                    change_type = "unchanged"
            else:
                if (
                    "Only in" in category_name
                    and data["metadata"]["Source"] in category_name
                ):
                    change_type = "only_in_source"
                elif (
                    "Only in" in category_name
                    and data["metadata"]["Target"] in category_name
                ):
                    change_type = "only_in_target"
                else:
                    change_type = "in_both"

            # Extract base category name (e.g., "Bid Adapters - Added" -> "Bid Adapters")
            base_category = category_name.split(" - ")[0]

            # Write a row for each module
            for module in sorted(item["modules"]):
                writer.writerow(
                    {
                        "category": base_category,
                        "module": module,
                        "change_type": change_type,
                    }
                )

        return output.getvalue()

    def _format_markdown(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as Markdown."""
        lines = []

        # Header
        lines.append(f"# {data['header']}")
        lines.append("")

        # Metadata
        lines.append("## Metadata")
        for key, value in data["metadata"].items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        for key, value in data["summary"].items():
            label = key.replace("_", " ").title()
            # Handle nested value structure
            if isinstance(value, dict) and "value" in value:
                lines.append(f"- **{label}**: {value['value']}")
            else:
                lines.append(f"- **{label}**: {value}")
        lines.append("")

        # Detailed statistics
        stats = data.get("statistics", {})
        if stats:
            lines.append("## Detailed Statistics")
            lines.append("")

            if stats.get("by_category"):
                lines.append("### By Category")
                lines.append("")

                if data["metadata"]["Comparison Type"] == "Version":
                    lines.append("| Category | Added | Removed | Net Change |")
                    lines.append("|----------|-------|---------|------------|")
                    for cat in stats["by_category"]:
                        lines.append(
                            f"| {cat['category']} | {cat['added']} | {cat['removed']} | "
                            f"{cat['net']} |"
                        )
                else:
                    lines.append("| Category | Source Only | Target Only | In Both |")
                    lines.append("|----------|-------------|-------------|---------|")
                    for cat in stats["by_category"]:
                        lines.append(
                            f"| {cat['category']} | {cat['only_in_source']} | "
                            f"{cat['only_in_target']} | {cat['in_both']} |"
                        )
                lines.append("")

        # Module changes
        if data["items"]:
            lines.append("## Module Changes")
            lines.append("")

            for item in data["items"]:
                lines.append(f"### {item['category']} ({item['count']} modules)")
                lines.append("")

                # Format modules in a bullet list
                modules = sorted(item["modules"])
                for module in modules:
                    lines.append(f"- {module}")
                lines.append("")

        return "\n".join(lines)

    def _format_json(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as JSON with proper structure."""
        # Create a flattened structure for JSON output
        output = {
            "metadata": {
                "source_repo": data["metadata"]["Source"].split(" @ ")[0],
                "target_repo": data["metadata"]["Target"].split(" @ ")[0],
                "source_version": data["metadata"]["Source"].split(" @ ")[1],
                "target_version": data["metadata"]["Target"].split(" @ ")[1],
                "comparison_type": data["metadata"]["Comparison Type"],
            },
            "summary": {},
            "items": data["items"],
            "statistics": data["statistics"],
        }

        # Flatten summary values
        for key, value in data["summary"].items():
            if isinstance(value, dict) and "value" in value:
                output["summary"][key] = value["value"]
            else:
                output["summary"][key] = value

        return json.dumps(output, indent=2, sort_keys=True, default=str)
