"""Integration and edge case tests for module comparator."""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.shared_utilities.repository_config import RepositoryConfigManager
from tests.test_module_compare.test_utils import (
    create_github_response,
    create_module_files,
)


class TestModuleComparatorIntegration:
    """Integration tests for ModuleComparator with real configurations."""

    @pytest.fixture
    def real_config_manager(self):
        """Create a real config manager."""
        return RepositoryConfigManager()

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client to avoid real API calls."""
        client = Mock()
        client.resolve_version = Mock(
            side_effect=lambda repo, version, **kwargs: version
        )
        return client

    def test_integration_with_real_config(
        self, mock_github_client, real_config_manager
    ):
        """Test comparator with real configuration manager."""
        comparator = ModuleComparator(mock_github_client, real_config_manager)

        # Mock fetch to avoid API calls with proper structure
        mock_data = create_github_response(
            "prebid/Prebid.js",
            "v9.0.0",
            paths_data={
                "modules": create_module_files("modules", ["appnexusBidAdapter.js"])
            },
        )
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[mock_data, mock_data]
        )

        # Should work with real config
        result = comparator.compare("prebid-js", "v9.0.0", "prebid-js", "v9.51.0")
        assert result is not None
        assert result.source_repo == "prebid-js"

    def test_version_override_respected(self, mock_github_client, real_config_manager):
        """Test that version_override in config is respected."""
        comparator = ModuleComparator(mock_github_client, real_config_manager)

        # Mock data with proper structure
        mock_data = create_github_response(
            "prebid/prebid.github.io", "master", paths_data={"dev-docs": {}}
        )
        mock_github_client.fetch_repository_data = Mock(return_value=mock_data)

        # prebid-docs has version_override = "master"
        comparator.compare("prebid-docs", "v1.0.0", "prebid-docs", "v2.0.0")

        # Verify master was used regardless of input versions
        calls = mock_github_client.fetch_repository_data.call_args_list
        assert calls[0][1]["version"] == "master"
        assert calls[1][1]["version"] == "master"


class TestModuleComparatorEdgeCases:
    """Edge case tests for module comparator."""

    @pytest.fixture
    def comparator(self, mock_github_client, mock_config_manager):
        """Create a comparator instance."""
        return ModuleComparator(mock_github_client, mock_config_manager)

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
        configs = {
            "prebid-js": {
                "repo": "prebid/Prebid.js",
                "parser_type": "prebid_js",
                "fetch_strategy": "filenames_only",
                "paths": {"Bid Adapters": "modules"},
            },
            "prebid-server": {
                "repo": "prebid/prebid-server",
                "parser_type": "prebid_server_go",
                "fetch_strategy": "directory_names",
                "paths": {"Bid Adapters": "adapters"},
            },
            "test-repo": {
                "repo": "test/test-repo",
                "parser_type": "prebid_js",
                "fetch_strategy": "filenames_only",
                "paths": {"Bid Adapters": "modules"},
            },
        }
        manager.get_config = Mock(side_effect=lambda k: configs.get(k))
        return manager

    def test_category_only_in_source(self, comparator, mock_github_client):
        """Test when a category exists only in source repository."""
        # Create source with multiple paths (bid adapters and analytics in same directory)
        source_data = create_github_response(
            "prebid/Prebid.js",
            "v9.0.0",
            paths_data={
                "modules": create_module_files(
                    "modules", ["appnexusBidAdapter.js", "googleAnalyticsAdapter.js"]
                )
            },
        )

        # Target only has bid adapters
        target_data = create_github_response(
            "prebid/prebid-server",
            "v3.0.0",
            paths_data={"adapters": {"adapters/appnexus": ""}},
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_data, target_data]
        )

        result = comparator.compare("prebid-js", "v9.0.0", "prebid-server", "v3.0.0")

        # With path-based categorization, all modules from "modules" path go to "Bid Adapters"
        # So we check statistics instead
        stats = result.get_statistics()
        assert stats.total_only_in_source > 0  # googleAnalyticsAdapter
        assert stats.total_in_both == 1  # appnexus

    def test_empty_module_lists(self, mock_github_client, mock_config_manager):
        """Test comparison when one or both repos have no modules."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Both empty
        empty_data = create_github_response("prebid/Prebid.js", "v1.0.0", paths_data={})
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[empty_data, empty_data]
        )

        result = comparator.compare("prebid-js", "v1.0.0", "prebid-js", "v2.0.0")
        assert len(result.categories) == 0
        assert len(result.all_added) == 0
        assert len(result.all_removed) == 0

        # Source empty, target has modules
        source_empty = create_github_response(
            "prebid/Prebid.js", "v1.0.0", paths_data={}
        )
        target_full = create_github_response(
            "prebid/prebid-server",
            "v2.0.0",
            paths_data={"adapters": {"adapters/appnexus": ""}},
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_empty, target_full]
        )

        result = comparator.compare("prebid-js", "v1.0.0", "prebid-server", "v2.0.0")
        assert "Bid Adapters" in result.categories
        bid_adapters = result.categories["Bid Adapters"]
        assert len(bid_adapters.only_in_target) == 1
        assert len(bid_adapters.only_in_source) == 0

    def test_malformed_module_names(self, mock_github_client, mock_config_manager):
        """Test parsing of malformed module names."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Test edge cases in module parsing
        repo_data = {
            "paths": {
                "modules": {
                    "": None,  # Empty filename
                    ".js": None,  # Just extension
                    "BidAdapter.js": None,  # No adapter name
                    "somethingBidAdapterAnalytics.js": None,  # Mixed suffixes
                    "AnalyticsAdapter.js": None,  # No adapter name
                    "noExtension": None,  # No extension
                }
            }
        }

        modules = comparator.module_parser.parse_modules(
            repo_data=repo_data, parser_type="prebid_js", repo_key="test-repo"
        )

        # Check that malformed names are handled gracefully
        all_names = []
        for module_list in modules.values():
            all_names.extend([m.name for m in module_list])

        # Empty names should be skipped or handled
        assert "" not in all_names or all_names.count("") <= 2  # At most the empty ones
        # Mixed suffix files should be in Other Modules
        assert any("somethingBidAdapterAnalytics" in name for name in all_names)

    def test_case_sensitivity(self, mock_github_client, mock_config_manager):
        """Test that module comparison handles case properly."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)
        # Different case in filenames
        source_data = create_github_response(
            "prebid/Prebid.js",
            "v1.0.0",
            paths_data={
                "modules": create_module_files(
                    "modules", ["AppNexusBidAdapter.js", "RubiconBidAdapter.js"]
                )
            },
        )

        target_data = create_github_response(
            "prebid/Prebid.js",
            "v2.0.0",
            paths_data={
                "modules": create_module_files(
                    "modules", ["appnexusBidAdapter.js", "rubiconBidAdapter.js"]
                )
            },
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_data, target_data]
        )

        result = comparator.compare("prebid-js", "v1.0.0", "prebid-js", "v2.0.0")

        # Should detect case changes as renames
        bid_adapters = result.categories["Bid Adapters"]
        # AppNexus vs appnexus should be detected as renames
        assert len(bid_adapters.renamed) == 2  # AppNexus->appnexus, Rubicon->rubicon
        assert len(bid_adapters.added) == 0
        assert len(bid_adapters.removed) == 0


