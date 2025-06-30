"""Tests for module comparator."""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import ComparisonMode

from .test_utils import create_github_response, create_module_files


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
        manager.get_config = Mock(side_effect=self._get_mock_config)
        manager.is_configured = Mock(return_value=True)
        return manager

    def _get_mock_config(self, repo_key):
        """Return mock repository configurations."""
        configs = {
            "prebid-js": {
                "repo": "prebid/Prebid.js",
                "description": "Prebid.js",
                "parser_type": "prebid_js",
                "fetch_strategy": "filenames_only",
                "paths": {
                    "Bid Adapters": "modules"
                },  # Single path, categorized by filename
            },
            "prebid-server": {
                "repo": "prebid/prebid-server",
                "description": "Prebid Server Go",
                "parser_type": "prebid_server_go",
                "fetch_strategy": "directory_names",
                "paths": {"Bid Adapters": "adapters"},  # Only bid adapters path
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

        # Create proper GitHub API responses
        source_files = [
            "appnexusBidAdapter.js",
            "rubiconBidAdapter.js",
            "oldBidAdapter.js",
            "googleAnalyticsAdapter.js",
        ]

        target_files = [
            "appnexusBidAdapter.js",
            "rubiconBidAdapter.js",
            "newBidAdapter.js",
            "googleAnalyticsAdapter.js",
            "adobeAnalyticsAdapter.js",
        ]

        source_data = create_github_response(
            "prebid/Prebid.js",
            "v9.0.0",
            paths_data={"modules": create_module_files("modules", source_files)},
        )

        target_data = create_github_response(
            "prebid/Prebid.js",
            "v9.51.0",
            paths_data={"modules": create_module_files("modules", target_files)},
        )

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

        # Since all files are in "modules" path, they'll be categorized based on the config
        # The mock config should map "modules" to "Bid Adapters"
        categories = result.categories

        # All modules should be in one category (based on path mapping)
        assert len(categories) > 0

        # Get statistics to verify the changes
        stats = result.get_statistics()
        assert stats.total_added == 2  # newBidAdapter and adobeAnalyticsAdapter
        assert stats.total_removed == 1  # oldBidAdapter
        assert stats.total_unchanged == 3  # appnexus, rubicon, googleAnalytics

    def test_compare_different_repos(self, mock_github_client, mock_config_manager):
        """Test comparing different repositories."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Create proper GitHub API responses for different repository types
        js_files = [
            "appnexusBidAdapter.js",
            "rubiconBidAdapter.js",
            "clientOnlyBidAdapter.js",
        ]

        server_adapters = [
            "appnexus",
            "rubicon",
            "serverOnly",
        ]

        js_data = create_github_response(
            "prebid/Prebid.js",
            "v9.51.0",
            paths_data={"modules": create_module_files("modules", js_files)},
        )

        # Prebid Server uses directory structure
        server_data = create_github_response(
            "prebid/prebid-server",
            "v3.8.0",
            paths_data={
                "adapters": {f"adapters/{name}": "" for name in server_adapters}
            },
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[js_data, server_data]
        )

        # Perform comparison
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-server", "v3.8.0")

        # Verify result
        assert result.comparison_mode == ComparisonMode.REPOSITORY_COMPARISON
        assert result.source_repo == "prebid-js"
        assert result.target_repo == "prebid-server"

        # Get statistics to verify the comparison
        stats = result.get_statistics()
        assert (
            stats.total_only_in_source == 1
        )  # clientOnly (name extracted from clientOnlyBidAdapter.js)
        assert stats.total_only_in_target == 1  # serverOnly
        assert stats.total_in_both == 2  # appnexus and rubicon match between repos

    def test_compare_with_progress_callback(
        self, mock_github_client, mock_config_manager
    ):
        """Test comparison with progress callback."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Mock empty data
        empty_data = create_github_response("prebid/Prebid.js", "v9.0.0", paths_data={})
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[empty_data, empty_data]
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
        mock_config_manager.get_config = Mock(return_value=None)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Unknown repository: invalid-repo"):
            comparator.compare("invalid-repo", "v1.0.0", "prebid-js", "v9.51.0")
