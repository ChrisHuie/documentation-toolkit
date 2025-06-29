"""Tests for module history output formatter."""

import json
import tempfile
from pathlib import Path

import pytest

from src.module_history.data_models import ModuleHistoryEntry, ModuleHistoryResult
from src.module_history.output_formatter import ModuleHistoryFormatter


@pytest.fixture
def sample_entries():
    """Create sample module history entries for testing."""
    return [
        ModuleHistoryEntry(
            module_name="appnexus",
            module_type="bid_adapters",
            first_version="2.15.0",
            first_major_version=2,
            file_path="modules/appnexusBidAdapter.js",
            first_commit_date="2023-01-01T00:00:00Z",
            first_commit_sha="abc123",
        ),
        ModuleHistoryEntry(
            module_name="rubicon",
            module_type="bid_adapters",
            first_version="1.0.0",
            first_major_version=1,
            file_path="modules/rubiconBidAdapter.js",
        ),
        ModuleHistoryEntry(
            module_name="google",
            module_type="analytics_adapters",
            first_version="3.0.0",
            first_major_version=3,
            file_path="modules/googleAnalyticsAdapter.js",
        ),
    ]


@pytest.fixture
def sample_result(sample_entries):
    """Create sample module history result for testing."""
    modules_by_type = {
        "bid_adapters": sample_entries[:2],
        "analytics_adapters": [sample_entries[2]],
    }

    modules_by_version = {
        1: [sample_entries[1]],
        2: [sample_entries[0]],
        3: [sample_entries[2]],
    }

    return ModuleHistoryResult(
        repo_name="prebid/Prebid.js",
        total_modules=3,
        modules_by_type=modules_by_type,
        modules_by_version=modules_by_version,
        metadata={"analysis_date": "2023-01-01"},
    )


class TestModuleHistoryFormatter:
    """Test ModuleHistoryFormatter."""

    def test_format_table_output(self, sample_result):
        """Test table output formatting."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_table_output(sample_result)

        assert "Module History: prebid/Prebid.js" in output
        assert "Total Modules: 3" in output
        assert "📦 Bid Adapters (2 modules)" in output
        assert "📦 Analytics Adapters (1 modules)" in output
        assert "appnexus" in output
        assert "First Version: v2.15.0" in output
        assert "modules/appnexusBidAdapter.js" in output

    def test_format_table_output_filtered_by_type(self, sample_result):
        """Test table output with type filter."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_table_output(
            sample_result, module_type="bid_adapters"
        )

        assert "Filtered by Type: bid_adapters" in output
        assert "appnexus" in output
        assert "rubicon" in output
        assert "google" not in output

    def test_format_table_output_filtered_by_version(self, sample_result):
        """Test table output with version filter."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_table_output(sample_result, major_version=2)

        assert "Filtered by Major Version: 2" in output
        assert "appnexus" in output
        assert "rubicon" not in output
        assert "google" not in output

    def test_format_csv_output(self, sample_result):
        """Test CSV output formatting."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_csv_output(sample_result)

        lines = output.strip().split("\n")

        # Check header
        header = lines[0]
        expected_cols = [
            "module_name",
            "module_type",
            "first_version",
            "first_major_version",
            "file_path",
            "first_commit_date",
            "first_commit_sha",
        ]
        for col in expected_cols:
            assert col in header

        # Check data rows (should have 3 + 1 header = 4 lines)
        assert len(lines) == 4

        # Check that appnexus row has commit info
        appnexus_line = next(line for line in lines if "appnexus" in line)
        assert "2023-01-01T00:00:00Z" in appnexus_line
        assert "abc123" in appnexus_line

    def test_format_json_output(self, sample_result):
        """Test JSON output formatting."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_json_output(sample_result)

        data = json.loads(output)

        assert data["repository"] == "prebid/Prebid.js"
        assert data["total_modules"] == 3
        assert len(data["modules"]) == 3
        assert data["metadata"]["analysis_date"] == "2023-01-01"

        # Check module data structure
        appnexus_module = next(
            m for m in data["modules"] if m["module_name"] == "appnexus"
        )
        assert appnexus_module["module_type"] == "bid_adapters"
        assert appnexus_module["first_version"] == "2.15.0"
        assert appnexus_module["first_major_version"] == 2
        assert appnexus_module["first_commit_date"] == "2023-01-01T00:00:00Z"

    def test_save_to_file(self, sample_result):
        """Test saving output to file."""
        formatter = ModuleHistoryFormatter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            formatter.save_to_file(sample_result, temp_file, format_type="json")

            # Verify file was created and contains correct data
            with open(temp_file) as f:
                data = json.load(f)

            assert data["repository"] == "prebid/Prebid.js"
            assert data["total_modules"] == 3

        finally:
            Path(temp_file).unlink()

    def test_format_cache_info(self):
        """Test cache info formatting."""
        formatter = ModuleHistoryFormatter()

        cache_info = {
            "repo_name": "prebid/Prebid.js",
            "cache_file": "/path/to/cache.json",
            "last_analyzed_version": "v1.2.3",
            "module_count": 150,
            "metadata": {"analysis_date": "2023-01-01", "total_modules": 150},
        }

        output = formatter.format_cache_info(cache_info)

        assert "Cache Information:" in output
        assert "Repository: prebid/Prebid.js" in output
        assert "Last Analyzed Version: v1.2.3" in output
        assert "Module Count: 150" in output
        assert "analysis_date: 2023-01-01" in output

    def test_format_cache_info_none(self):
        """Test cache info formatting with None input."""
        formatter = ModuleHistoryFormatter()
        output = formatter.format_cache_info(None)

        assert output == "No cache information available."

    def test_unsupported_format_error(self, sample_result):
        """Test error handling for unsupported format."""
        formatter = ModuleHistoryFormatter()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported format"):
                formatter.save_to_file(
                    sample_result, temp_file, format_type="unsupported"
                )
        finally:
            Path(temp_file).unlink()