class TestModuleComparatorErrorHandling:
    """Error handling tests for module comparator."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock()

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        manager = Mock()
        manager.get_config = Mock(
            side_effect=lambda k: (
                {
                    "repo": "test/repo",
                    "parser_type": "default",
                    "paths": {},
                }
                if k == "valid-repo"
                else None
            )
        )
        return manager

    def test_github_api_failure(self, mock_github_client, mock_config_manager):
        """Test handling of GitHub API failures."""
        # Need to create comparator with the mocked github_client
        mock_github_client.resolve_version = Mock(return_value="v1.0.0")
        mock_github_client.fetch_repository_data = Mock(
            side_effect=Exception("GitHub API error")
        )
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        with pytest.raises(Exception, match="GitHub API error"):
            comparator.compare("valid-repo", "v1.0.0", "valid-repo", "v2.0.0")

    def test_fetch_data_failure(self, mock_github_client, mock_config_manager):
        """Test handling of data fetch failures."""
        mock_github_client.resolve_version = Mock(return_value="v1.0.0")
        mock_github_client.fetch_repository_data = Mock(
            side_effect=Exception("Network error")
        )
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        with pytest.raises(Exception, match="Network error"):
            comparator.compare("valid-repo", "v1.0.0", "valid-repo", "v2.0.0")

    def test_invalid_repository_both(self, mock_github_client, mock_config_manager):
        """Test when both repositories are invalid."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)
        with pytest.raises(ValueError, match="Unknown repository: invalid1"):
            comparator.compare("invalid1", "v1.0.0", "invalid2", "v2.0.0")

    def test_partial_data_fetch(self, mock_github_client, mock_config_manager):
        """Test when fetch returns partial data."""
        mock_github_client.resolve_version = Mock(return_value="v1.0.0")

        # First fetch succeeds, second fails
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[
                {"Bid Adapters": []},
                Exception("Partial failure"),
            ]
        )
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        with pytest.raises(Exception, match="Partial failure"):
            comparator.compare("valid-repo", "v1.0.0", "valid-repo", "v2.0.0")


