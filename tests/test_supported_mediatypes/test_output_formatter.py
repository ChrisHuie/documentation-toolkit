"""
Tests for MediaTypeOutputFormatter
"""

import json

import pytest

from src.supported_mediatypes.output_formatter import MediaTypeOutputFormatter


class TestMediaTypeOutputFormatter:
    """Test cases for MediaTypeOutputFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create a MediaTypeOutputFormatter instance."""
        return MediaTypeOutputFormatter()

    @pytest.fixture
    def sample_data(self):
        """Create sample media type data for testing."""
        return {
            "version": "v9.0.0",
            "total_adapters": 3,
            "adapters_with_media_types": 3,
            "adapters": {
                "appnexus": {
                    "mediaTypes": ["banner", "video"],
                    "file": "modules/appnexusBidAdapter.js",
                },
                "rubicon": {
                    "mediaTypes": ["banner", "video", "native"],
                    "file": "modules/rubiconBidAdapter.js",
                },
                "amazon": {
                    "mediaTypes": ["banner"],
                    "file": "modules/amazonBidAdapter.js",
                },
            },
            "summary": {
                "total_adapters": 3,
                "by_media_type": {"banner": 3, "video": 2, "native": 1},
                "by_combination": {
                    "banner": 1,
                    "banner, video": 1,
                    "banner, native, video": 1,
                },
            },
        }

    def test_format_table_basic(self, formatter, sample_data):
        """Test basic table formatting."""
        output = formatter.format(sample_data, "table")

        assert "Prebid.js Supported Media Types Report" in output
        assert "Version: v9.0.0" in output
        assert "Total Adapters: 3" in output
        assert "appnexus" in output
        assert "banner, video" in output
        assert "rubicon" in output
        assert "banner, video, native" in output

    def test_format_table_with_summary(self, formatter, sample_data):
        """Test table formatting with summary."""
        output = formatter.format(sample_data, "table", show_summary=True)

        assert "Summary Statistics:" in output
        assert "Media Type Usage:" in output
        assert "Banner: 3 (100.0%)" in output
        assert "Video: 2 (66.7%)" in output
        assert "Native: 1 (33.3%)" in output
        assert "Media Type Combinations:" in output

    def test_format_json(self, formatter, sample_data):
        """Test JSON formatting with percentages."""
        output = formatter.format(sample_data, "json")
        parsed = json.loads(output)

        assert parsed["version"] == "v9.0.0"
        assert parsed["metadata"]["total_adapters"] == 3
        assert "appnexus" in parsed["adapters"]
        assert parsed["adapters"]["appnexus"]["mediaTypes"] == ["banner", "video"]

        # Check summary has percentages
        assert parsed["summary"]["total_adapters"] == 3
        assert parsed["summary"]["by_media_type"]["banner"]["count"] == 3
        assert parsed["summary"]["by_media_type"]["banner"]["percentage"] == 100.0
        assert parsed["summary"]["by_media_type"]["video"]["count"] == 2
        assert parsed["summary"]["by_media_type"]["video"]["percentage"] == 66.7
        assert parsed["summary"]["by_combination"]["banner, video"]["count"] == 1
        assert (
            parsed["summary"]["by_combination"]["banner, video"]["percentage"] == 33.3
        )

    def test_format_csv(self, formatter, sample_data):
        """Test CSV formatting."""
        output = formatter.format(sample_data, "csv")
        lines = output.strip().split("\n")

        # Check header
        assert "Prebid.js Supported Media Types Report" in lines[0]
        assert "Version: v9.0.0" in lines[1]

        # Check column headers
        headers = lines[4].split(",")
        assert headers[0] == "Adapter Name"
        assert headers[1] == "Banner"
        assert headers[2] == "Video"
        assert headers[3] == "Native"

        # Check data rows
        assert any("appnexus" in line and "Yes" in line for line in lines)
        assert any(
            "rubicon" in line and all(x in line for x in ["Yes", "Yes", "Yes"])
            for line in lines
        )

    def test_format_markdown(self, formatter, sample_data):
        """Test Markdown formatting."""
        output = formatter.format(sample_data, "markdown")

        assert "# Prebid.js Supported Media Types" in output
        assert "**Version**: v9.0.0" in output
        assert "| Adapter | Media Types | File |" in output
        assert "| appnexus | banner, video | appnexusBidAdapter.js |" in output
        assert "## Summary Statistics" in output
        assert "### Media Type Usage" in output

    def test_format_yaml(self, formatter, sample_data):
        """Test YAML formatting."""
        try:
            import yaml

            output = formatter.format(sample_data, "yaml")
            parsed = yaml.safe_load(output)

            assert parsed["version"] == "v9.0.0"
            assert "appnexus" in parsed["adapters"]
        except ImportError:
            pytest.skip("PyYAML not installed")

    def test_format_html(self, formatter, sample_data):
        """Test HTML formatting."""
        output = formatter.format(sample_data, "html")

        assert "<!DOCTYPE html>" in output
        assert "<title>Output</title>" in output
        assert "Prebid.js Supported Media Types" in output
        assert "v9.0.0" in output

    def test_empty_adapters(self, formatter):
        """Test formatting with no adapters."""
        data = {
            "version": "v9.0.0",
            "total_adapters": 0,
            "adapters_with_media_types": 0,
            "adapters": {},
            "summary": {
                "total_adapters": 0,
                "by_media_type": {"banner": 0, "video": 0, "native": 0},
                "by_combination": {},
            },
        }

        output = formatter.format(data, "table")
        assert "Total Adapters: 0" in output

    def test_adapter_without_media_types(self, formatter):
        """Test formatting adapter with no detected media types."""
        data = {
            "version": "v9.0.0",
            "total_adapters": 1,
            "adapters_with_media_types": 1,
            "adapters": {
                "unknown": {"mediaTypes": [], "file": "modules/unknownBidAdapter.js"}
            },
            "summary": {
                "total_adapters": 1,
                "by_media_type": {"banner": 0, "video": 0, "native": 0},
                "by_combination": {},
            },
        }

        output = formatter.format(data, "table")
        assert "unknown" in output
        assert "[]" in output  # Empty array for no media types

    def test_json_output_structure(self, formatter, sample_data):
        """Test JSON output has correct structure (without saving to file)."""
        # Test the format method directly instead of save
        json_output = formatter.format(sample_data, "json")
        parsed = json.loads(json_output)

        assert parsed["version"] == "v9.0.0"
        assert parsed["metadata"]["total_adapters"] == 3
        assert "adapters" in parsed
        assert "summary" in parsed
