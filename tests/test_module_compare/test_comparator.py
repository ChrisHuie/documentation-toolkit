"""Tests for module comparator."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import ComparisonMode, ModuleInfo, ComparisonResult


class TestModuleComparator:
    """Test ModuleComparator class."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = Mock()
        client.resolve_version = Mock(
            side_effect=lambda repo, version, **kwargs: version
        )
        return client

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        manager = Mock()
        manager.get_repo_config = Mock(side_effect=self._get_mock_config)
        return manager

    def _get_mock_config(self, repo_key):
        """Return mock repository configurations."""
        configs = {
            "prebid-js": {
                "repo": "prebid/Prebid.js",
                "description": "Prebid.js",
                "parser_type": "prebid_js",
                "fetch_strategy": "filenames_only",
                "paths": {"Bid Adapters": "modules", "Analytics": "modules"},
            },
            "prebid-server": {
                "repo": "prebid/prebid-server",
                "description": "Prebid Server Go",
                "parser_type": "prebid_server_go",
                "fetch_strategy": "directory_names",
                "paths": {"Bid Adapters": "adapters", "Analytics": "analytics"},
            },
        }
        return configs.get(repo_key)

    def test_extract_module_name_prebid_js(
        self, mock_github_client, mock_config_manager
    ):
        """Test module name extraction for Prebid.js."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Test various Prebid.js module types
        assert (
            comparator._extract_module_name("appnexusBidAdapter.js", "prebid_js")
            == "appnexus"
        )
        assert (
            comparator._extract_module_name("googleAnalyticsAdapter.js", "prebid_js")
            == "google"
        )
        assert (
            comparator._extract_module_name("permutiveRtdProvider.js", "prebid_js")
            == "permutive"
        )
        assert (
            comparator._extract_module_name("sharedIdSystem.js", "prebid_js")
            == "shared"
        )
        assert (
            comparator._extract_module_name("someModule.js", "prebid_js")
            == "someModule"
        )

    def test_extract_module_name_other(self, mock_github_client, mock_config_manager):
        """Test module name extraction for other repository types."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Test generic extraction
        assert comparator._extract_module_name("adapter.go", None) == "adapter"
        assert comparator._extract_module_name("module.java", None) == "module"
        assert comparator._extract_module_name("doc.md", None) == "doc"

    def test_compare_versions_same_repo(self, mock_github_client, mock_config_manager):
        """Test comparing versions of the same repository."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Mock fetch_repository_data responses
        source_data = {
            "Bid Adapters": [
                {
                    "name": "appnexusBidAdapter.js",
                    "path": "modules/appnexusBidAdapter.js",
                },
                {
                    "name": "rubiconBidAdapter.js",
                    "path": "modules/rubiconBidAdapter.js",
                },
                {"name": "oldBidAdapter.js", "path": "modules/oldBidAdapter.js"},
            ],
            "Analytics": [
                {
                    "name": "googleAnalyticsAdapter.js",
                    "path": "modules/googleAnalyticsAdapter.js",
                }
            ],
        }

        target_data = {
            "Bid Adapters": [
                {
                    "name": "appnexusBidAdapter.js",
                    "path": "modules/appnexusBidAdapter.js",
                },
                {
                    "name": "rubiconBidAdapter.js",
                    "path": "modules/rubiconBidAdapter.js",
                },
                {"name": "newBidAdapter.js", "path": "modules/newBidAdapter.js"},
            ],
            "Analytics": [
                {
                    "name": "googleAnalyticsAdapter.js",
                    "path": "modules/googleAnalyticsAdapter.js",
                },
                {
                    "name": "adobeAnalyticsAdapter.js",
                    "path": "modules/adobeAnalyticsAdapter.js",
                },
            ],
        }

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_data, target_data]
        )

        # Perform comparison
        result = comparator.compare("prebid-js", "v9.0.0", "prebid-js", "v9.51.0")

        # Verify result
        assert result.comparison_mode == ComparisonMode.VERSION_COMPARISON
        assert result.source_repo == "prebid-js"
        assert result.target_repo == "prebid-js"
        assert result.source_version == "v9.0.0"
        assert result.target_version == "v9.51.0"

        # Check Bid Adapters category
        bid_adapters = result.categories["Bid Adapters"]
        assert len(bid_adapters.added) == 1
        assert bid_adapters.added[0].name == "new"
        assert len(bid_adapters.removed) == 1
        assert bid_adapters.removed[0].name == "old"
        assert len(bid_adapters.unchanged) == 2

        # Check Analytics category
        analytics = result.categories["Analytics"]
        assert len(analytics.added) == 1
        assert analytics.added[0].name == "adobe"
        assert len(analytics.removed) == 0
        assert len(analytics.unchanged) == 1

    def test_compare_different_repos(self, mock_github_client, mock_config_manager):
        """Test comparing different repositories."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Mock fetch_repository_data responses
        js_data = {
            "Bid Adapters": [
                {
                    "name": "appnexusBidAdapter.js",
                    "path": "modules/appnexusBidAdapter.js",
                },
                {
                    "name": "rubiconBidAdapter.js",
                    "path": "modules/rubiconBidAdapter.js",
                },
                {
                    "name": "clientOnlyBidAdapter.js",
                    "path": "modules/clientOnlyBidAdapter.js",
                },
            ]
        }

        server_data = {
            "Bid Adapters": [
                {"name": "appnexus", "path": "adapters/appnexus"},
                {"name": "rubicon", "path": "adapters/rubicon"},
                {"name": "serverOnly", "path": "adapters/serverOnly"},
            ]
        }

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[js_data, server_data]
        )

        # Perform comparison
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-server", "v3.8.0")

        # Verify result
        assert result.comparison_mode == ComparisonMode.REPOSITORY_COMPARISON
        assert result.source_repo == "prebid-js"
        assert result.target_repo == "prebid-server"

        # Check Bid Adapters category
        bid_adapters = result.categories["Bid Adapters"]
        assert len(bid_adapters.only_in_source) == 1
        assert bid_adapters.only_in_source[0].name == "clientOnly"
        assert len(bid_adapters.only_in_target) == 1
        assert bid_adapters.only_in_target[0].name == "serverOnly"
        assert len(bid_adapters.in_both) == 2
        assert any(m.name == "appnexus" for m in bid_adapters.in_both)
        assert any(m.name == "rubicon" for m in bid_adapters.in_both)

    def test_compare_with_progress_callback(
        self, mock_github_client, mock_config_manager
    ):
        """Test comparison with progress callback."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Mock data
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[{"Bid Adapters": []}, {"Bid Adapters": []}]
        )

        # Track progress messages
        progress_messages = []

        def progress_callback(msg):
            progress_messages.append(msg)

        # Perform comparison
        comparator.compare(
            "prebid-js",
            "v9.0.0",
            "prebid-js",
            "v9.51.0",
            progress_callback=progress_callback,
        )

        # Verify progress messages
        assert "Fetching source modules..." in progress_messages
        assert "Fetching target modules..." in progress_messages
        assert "Comparing modules..." in progress_messages

    def test_compare_invalid_repo(self, mock_github_client, mock_config_manager):
        """Test comparison with invalid repository."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Mock config manager to return None for invalid repo
        mock_config_manager.get_repo_config = Mock(return_value=None)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Unknown repository: invalid-repo"):
            comparator.compare("invalid-repo", "v1.0.0", "prebid-js", "v9.51.0")