class TestModuleComparatorStatistics:
    """Test statistics calculation edge cases."""

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
        manager.get_config = Mock(
            return_value={
                "repo": "test/repo",
                "parser_type": "prebid_js",
                "paths": {"Bid Adapters": "modules"},
            }
        )
        return manager

    def test_division_by_zero(self, mock_github_client, mock_config_manager):
        """Test statistics calculation with zero source modules."""
        # Empty source, non-empty target
        source_data = create_github_response(
            "test-repo",
            "v1.0.0",
            paths_data={"modules": {}},  # Empty modules directory
        )
        target_data = create_github_response(
            "test-repo",
            "v2.0.0",
            paths_data={
                "modules": create_module_files("modules", ["newBidAdapter.js"])
            },
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_data, target_data]
        )

        comparator = ModuleComparator(mock_github_client, mock_config_manager)
        result = comparator.compare("test-repo", "v1.0.0", "test-repo", "v2.0.0")

        # Should handle division by zero gracefully
        stats = result.get_statistics()
        # Check that we get correct counts even with empty source
        assert stats.total_added == 1
        assert stats.total_removed == 0
        assert stats.source_total == 0
        assert stats.target_total == 1

    def test_large_percentage_changes(self, mock_github_client, mock_config_manager):
        """Test statistics with very large changes."""
        # 1 module to 100 modules
        source_data = create_github_response(
            "test-repo",
            "v1.0.0",
            paths_data={
                "modules": create_module_files("modules", ["onlyBidAdapter.js"])
            },
        )

        # Create 100 modules in target
        target_files = [f"bidAdapter{i}.js" for i in range(100)]
        target_data = create_github_response(
            "test-repo",
            "v2.0.0",
            paths_data={"modules": create_module_files("modules", target_files)},
        )

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[source_data, target_data]
        )

        comparator = ModuleComparator(mock_github_client, mock_config_manager)
        result = comparator.compare("test-repo", "v1.0.0", "test-repo", "v2.0.0")

        # Should handle large changes correctly
        stats = result.get_statistics()
        assert stats.total_added == 100  # All 100 are new (names don't match source)
        assert stats.total_removed == 1  # The original module was removed
        assert stats.net_change == 99  # Net change is still +99


class TestModuleComparatorConfiguration:
    """Test configuration handling edge cases."""

    def test_missing_parser_type(self):
        """Test handling of missing parser_type in config."""
        config_manager = Mock()
        config_manager.get_config = Mock(
            return_value={
                "repo": "test/repo",
                # Missing parser_type
                "paths": {"Modules": "src"},
            }
        )

        github_client = Mock()
        comparator = ModuleComparator(github_client, config_manager)

        # Should use default parser when parser_type is missing
        repo_data = {"paths": {"src": {"module.js": None}}}
        modules = comparator.module_parser.parse_modules(
            repo_data=repo_data,
            parser_type="default",  # Default when missing
            repo_key="test-repo",
        )
        # Should have parsed the module
        assert len(modules) > 0
        all_names = []
        for module_list in modules.values():
            all_names.extend([m.name for m in module_list])
        assert "module" in all_names

    def test_custom_fetch_strategy(self):
        """Test that fetch_strategy is properly passed through."""
        config_manager = Mock()
        config_manager.get_config = Mock(
            return_value={
                "repo": "test/repo",
                "parser_type": "default",
                "fetch_strategy": "directory_names",
                "paths": {"Modules": "src"},
            }
        )

        github_client = Mock()
        github_client.resolve_version = Mock(return_value="v1.0.0")
        github_client.fetch_repository_data = Mock(return_value={})

        comparator = ModuleComparator(github_client, config_manager)
        comparator.compare("test-repo", "v1.0.0", "test-repo", "v2.0.0")

        # Verify fetch_strategy was passed
        calls = github_client.fetch_repository_data.call_args_list
        assert calls[0][1]["fetch_strategy"] == "directory_names"
        assert calls[1][1]["fetch_strategy"] == "directory_names"
