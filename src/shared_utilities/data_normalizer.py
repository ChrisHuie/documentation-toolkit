"""
Data normalization utilities to ensure consistent data structure across all output formats.
"""

from typing import Any


class DataNormalizer:
    """Normalizes data to ensure all output formats receive the same enriched data."""

    @staticmethod
    def normalize_with_percentages(data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize data by adding percentage calculations to all relevant fields.

        This ensures all formatters receive the same complete data structure.
        """
        # Create a deep copy to avoid modifying the original
        normalized = {
            "version": data.get("version"),
            "total_adapters": data.get("total_adapters", 0),
            "adapters_with_media_types": data.get("adapters_with_media_types", 0),
            "timestamp": data.get("timestamp"),
            "adapters": data.get("adapters", {}),
        }

        # Get summary data
        summary = data.get("summary", {})
        total_adapters = summary.get("total_adapters", 0)

        # Normalize media type data with percentages
        by_media_type_normalized = {}
        for media_type, value in summary.get("by_media_type", {}).items():
            # Handle both raw counts and already normalized data
            if isinstance(value, dict) and "count" in value:
                # Already normalized
                by_media_type_normalized[media_type] = value
            else:
                # Raw count
                count = value
                percentage = (count / total_adapters * 100) if total_adapters > 0 else 0
                by_media_type_normalized[media_type] = {
                    "count": count,
                    "percentage": round(percentage, 1),
                }

        # Normalize combination data with percentages
        by_combination_normalized = {}
        for combination, value in summary.get("by_combination", {}).items():
            # Handle both raw counts and already normalized data
            if isinstance(value, dict) and "count" in value:
                # Already normalized
                by_combination_normalized[combination] = value
            else:
                # Raw count
                count = value
                percentage = (count / total_adapters * 100) if total_adapters > 0 else 0
                by_combination_normalized[combination] = {
                    "count": count,
                    "percentage": round(percentage, 1),
                }

        # Sort combinations by count (descending) for consistent ordering
        by_combination_sorted = dict(
            sorted(
                by_combination_normalized.items(), key=lambda x: (-x[1]["count"], x[0])
            )
        )

        # Create normalized summary
        normalized["summary"] = {
            "total_adapters": total_adapters,
            "by_media_type": by_media_type_normalized,
            "by_combination": by_combination_sorted,
        }

        return normalized

    @staticmethod
    def get_formatted_percentage(value: dict[str, Any]) -> str:
        """Get formatted percentage string from normalized data."""
        return f"{value['count']} ({value['percentage']:.1f}%)"

    @staticmethod
    def get_media_types_display(
        media_types: list[str], format_type: str = "array"
    ) -> str:
        """
        Format media types for display based on format type.

        Args:
            media_types: List of media types
            format_type: How to format ("array", "csv", "plain")
        """
        if not media_types:
            return "[]" if format_type == "array" else ""

        if format_type == "array":
            return f"[{', '.join(media_types)}]"
        elif format_type == "csv":
            return ", ".join(media_types)
        else:  # plain
            return " ".join(media_types)
