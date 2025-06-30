"""
Integration tests using real GitHub API response structures.

These tests ensure our module comparison logic works with actual API responses.
"""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import ComparisonMode
from src.shared_utilities.repository_config import RepositoryConfigManager


class TestRealAPIIntegration:
    """Integration tests with real GitHub API response structures."""

    @pytest.fixture
    def real_api_response_prebid_js(self):
        """Create a realistic GitHub API response for Prebid.js."""
        return {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",
            "paths": {
                "modules": {
                    "modules/33acrossBidAdapter.js": "// 33across bid adapter code",
                    "modules/33acrossBidAdapter.md": "# 33across Bid Adapter",
                    "modules/appnexusBidAdapter.js": "// appnexus bid adapter code",
                    "modules/appnexusBidAdapter.md": "# Appnexus Bid Adapter",
                    "modules/rubiconBidAdapter.js": "// rubicon bid adapter code",
                    "modules/googleAnalyticsAdapter.js": "// Google Analytics adapter",
                    "modules/userId/index.js": "// User ID module",
                    "modules/currency.js": "// Currency module",
                    "modules/priceFloors.js": "// Price floors module",
                    "modules/rtdModule/index.js": "// RTD module base",
                    "modules/browsiRtdProvider.js": "// Browsi RTD provider",
                    "modules/identityLinkIdSystem.js": "// Identity Link ID system",
                }
            },
            "files": [],
            "metadata": {
                "commit_sha": "abc123def456",
                "total_files": 12,
                "fetch_strategy": "filenames_only",
            },
        }

    @pytest.fixture
    def real_api_response_prebid_server(self):
        """Create a realistic GitHub API response for Prebid Server."""
        return {
            "repo": "prebid/prebid-server",
            "version": "v3.8.0",
            "paths": {
                "adapters": {
                    "adapters/33across": "",
                    "adapters/appnexus": "",
                    "adapters/rubicon": "",
                    "adapters/pubmatic": "",
                    "adapters/openx": "",
                },
                "analytics": {
                    "analytics/pubstack": "",
                    "analytics/agma": "",
                },
                "modules": {
                    "modules/prebid": "",
                    "modules/fiftyonedegrees/devicedetection": "",
                },
            },
            "files": [],
            "metadata": {
                "commit_sha": "def789ghi012",
                "total_files": 10,
                "fetch_strategy": "directory_names",
            },
        }

    @pytest.fixture
    def real_api_response_empty(self):
        """Create a realistic empty GitHub API response."""
        return {
            "repo": "test/empty-repo",
            "version": "v1.0.0",
            "paths": {},
            "files": [],
            "metadata": {
                "commit_sha": "empty123",
                "total_files": 0,
                "fetch_strategy": "filenames_only",
            },
        }

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = Mock()
        client.resolve_version = Mock(
            side_effect=lambda repo, version, **kwargs: version
        )
        return client

    @pytest.fixture
    def real_config_manager(self):
        """Use the real configuration manager."""
        return RepositoryConfigManager()

    def test_version_comparison_with_real_structure(
        self, mock_github_client, real_config_manager, real_api_response_prebid_js
    ):
        """Test version comparison with real API response structure."""
        # Create v1 response with fewer modules
        v1_response = {
            "repo": "prebid/Prebid.js",
            "version": "v9.0.0",
            "paths": {
                "modules": {
                    "modules/33acrossBidAdapter.js": "",
                    "modules/appnexusBidAdapter.js": "",
                    "modules/rubiconBidAdapter.js": "",
                    "modules/googleAnalyticsAdapter.js": "",
                    "modules/currency.js": "",
                }
            },
            "files": [],
            "metadata": {
                "commit_sha": "v9_commit",
                "total_files": 5,
                "fetch_strategy": "filenames_only",
            },
        }

        # Create v2 response with more modules (v1 modules + new ones)
        v2_response = {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",
            "paths": {
                "modules": {
                    # All v1 modules
                    "modules/33acrossBidAdapter.js": "",
                    "modules/appnexusBidAdapter.js": "",
                    "modules/rubiconBidAdapter.js": "",
                    "modules/googleAnalyticsAdapter.js": "",
                    "modules/currency.js": "",
                    # New modules in v2
                    "modules/browsiRtdProvider.js": "",
                    "modules/identityLinkIdSystem.js": "",
                    "modules/newBidAdapter.js": "",
                    "modules/anotherRtdProvider.js": "",
                }
            },
            "files": [],
            "metadata": {
                "commit_sha": "v9_51_commit",
                "total_files": 9,
                "fetch_strategy": "filenames_only",
            },
        }

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[v1_response, v2_response]
        )

        comparator = ModuleComparator(mock_github_client, real_config_manager)
        result = comparator.compare("prebid-js", "v9.0.0", "prebid-js", "v9.51.0")

        # Verify the comparison worked correctly
        assert result is not None
        assert result.comparison_mode == ComparisonMode.VERSION_COMPARISON
        assert len(result.all_added) == 4  # 2 restored + 2 new
        assert len(result.all_removed) == 0  # We didn't remove any in v2

        # Check specific modules were detected
        added_names = {m.name for m in result.all_added}
        assert "browsi" in added_names  # browsiRtdProvider -> browsi
        assert "identityLink" in added_names  # identityLinkIdSystem -> identityLink
        assert "new" in added_names  # newBidAdapter -> new
        assert "another" in added_names  # anotherRtdProvider -> another

    def test_cross_repo_comparison_with_real_structure(
        self,
        mock_github_client,
        real_config_manager,
        real_api_response_prebid_js,
        real_api_response_prebid_server,
    ):
        """Test cross-repository comparison with real API structures."""
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[real_api_response_prebid_js, real_api_response_prebid_server]
        )

        comparator = ModuleComparator(mock_github_client, real_config_manager)
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-server", "v3.8.0")

        # Verify cross-repo comparison
        assert result is not None
        assert result.comparison_mode == ComparisonMode.REPOSITORY_COMPARISON

        # Check categories exist
        assert "Bid Adapters" in result.categories

        # Check some expected differences
        bid_adapters = result.categories["Bid Adapters"]

        # Common adapters (in both)
        common_names = {m.name for m in bid_adapters.in_both}
        assert "33across" in common_names
        assert "appnexus" in common_names
        assert "rubicon" in common_names

        # Only in prebid-server
        server_only = {m.name for m in bid_adapters.only_in_target}
        assert "pubmatic" in server_only
        assert "openx" in server_only

    def test_empty_repository_comparison(
        self,
        mock_github_client,
        real_config_manager,
        real_api_response_prebid_js,
        real_api_response_empty,
    ):
        """Test comparison with empty repository."""
        mock_github_client.fetch_repository_data = Mock(
            side_effect=[real_api_response_prebid_js, real_api_response_empty]
        )

        comparator = ModuleComparator(mock_github_client, real_config_manager)
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-js", "v1.0.0")

        # All modules should be removed (empty target)
        assert len(result.all_removed) > 0
        assert len(result.all_added) == 0

        stats = result.get_statistics()
        assert stats.total_removed == stats.source_total
        assert stats.target_total == 0

    def test_parser_type_extraction_with_real_data(
        self, mock_github_client, real_config_manager, real_api_response_prebid_js
    ):
        """Test that parser types correctly extract module names from real data."""
        mock_github_client.fetch_repository_data = Mock(
            return_value=real_api_response_prebid_js
        )

        comparator = ModuleComparator(mock_github_client, real_config_manager)

        # Parse the real data
        modules = comparator.module_parser.parse_modules(
            repo_data=real_api_response_prebid_js,
            parser_type="prebid_js",
            repo_key="prebid-js",
        )

        # Check that modules were correctly parsed
        bid_adapter_names = [m.name for m in modules.get("Bid Adapters", [])]
        analytics_names = [m.name for m in modules.get("Analytics Adapters", [])]
        id_system_names = [m.name for m in modules.get("User ID Modules", [])]
        rtd_names = [m.name for m in modules.get("Real-Time Data Modules", [])]

        # Test that expected modules are in the right categories
        assert "33across" in bid_adapter_names
        assert "google" in analytics_names
        assert "identityLink" in id_system_names
        assert "browsi" in rtd_names

    def test_malformed_api_response_handling(
        self, mock_github_client, real_config_manager
    ):
        """Test handling of malformed API responses."""
        # Missing required fields
        malformed_response = {
            "repo": "test/repo",
            # Missing version, paths, files, metadata
        }

        mock_github_client.fetch_repository_data = Mock(return_value=malformed_response)

        comparator = ModuleComparator(mock_github_client, real_config_manager)

        # Should handle gracefully - the code logs a warning but doesn't raise
        result = comparator.compare("prebid-js", "v1.0.0", "prebid-js", "v2.0.0")

        # With malformed data, we should get an empty comparison
        assert result is not None
        assert len(result.categories) == 0

    def test_mixed_content_in_paths(self, mock_github_client, real_config_manager):
        """Test handling of mixed content types in the same path."""
        response = {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",
            "paths": {
                "modules": {
                    # Mix of different file types
                    "modules/appnexusBidAdapter.js": "",
                    "modules/appnexusBidAdapter.md": "",  # Documentation
                    "modules/test/appnexusBidAdapter_spec.js": "",  # Test file
                    "modules/.gitignore": "",  # Git file
                    "modules/README.md": "",  # README
                    "modules/package.json": "",  # Package file
                }
            },
            "files": [],
            "metadata": {"commit_sha": "test123", "total_files": 6},
        }

        mock_github_client.fetch_repository_data = Mock(
            side_effect=[response, response]
        )

        comparator = ModuleComparator(mock_github_client, real_config_manager)
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-js", "v9.51.0")

        # Should only extract actual module files
        all_modules = []
        for category in result.categories.values():
            all_modules.extend(category.unchanged)

        module_names = {m.name for m in all_modules}

        # Should have extracted appnexus from the .js file
        assert "appnexus" in module_names

        # Should not include test files, docs, or config files
        assert not any("test" in name for name in module_names)
        # README.md and .gitignore are extracted as "README" and "" (empty) respectively
        # but the parser filters them out
        assert "gitignore" not in module_names
        assert "package" not in module_names

    def test_large_repository_performance(
        self, mock_github_client, real_config_manager
    ):
        """Test performance with large number of modules."""
        # Create a response with 1000 modules
        large_response = {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",
            "paths": {
                "modules": {f"modules/adapter{i}BidAdapter.js": "" for i in range(1000)}
            },
            "files": [],
            "metadata": {"commit_sha": "perf123", "total_files": 1000},
        }

        mock_github_client.fetch_repository_data = Mock(return_value=large_response)

        comparator = ModuleComparator(mock_github_client, real_config_manager)

        # Should complete without issues
        result = comparator.compare("prebid-js", "v9.51.0", "prebid-js", "v9.51.0")

        assert result is not None
        total_modules = sum(len(cat.unchanged) for cat in result.categories.values())
        assert total_modules == 1000
