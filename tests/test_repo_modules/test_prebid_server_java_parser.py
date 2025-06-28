"""
Tests for the PrebidServerJavaParser
"""

from src.repo_modules.config import RepoConfig
from src.repo_modules.parser_factory import PrebidServerJavaParser


class TestPrebidServerJavaParser:
    """Test suite for PrebidServerJavaParser."""

    def test_prebid_server_java_parser_creation(self):
        """Test that PrebidServerJavaParser can be created with proper config."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)
        assert parser.config == config

    def test_prebid_server_java_parser_categorize_bid_adapters(self):
        """Test categorizing bid adapters."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)

        # Mock data for bid adapters
        files = {
            "src/main/java/org/prebid/server/bidder/appnexus": "",
            "src/main/java/org/prebid/server/bidder/rubicon": "",
            "src/main/java/org/prebid/server/bidder/pubmatic": "",
        }

        result = parser._categorize_by_path(
            "Bid Adapters", "src/main/java/org/prebid/server/bidder", files
        )

        assert "Bid Adapters" in result
        assert set(result["Bid Adapters"]) == {"appnexus", "rubicon", "pubmatic"}

    def test_prebid_server_java_parser_categorize_analytics_adapters(self):
        """Test categorizing analytics adapters."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)

        # Mock data for analytics adapters
        files = {
            "src/main/java/org/prebid/server/analytics/reporter/pubstack": "",
            "src/main/java/org/prebid/server/analytics/reporter/agma": "",
            "src/main/java/org/prebid/server/analytics/reporter/log": "",  # Should be excluded
        }

        result = parser._categorize_by_path(
            "Analytics Adapters",
            "src/main/java/org/prebid/server/analytics/reporter",
            files,
        )

        assert "Analytics Adapters" in result
        assert set(result["Analytics Adapters"]) == {"pubstack", "agma"}

    def test_prebid_server_java_parser_categorize_general_modules(self):
        """Test categorizing general modules with proper formatting."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)

        # Mock data for general modules
        files = {
            "extra/modules/pb-ortb2-blocking": "",
            "extra/modules/pb-request-correction": "",
            "extra/modules/normal-module": "",
        }

        result = parser._categorize_by_path("General Modules", "extra/modules", files)

        assert "General Modules" in result
        expected_modules = {
            "ortb2 blocking",  # pb- prefix removed, - replaced with space
            "request correction",  # pb- prefix removed, - replaced with space
            "normal module",  # just - replaced with space
        }
        assert set(result["General Modules"]) == expected_modules

    def test_prebid_server_java_parser_categorize_privacy_modules(self):
        """Test categorizing privacy modules."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)

        # Mock data for privacy modules
        files = {
            "src/main/java/org/prebid/server/activity/infrastructure/privacy/uscustomlogic": "",
            "src/main/java/org/prebid/server/activity/infrastructure/privacy/usnat": "",
        }

        result = parser._categorize_by_path(
            "Privacy Modules",
            "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            files,
        )

        assert "Privacy Modules" in result
        assert set(result["Privacy Modules"]) == {"uscustomlogic", "usnat"}

    def test_prebid_server_java_parser_parse_full_data(self):
        """Test parsing complete data structure."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Prebid Server Java implementation",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            },
        )
        parser = PrebidServerJavaParser(config)

        # Mock complete data structure
        data = {
            "repo": "prebid/prebid-server-java",
            "version": "master",
            "paths": {
                "src/main/java/org/prebid/server/bidder": {
                    "src/main/java/org/prebid/server/bidder/appnexus": "",
                    "src/main/java/org/prebid/server/bidder/rubicon": "",
                },
                "src/main/java/org/prebid/server/analytics/reporter": {
                    "src/main/java/org/prebid/server/analytics/reporter/pubstack": "",
                    "src/main/java/org/prebid/server/analytics/reporter/log": "",  # Should be excluded
                },
                "extra/modules": {
                    "extra/modules/pb-ortb2-blocking": "",
                },
                "src/main/java/org/prebid/server/activity/infrastructure/privacy": {
                    "src/main/java/org/prebid/server/activity/infrastructure/privacy/uscustomlogic": "",
                },
            },
        }

        result = parser.parse(data)

        # Verify the output contains all sections
        assert "Repository: prebid/prebid-server-java" in result
        assert "Version: master" in result
        assert "Prebid Server Java Categories:" in result
        assert "📦 Bid Adapters" in result
        assert "📦 Analytics Adapters" in result
        assert "📦 General Modules" in result
        assert "📦 Privacy Modules" in result
        assert "JSON Output:" in result

        # Verify specific content
        assert "appnexus" in result
        assert "rubicon" in result
        assert "pubstack" in result
        # Check that log is not in Analytics Adapters specifically (but may appear in other modules like uscustomlogic)
        assert '"log"' not in result  # Should be excluded from JSON
        assert (
            "ortb2 blocking" in result
        )  # Should have pb- removed and - replaced with space
        assert "uscustomlogic" in result
