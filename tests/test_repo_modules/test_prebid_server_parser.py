"""
Tests for the PrebidServerGoParser
"""

from src.repo_modules_by_version.config import RepoConfig
from src.repo_modules_by_version.parser_factory import PrebidServerGoParser


class TestPrebidServerGoParser:
    """Test suite for PrebidServerGoParser."""

    def test_prebid_server_go_parser_creation(self):
        """Test that PrebidServerGoParser can be created with proper config."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Prebid Server Go implementation",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)
        assert parser.config == config

    def test_prebid_server_parser_categorize_bid_adapters(self):
        """Test categorizing bid adapters."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Prebid Server Go implementation",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)

        # Mock data for bid adapters
        files = {
            "adapters/33across": "",
            "adapters/appnexus": "",
            "adapters/rubicon": "",
        }

        result = parser._categorize_by_path("Bid Adapters", "adapters", files)

        assert "Bid Adapters" in result
        assert set(result["Bid Adapters"]) == {"33across", "appnexus", "rubicon"}

    def test_prebid_server_parser_categorize_analytics_adapters(self):
        """Test categorizing analytics adapters."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Prebid Server Go implementation",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)

        # Mock data for analytics adapters
        files = {
            "analytics/pubstack": "",
            "analytics/agma": "",
            "analytics/build": "",  # Should be excluded
            "analytics/clients": "",  # Should be excluded
            "analytics/filesystem": "",  # Should be excluded
        }

        result = parser._categorize_by_path("Analytics Adapters", "analytics", files)

        assert "Analytics Adapters" in result
        assert set(result["Analytics Adapters"]) == {"pubstack", "agma"}

    def test_prebid_server_parser_categorize_general_modules(self):
        """Test categorizing general modules."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Prebid Server Go implementation",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)

        # Mock data for general modules
        files = {
            "modules/fiftyonedegrees": "",
            "modules/fiftyonedegrees/devicedetection": "",
            "modules/prebid": "",
            "modules/prebid/ortb2blocking": "",
            "modules/generator": "",
        }

        result = parser._categorize_by_path("General Modules", "modules", files)

        assert "General Modules" in result
        expected_modules = {"fiftyonedegrees devicedetection", "prebid ortb2blocking"}
        assert set(result["General Modules"]) == expected_modules

    def test_prebid_server_parser_parse_full_data(self):
        """Test parsing complete data structure."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Prebid Server Go implementation",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)

        # Mock complete data structure
        data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {
                "adapters": {
                    "adapters/33across": "",
                    "adapters/appnexus": "",
                },
                "analytics": {
                    "analytics/pubstack": "",
                    "analytics/build": "",  # Should be excluded
                },
                "modules": {
                    "modules/fiftyonedegrees": "",
                    "modules/fiftyonedegrees/devicedetection": "",
                },
            },
        }

        result = parser.parse(data)

        # Verify the output contains all sections
        assert "Repository: prebid/prebid-server" in result
        assert "Version: master" in result
        assert "Prebid Server Go Categories:" in result
        assert "📦 Bid Adapters" in result
        assert "📦 Analytics Adapters" in result
        assert "📦 General Modules" in result
        assert "JSON Output:" in result

        # Verify specific content
        assert "33across" in result
        assert "appnexus" in result
        assert "pubstack" in result
        assert "build" not in result  # Should be excluded
        assert "fiftyonedegrees devicedetection" in result
        # Should not include directories without subdirectories
        assert "generator" not in result
        assert "moduledeps" not in result
