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
                    "renamed": {"value": stats.total_renamed, "percentage": None},
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

                if category.renamed:
                    # Format renames with detection method
                    rename_strings = []
                    for rename in category.renamed:
                        method_label = {
                            "git_history": "[CONFIRMED]",
                            "case_change": "[case]",
                            "abbreviation": "[abbrev]",
                            "substring": "[substr]",
                            "similarity": "[similar]",
                        }.get(rename.detection_method, f"[{rename.detection_method}]")
                        rename_strings.append(
                            f"{rename.old_module.name} → {rename.new_module.name} {method_label}"
                        )

                    items.append(
                        {
                            "category": f"{cat_name} - Renamed",
                            "modules": rename_strings,
                            "count": len(category.renamed),
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
                        "modules_detailed": [
                            {"name": c.module.name, "added_in": c.added_in_version}
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
                        "modules_detailed": [
                            {
                                "name": c.module.name,
                                "added_in": c.added_in_version,
                                "removed_in": c.removed_in_version,
                            }
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
                # Handle different metadata formats
                source_repo = ""
                target_repo = ""
                if "Source" in data["metadata"]:
                    source_repo = data["metadata"]["Source"].split("@")[0]
                elif "Repository" in data["metadata"]:
                    source_repo = data["metadata"]["Repository"]

                if "Target" in data["metadata"]:
                    target_repo = data["metadata"]["Target"].split("@")[0]
                elif "Repository" in data["metadata"]:
                    target_repo = data["metadata"]["Repository"]

                lines.append(
                    f"Unique to {source_repo}: {', '.join(stats['unique_categories']['source_only']) or 'None'}"
                )
                lines.append(
                    f"Unique to {target_repo}: {', '.join(stats['unique_categories']['target_only']) or 'None'}"
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

                # Check if we have detailed module information
                if "modules_detailed" in item and item["modules_detailed"]:
                    # Use detailed format with version info on the same line but separated
                    for module_info in sorted(
                        item["modules_detailed"], key=lambda x: x["name"]
                    ):
                        version_info = ""
                        if "added_in" in module_info:
                            version_info = f" | added in {module_info['added_in']}"
                        if "removed_in" in module_info:
                            version_info += f", removed in {module_info['removed_in']}"
                        lines.append(f"  {module_info['name']}{version_info}")
                else:
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

            # Add legend for rename detection methods if there are renames
            has_renames = any("Renamed" in item["category"] for item in data["items"])
            if has_renames:
                lines.append("\nRename Detection Methods:")
                lines.append("  [CONFIRMED] - Verified via git history/PRs")
                lines.append("  [case] - Case change (e.g., camelCase to snake_case)")
                lines.append("  [abbrev] - Abbreviation detected")
                lines.append("  [substr] - Substring match")
                lines.append("  [similar] - Character similarity")

        return "\n".join(lines)

    def _format_csv(self, data: dict[str, Any], **kwargs) -> str:
        """Format data as CSV with rows for each module change."""
        output = io.StringIO()

        # Determine if we have detailed module data
        has_detailed = any("modules_detailed" in item for item in data["items"])

        # Determine comparison mode
        comparison_type = data["metadata"]["Comparison Type"]
        is_cumulative = comparison_type == "Cumulative"

        if has_detailed and is_cumulative:
            # Use detailed format with separate columns for cumulative comparisons
            fieldnames = [
                "category",
                "module",
                "added_in_version",
                "removed_in_version",
                "change_type",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
        else:
            # Use standard format
            fieldnames = ["category", "module", "change_type"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

        # Write rows for each module
        for item in data["items"]:
            category_name = item["category"]

            # Extract change type from category name
            if is_cumulative:
                # Cumulative comparison types
                if "still present" in category_name:
                    change_type = "added_still_present"
                elif "then removed" in category_name:
                    change_type = "added_then_removed"
                else:
                    change_type = "changed"
            elif comparison_type == "Version":
                # Version comparison types
                if "Added" in category_name:
                    change_type = "added"
                elif "Removed" in category_name:
                    change_type = "removed"
                elif "Renamed" in category_name:
                    change_type = "renamed"
                else:
                    change_type = "unchanged"
            else:
                # Repository comparison types
                if "Only in" in category_name:
                    # Parse repository name from category to determine source/target
                    if (
                        "Source" in data["metadata"]
                        and data["metadata"]["Source"].split(" @ ")[0] in category_name
                    ):
                        change_type = "only_in_source"
                    elif (
                        "Target" in data["metadata"]
                        and data["metadata"]["Target"].split(" @ ")[0] in category_name
                    ):
                        change_type = "only_in_target"
                    else:
                        # Fallback: check which repo appears in the category name
                        change_type = (
                            "only_in_source"
                            if "source" in category_name.lower()
                            else "only_in_target"
                        )
                else:
                    change_type = "in_both"

            # Extract base category name (e.g., "Bid Adapters - Added" -> "Bid Adapters")
            base_category = category_name.split(" - ")[0]

            # Write a row for each module
            if has_detailed and is_cumulative and "modules_detailed" in item:
                for module_info in item["modules_detailed"]:
                    writer.writerow(
                        {
                            "category": base_category,
                            "module": module_info["name"],
                            "added_in_version": module_info.get("added_in", ""),
                            "removed_in_version": module_info.get("removed_in", ""),
                            "change_type": change_type,
                        }
                    )
            else:
                # Standard format or no detailed data available
                for module in sorted(item["modules"]):
                    # For cumulative comparisons, extract version info from module string
                    if is_cumulative and "(" in module and ")" in module:
                        # Parse module name and version info
                        module_name = module.split(" (")[0]
                        version_info = module.split(" (")[1].rstrip(")")

                        if has_detailed:
                            # Extract version details
                            added_in = ""
                            removed_in = ""
                            if "added in " in version_info:
                                added_in = version_info.replace("added in ", "")
                            elif (
                                "added: " in version_info
                                and "removed: " in version_info
                            ):
                                parts = version_info.split(", ")
                                added_in = parts[0].replace("added: ", "")
                                removed_in = parts[1].replace("removed: ", "")

                            writer.writerow(
                                {
                                    "category": base_category,
                                    "module": module_name,
                                    "added_in_version": added_in,
                                    "removed_in_version": removed_in,
                                    "change_type": change_type,
                                }
                            )
                        else:
                            writer.writerow(
                                {
                                    "category": base_category,
                                    "module": module,
                                    "change_type": change_type,
                                }
                            )
                    else:
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

                comparison_type = data["metadata"]["Comparison Type"]

                if comparison_type == "Version":
                    lines.append(
                        "| Category | Added | Removed | Renamed | Net Change |"
                    )
                    lines.append(
                        "|----------|-------|---------|---------|------------|"
                    )
                    for cat in stats["by_category"]:
                        renamed = cat.get("renamed", 0)
                        lines.append(
                            f"| {cat['category']} | {cat['added']} | {cat['removed']} | "
                            f"{renamed} | {cat['net']} |"
                        )
                elif comparison_type == "Cumulative":
                    lines.append("| Category | Total Added | Still Present | Removed |")
                    lines.append("|----------|-------------|---------------|---------|")
                    for cat in stats["by_category"]:
                        lines.append(
                            f"| {cat['category']} | {cat['total_added']} | "
                            f"{cat['still_present']} | {cat['removed']} |"
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

                # Check if we have detailed module information
                if "modules_detailed" in item and item["modules_detailed"]:
                    # Create a table for detailed information
                    if any("removed_in" in m for m in item["modules_detailed"]):
                        # Has both added and removed columns
                        lines.append("| Module | Added In | Removed In |")
                        lines.append("|--------|----------|------------|")
                        for module_info in sorted(
                            item["modules_detailed"], key=lambda x: x["name"]
                        ):
                            lines.append(
                                f"| {module_info['name']} | {module_info.get('added_in', '')} | "
                                f"{module_info.get('removed_in', '')} |"
                            )
                    else:
                        # Only has added column
                        lines.append("| Module | Added In |")
                        lines.append("|--------|----------|")
                        for module_info in sorted(
                            item["modules_detailed"], key=lambda x: x["name"]
                        ):
                            lines.append(
                                f"| {module_info['name']} | {module_info.get('added_in', '')} |"
                            )
                else:
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
            "metadata": {},
            "summary": {},
            "items": [],
            "statistics": data["statistics"],
        }

        # Process items to include modules_detailed if available
        for item in data["items"]:
            new_item = {
                "category": item["category"],
                "count": item["count"],
                "modules": item["modules"],
            }
            if "modules_detailed" in item:
                new_item["modules_detailed"] = item["modules_detailed"]
            output["items"].append(new_item)

        # Parse metadata safely - handle both regular and cumulative comparison formats
        if "Source" in data["metadata"] and " @ " in data["metadata"]["Source"]:
            # Regular comparison format
            source_parts = data["metadata"]["Source"].split(" @ ", 1)
            output["metadata"]["source_repo"] = source_parts[0]
            output["metadata"]["source_version"] = (
                source_parts[1] if len(source_parts) > 1 else ""
            )
        elif "Repository" in data["metadata"]:
            # Cumulative comparison format
            output["metadata"]["source_repo"] = data["metadata"].get("Repository", "")
            output["metadata"]["source_version"] = data["metadata"].get(
                "From Version", ""
            )
        else:
            output["metadata"]["source_repo"] = data["metadata"].get("Source", "")
            output["metadata"]["source_version"] = ""

        if "Target" in data["metadata"] and " @ " in data["metadata"]["Target"]:
            # Regular comparison format
            target_parts = data["metadata"]["Target"].split(" @ ", 1)
            output["metadata"]["target_repo"] = target_parts[0]
            output["metadata"]["target_version"] = (
                target_parts[1] if len(target_parts) > 1 else ""
            )
        elif "Repository" in data["metadata"]:
            # Cumulative comparison format (same repo)
            output["metadata"]["target_repo"] = data["metadata"].get("Repository", "")
            output["metadata"]["target_version"] = data["metadata"].get(
                "To Version", ""
            )
        else:
            output["metadata"]["target_repo"] = data["metadata"].get("Target", "")
            output["metadata"]["target_version"] = ""

        output["metadata"]["comparison_type"] = data["metadata"].get(
            "Comparison Type", ""
        )

        # Add versions analyzed for cumulative comparisons
        if "Versions Analyzed" in data["metadata"]:
            output["metadata"]["versions_analyzed"] = data["metadata"][
                "Versions Analyzed"
            ]

        # Flatten summary values
        for key, value in data["summary"].items():
            if isinstance(value, dict) and "value" in value:
                output["summary"][key] = value["value"]
            else:
                output["summary"][key] = value

        return json.dumps(output, indent=2, sort_keys=True, default=str)
