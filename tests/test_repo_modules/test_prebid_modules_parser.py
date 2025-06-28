"""
Tests for PrebidJSParser functionality
"""

import json

from src.repo_modules.config import RepoConfig
from src.repo_modules.parser_factory import PrebidJSParser


class TestPrebidJSParser:
    """Test PrebidJSParser implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RepoConfig(
            repo="prebid/Prebid.js",
            directory="modules",
            description="Test repository",
            versions=["master"],
            parser_type="prebid_js",
            modules_path="modules",
        )
        self.parser = PrebidJSParser(self.config)

    def test_prebid_modules_parser_initialization(self):
        """Test PrebidJSParser can be initialized."""
        assert isinstance(self.parser, PrebidJSParser)
        assert self.parser.config == self.config

    def test_categorize_bid_adapters(self):
        """Test categorization of bid adapters."""
        files = {
            "modules/appnexusBidAdapter.js": "content",
            "modules/rubiconBidAdapter.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert "appnexus" in categories["bid_adapters"]
        assert "rubicon" in categories["bid_adapters"]
        assert len(categories["bid_adapters"]) == 2

    def test_categorize_analytics_adapters(self):
        """Test categorization of analytics adapters."""
        files = {
            "modules/googleAnalyticsAnalyticsAdapter.js": "content",
            "modules/facebookAnalyticsAdapter.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert "googleAnalytics" in categories["analytics_adapters"]
        assert "facebook" in categories["analytics_adapters"]
        assert len(categories["analytics_adapters"]) == 2

    def test_categorize_rtd_modules(self):
        """Test categorization of RTD modules."""
        files = {
            "modules/facebookRtdProvider.js": "content",
            "modules/amazonRtdProvider.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert "facebook" in categories["rtd_modules"]
        assert "amazon" in categories["rtd_modules"]
        assert len(categories["rtd_modules"]) == 2

    def test_categorize_identity_modules(self):
        """Test categorization of identity modules."""
        files = {
            "modules/facebookIdSystem.js": "content",
            "modules/googleIdSystem.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert "facebook" in categories["identity_modules"]
        assert "google" in categories["identity_modules"]
        assert len(categories["identity_modules"]) == 2

    def test_categorize_other_modules(self):
        """Test categorization of other modules."""
        files = {
            "modules/currency.js": "content",
            "modules/consentManagement.js": "content",
            "modules/userSync.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert "currency" in categories["other_modules"]
        assert "consentManagement" in categories["other_modules"]
        assert "userSync" in categories["other_modules"]
        assert len(categories["other_modules"]) == 3

    def test_ignore_non_js_files(self):
        """Test that non-.js files are ignored."""
        files = {
            "modules/README.md": "content",
            "modules/config.yaml": "content",
            "modules/appnexusBidAdapter.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        # Only the .js file should be categorized
        total_modules = sum(len(modules) for modules in categories.values())
        assert total_modules == 1
        assert "appnexus" in categories["bid_adapters"]

    def test_ignore_subdirectory_files(self):
        """Test that files in subdirectories are ignored."""
        files = {
            "modules/appnexusBidAdapter.js": "content",
            "modules/subfolder/nestedFile.js": "content",
            "modules/utils/helperFile.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        # Only the root level .js file should be categorized
        total_modules = sum(len(modules) for modules in categories.values())
        assert total_modules == 1
        assert "appnexus" in categories["bid_adapters"]

    def test_parse_output_format(self):
        """Test that parse method produces correctly formatted output."""
        data = {
            "repo": "prebid/Prebid.js",
            "version": "master",
            "directory": "modules",
            "files": {
                "modules/appnexusBidAdapter.js": "content",
                "modules/googleAnalyticsAnalyticsAdapter.js": "content",
                "modules/currency.js": "content",
            },
            "metadata": {"commit_sha": "abc123", "total_files": 3},
        }

        result = self.parser.parse(data)

        assert "Repository: prebid/Prebid.js" in result
        assert "Version: master" in result
        assert "Modules Directory: modules" in result
        assert "Bid Adapters (1):" in result
        assert "Analytics Adapters (1):" in result
        assert "Other Modules (1):" in result
        assert "JSON Output:" in result

        # Check that JSON is valid
        json_start = result.find('{\n  "bid_adapters"')
        json_end = result.rfind("}") + 1
        json_output = result[json_start:json_end]
        parsed_json = json.loads(json_output)

        assert "bid_adapters" in parsed_json
        assert "analytics_adapters" in parsed_json
        assert "other_modules" in parsed_json

    def test_mixed_categories(self):
        """Test with files from all categories."""
        files = {
            "modules/appnexusBidAdapter.js": "content",
            "modules/rubiconBidAdapter.js": "content",
            "modules/googleAnalyticsAnalyticsAdapter.js": "content",
            "modules/amazonRtdProvider.js": "content",
            "modules/facebookIdSystem.js": "content",
            "modules/currency.js": "content",
            "modules/consentManagement.js": "content",
        }

        categories = self.parser._categorize_modules(files)

        assert len(categories["bid_adapters"]) == 2
        assert len(categories["analytics_adapters"]) == 1
        assert len(categories["rtd_modules"]) == 1
        assert len(categories["identity_modules"]) == 1
        assert len(categories["other_modules"]) == 2

        # Verify total count
        total_modules = sum(len(modules) for modules in categories.values())
        assert total_modules == 7
