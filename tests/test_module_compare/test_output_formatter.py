"""Tests for module comparison output formatter."""

import csv
import json
from io import StringIO

import pytest

from src.module_compare.data_models import (
    CategoryComparison,
    ComparisonMode,
    ComparisonResult,
    ModuleInfo,
)
from src.module_compare.output_formatter import ModuleCompareOutputFormatter


class TestModuleCompareOutputFormatter:
    """Test ModuleCompareOutputFormatter class."""

    @pytest.fixture
    def version_comparison_result(self):
        """Create a sample version comparison result."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.51.0",
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        # Add Bid Adapters category
        bid_adapters = CategoryComparison(
            category="Bid Adapters", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )
        bid_adapters.added = [
            ModuleInfo(name="newAdapter1", path="modules/newAdapter1BidAdapter.js"),
            ModuleInfo(name="newAdapter2", path="modules/newAdapter2BidAdapter.js"),
        ]
        bid_adapters.removed = [
            ModuleInfo(name="oldAdapter", path="modules/oldAdapterBidAdapter.js")
        ]
        bid_adapters.unchanged = [
            ModuleInfo(name="stableAdapter", path="modules/stableAdapterBidAdapter.js")
        ]
        result.categories["Bid Adapters"] = bid_adapters

        # Add Analytics category
        analytics = CategoryComparison(
            category="Analytics", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )
        analytics.added = [
            ModuleInfo(name="newAnalytics", path="modules/newAnalyticsAdapter.js")
        ]
        analytics.unchanged = [
            ModuleInfo(name="googleAnalytics", path="modules/googleAnalyticsAdapter.js")
        ]
        result.categories["Analytics"] = analytics

        return result

    @pytest.fixture
    def repo_comparison_result(self):
        """Create a sample repository comparison result."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.51.0",
            target_repo="prebid-server",
            target_version="v3.8.0",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Add Bid Adapters category
        bid_adapters = CategoryComparison(
            category="Bid Adapters",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )
        bid_adapters.only_in_source = [
            ModuleInfo(name="clientOnly1", path="modules/clientOnly1BidAdapter.js"),
            ModuleInfo(name="clientOnly2", path="modules/clientOnly2BidAdapter.js"),
        ]
        bid_adapters.only_in_target = [
            ModuleInfo(name="serverOnly", path="adapters/serverOnly")
        ]
        bid_adapters.in_both = [
            ModuleInfo(name="appnexus", path="modules/appnexusBidAdapter.js"),
            ModuleInfo(name="rubicon", path="modules/rubiconBidAdapter.js"),
        ]
        result.categories["Bid Adapters"] = bid_adapters

        return result

    def test_prepare_data_version_comparison(self, version_comparison_result):
        """Test preparing data for version comparison."""
        formatter = ModuleCompareOutputFormatter()
        data = formatter.prepare_data(version_comparison_result, show_unchanged=False)

        # Check header
        assert "v9.0.0 → v9.51.0" in data["header"]

        # Check metadata
        assert data["metadata"]["Source"] == "prebid-js @ v9.0.0"
        assert data["metadata"]["Target"] == "prebid-js @ v9.51.0"
        assert data["metadata"]["Comparison Type"] == "Version"

        # Check summary
        assert data["summary"]["added"]["value"] == 3
        assert data["summary"]["removed"]["value"] == 1
        assert data["summary"]["net_change"]["value"] == 2

        # Check items (should not include unchanged by default)
        assert len(data["items"]) == 3  # 2 added categories + 1 removed category
        assert any(item["category"] == "Bid Adapters - Added" for item in data["items"])
        assert any(
            item["category"] == "Bid Adapters - Removed" for item in data["items"]
        )
        assert any(item["category"] == "Analytics - Added" for item in data["items"])
        assert not any("Unchanged" in item["category"] for item in data["items"])

    def test_prepare_data_repo_comparison(self, repo_comparison_result):
        """Test preparing data for repository comparison."""
        formatter = ModuleCompareOutputFormatter()
        data = formatter.prepare_data(repo_comparison_result, show_unchanged=False)

        # Check header
        assert "prebid-js vs prebid-server" in data["header"]

        # Check metadata
        assert data["metadata"]["Comparison Type"] == "Repository"

        # Check summary
        assert data["summary"]["only_in_source"]["value"] == 2
        assert data["summary"]["only_in_target"]["value"] == 1
        assert data["summary"]["in_both"]["value"] == 2

        # Check items (should not include common modules by default)
        assert len(data["items"]) == 2  # Only differences
        assert any("Only in prebid-js" in item["category"] for item in data["items"])
        assert any(
            "Only in prebid-server" in item["category"] for item in data["items"]
        )
        assert not any("In Both" in item["category"] for item in data["items"])

    def test_prepare_data_with_unchanged(self, version_comparison_result):
        """Test preparing data with unchanged modules included."""
        formatter = ModuleCompareOutputFormatter()
        data = formatter.prepare_data(version_comparison_result, show_unchanged=True)

        # Should include unchanged items
        items_with_unchanged = [
            item for item in data["items"] if "Unchanged" in item["category"]
        ]
        assert len(items_with_unchanged) == 2  # Bid Adapters and Analytics unchanged

    def test_format_table_output(self, version_comparison_result):
        """Test table format output."""
        formatter = ModuleCompareOutputFormatter()
        output = formatter.format_output(
            version_comparison_result, "table", show_unchanged=False
        )

        # Check key elements in output
        assert "Module Comparison: prebid-js (v9.0.0 → v9.51.0)" in output
        assert "SUMMARY" in output
        assert "DETAILED STATISTICS" in output
        assert "MODULE CHANGES" in output
        assert "Bid Adapters - Added (2 modules):" in output
        assert "newAdapter1" in output
        assert "newAdapter2" in output
        assert "oldAdapter" in output

    def test_format_json_output(self, version_comparison_result):
        """Test JSON format output."""
        formatter = ModuleCompareOutputFormatter()
        output = formatter.format_output(
            version_comparison_result, "json", show_unchanged=False
        )

        # Parse JSON and verify structure
        data = json.loads(output)
        assert data["metadata"]["source_repo"] == "prebid-js"
        assert data["metadata"]["target_repo"] == "prebid-js"
        assert data["summary"]["added"] == 3
        assert data["summary"]["removed"] == 1
        assert "items" in data
        assert "statistics" in data

    def test_format_csv_output(self, version_comparison_result):
        """Test CSV format output."""
        formatter = ModuleCompareOutputFormatter()
        output = formatter.format_output(
            version_comparison_result, "csv", show_unchanged=False
        )

        # Parse CSV and verify structure
        reader = csv.DictReader(StringIO(output))
        rows = list(reader)

        # Should have rows for each change
        assert len(rows) > 0
        assert all(key in rows[0] for key in ["category", "module", "change_type"])

        # Check specific entries
        added_rows = [r for r in rows if r["change_type"] == "added"]
        removed_rows = [r for r in rows if r["change_type"] == "removed"]
        assert len(added_rows) == 3
        assert len(removed_rows) == 1

    def test_format_markdown_output(self, repo_comparison_result):
        """Test Markdown format output."""
        formatter = ModuleCompareOutputFormatter()
        output = formatter.format_output(
            repo_comparison_result, "markdown", show_unchanged=False
        )

        # Check Markdown elements
        assert "# Module Comparison:" in output
        assert "## Metadata" in output
        assert "## Summary" in output
        assert "## Module Changes" in output
        assert "### Bid Adapters - Only in prebid-js" in output
        assert "- clientOnly1" in output
        assert "- clientOnly2" in output

    def test_statistics_in_output(self, version_comparison_result):
        """Test that statistics are properly included in output."""
        formatter = ModuleCompareOutputFormatter()
        data = formatter.prepare_data(version_comparison_result, show_unchanged=False)

        # Check statistics structure
        stats = data["statistics"]
        assert "overall" in stats
        assert "by_category" in stats
        assert "top_changes" in stats

        # Check category statistics
        by_category = stats["by_category"]
        bid_adapter_stats = next(
            c for c in by_category if c["category"] == "Bid Adapters"
        )
        assert bid_adapter_stats["added"] == 2
        assert bid_adapter_stats["removed"] == 1
        assert bid_adapter_stats["net"] == 1
