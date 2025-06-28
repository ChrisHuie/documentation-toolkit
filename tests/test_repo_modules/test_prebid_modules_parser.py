"""
Tests for PrebidJSParser functionality
"""

import json
import unittest.mock

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

    def test_should_use_metadata_version_detection(self):
        """Test version detection for metadata usage."""
        # Test v10.0+ versions should use metadata
        assert self.parser._should_use_metadata("v10.0.0") is True
        assert self.parser._should_use_metadata("10.0.0") is True
        assert self.parser._should_use_metadata("v10.1.0") is True
        assert self.parser._should_use_metadata("v11.0.0") is True
        assert self.parser._should_use_metadata("master") is True
        assert self.parser._should_use_metadata("main") is True

        # Test versions before v10.0 should not use metadata
        assert self.parser._should_use_metadata("v9.51.0") is False
        assert self.parser._should_use_metadata("9.51.0") is False
        assert self.parser._should_use_metadata("v8.0.0") is False
        assert self.parser._should_use_metadata("v1.0.0") is False

        # Test invalid versions
        assert self.parser._should_use_metadata("invalid") is False
        assert self.parser._should_use_metadata("") is False

    def test_parse_from_metadata_mock(self):
        """Test metadata parsing with mock data."""

        # Mock metadata response
        mock_metadata = {
            "NOTICE": "auto-generated",
            "components": [
                {
                    "componentType": "bidder",
                    "componentName": "appnexus",
                    "aliasOf": None,
                    "gvlid": 32,
                    "disclosureURL": None,
                },
                {
                    "componentType": "bidder",
                    "componentName": "appnexus_alias",
                    "aliasOf": "appnexus",
                    "gvlid": None,
                    "disclosureURL": None,
                },
                {
                    "componentType": "analytics",
                    "componentName": "googleAnalytics",
                    "aliasOf": None,
                    "gvlid": None,
                    "disclosureURL": None,
                },
                {
                    "componentType": "rtd",
                    "componentName": "amazon",
                    "aliasOf": None,
                    "gvlid": None,
                    "disclosureURL": None,
                },
                {
                    "componentType": "userId",
                    "componentName": "facebookId",
                    "aliasOf": None,
                    "gvlid": None,
                    "disclosureURL": None,
                },
            ],
        }

        data = {
            "repo": "prebid/Prebid.js",
            "version": "v10.0.0",
            "directory": "modules",
            "files": {},
        }

        with unittest.mock.patch("requests.get") as mock_get:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_metadata
            mock_get.return_value = mock_response

            categories = self.parser._parse_from_metadata(data)

            # Verify categories were parsed correctly
            assert "appnexus" in categories["bid_adapters"]
            assert (
                "appnexus_alias" not in categories["bid_adapters"]
            )  # Aliases excluded
            assert "googleAnalytics" in categories["analytics_adapters"]
            assert "amazon" in categories["rtd_modules"]
            assert "facebookId" in categories["identity_modules"]

            # Verify the correct URL was called
            expected_url = "https://raw.githubusercontent.com/prebid/Prebid.js/v10.0.0/metadata/modules.json"
            mock_get.assert_called_once_with(expected_url, timeout=30)

    def test_parse_from_metadata_fallback_on_error(self):
        """Test fallback to traditional parsing when metadata fails."""

        data = {
            "repo": "prebid/Prebid.js",
            "version": "v10.0.0",
            "directory": "modules",
            "files": {
                "modules/appnexusBidAdapter.js": "content",
            },
        }

        with unittest.mock.patch("requests.get") as mock_get:
            # Simulate network error
            mock_get.side_effect = Exception("Network error")

            categories = self.parser._parse_from_metadata(data)

            # Should fall back to traditional parsing
            assert "appnexus" in categories["bid_adapters"]

    def test_parse_from_metadata_fallback_on_404(self):
        """Test fallback to traditional parsing when metadata is not found."""

        data = {
            "repo": "prebid/Prebid.js",
            "version": "v10.0.0",
            "directory": "modules",
            "files": {
                "modules/rubiconBidAdapter.js": "content",
            },
        }

        with unittest.mock.patch("requests.get") as mock_get:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            categories = self.parser._parse_from_metadata(data)

            # Should fall back to traditional parsing
            assert "rubicon" in categories["bid_adapters"]

    def test_parse_uses_metadata_for_v10(self):
        """Test that parse method uses metadata for v10.0+ versions."""

        mock_metadata = {
            "components": [
                {
                    "componentType": "bidder",
                    "componentName": "metadata_adapter",
                    "aliasOf": None,
                    "gvlid": 123,
                    "disclosureURL": None,
                }
            ]
        }

        data = {
            "repo": "prebid/Prebid.js",
            "version": "v10.0.0",
            "directory": "modules",
            "files": {
                "modules/traditional_adapter.js": "content",  # This should be ignored for v10+
            },
            "metadata": {"total_files": 1},
        }

        with unittest.mock.patch("requests.get") as mock_get:
            mock_response = unittest.mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_metadata
            mock_get.return_value = mock_response

            result = self.parser.parse(data)

            # Should use metadata, not traditional parsing
            assert "metadata_adapter" in result
            assert "traditional_adapter" not in result

    def test_parse_uses_traditional_for_v9(self):
        """Test that parse method uses traditional parsing for v9.x versions."""
        data = {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",
            "directory": "modules",
            "files": {
                "modules/traditionalBidAdapter.js": "content",
            },
            "metadata": {"total_files": 1},
        }

        result = self.parser.parse(data)

        # Should use traditional parsing for v9.x
        assert "traditional" in result
