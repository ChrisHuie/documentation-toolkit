"""Tests for module comparator."""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import ComparisonMode, ModuleInfo

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

    def test_module_parser_integration(self, mock_github_client, mock_config_manager):
        """Test that the comparator correctly uses the module parser."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Test that module parser is initialized
        assert comparator.module_parser is not None

        # Test parsing a simple module structure
        repo_data = {
            "paths": {
                "modules": {
                    "appnexusBidAdapter.js": None,
                    "googleAnalyticsAdapter.js": None,
                    "permutiveRtdProvider.js": None,
                    "sharedIdSystem.js": None,
                    "someModule.js": None,
                }
            }
        }

        modules = comparator.module_parser.parse_modules(
            repo_data=repo_data, parser_type="prebid_js", repo_key="test-repo"
        )

        # Verify parsed modules
        assert "Bid Adapters" in modules
        assert "Analytics Adapters" in modules
        assert "Real-Time Data Modules" in modules
        assert "User ID Modules" in modules
        assert "Other Modules" in modules

        # Check specific modules
        bid_adapter_names = [m.name for m in modules["Bid Adapters"]]
        assert "appnexus" in bid_adapter_names

        analytics_names = [m.name for m in modules["Analytics Adapters"]]
        assert "google" in analytics_names

        rtd_module_names = [m.name for m in modules["Real-Time Data Modules"]]
        assert "permutive" in rtd_module_names

        id_module_names = [m.name for m in modules["User ID Modules"]]
        assert "shared" in id_module_names

        other_module_names = [m.name for m in modules["Other Modules"]]
        assert "someModule" in other_module_names

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

    def test_rename_detection_git_history(
        self, mock_github_client, mock_config_manager
    ):
        """Test rename detection using git history."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        # Test modules that should be detected as renames
        removed_modules = [
            ModuleInfo(
                name="imds",
                path="modules/imdsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="gothamads",
                path="modules/gothamadsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added_modules = [
            ModuleInfo(
                name="advertising",
                path="modules/advertisingBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="intenze",
                path="modules/intenzeBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed_modules, added_modules
        )

        # Should detect both as renames from git history
        assert len(renames) == 2
        assert len(remaining_removed) == 0
        assert len(remaining_added) == 0

        # Check specific renames
        rename_map = {r.old_module.name: r for r in renames}
        assert "imds" in rename_map
        assert rename_map["imds"].new_module.name == "advertising"
        assert rename_map["imds"].detection_method == "git_history"
        assert rename_map["imds"].similarity_score == 1.0

        assert "gothamads" in rename_map
        assert rename_map["gothamads"].new_module.name == "intenze"
        assert rename_map["gothamads"].detection_method == "git_history"

    def test_rename_detection_case_change(
        self, mock_github_client, mock_config_manager
    ):
        """Test rename detection for case changes."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        removed_modules = [
            ModuleInfo(
                name="cadentApertureMX",
                path="modules/cadentApertureMXBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="epomDsp",
                path="modules/epomDspBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added_modules = [
            ModuleInfo(
                name="cadent_aperture_mx",
                path="modules/cadent_aperture_mxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="epom_dsp",
                path="modules/epom_dspBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed_modules, added_modules)

        assert len(renames) == 2
        for rename in renames:
            assert rename.detection_method == "case_change"
            assert rename.similarity_score == 0.95

    def test_rename_detection_abbreviation(
        self, mock_github_client, mock_config_manager
    ):
        """Test rename detection for abbreviations."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        removed_modules = [
            ModuleInfo(
                name="incrx",
                path="modules/incrxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="rads",
                path="modules/radsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added_modules = [
            ModuleInfo(
                name="incrementx",
                path="modules/incrementxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="sonarads",
                path="modules/sonaradsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed_modules, added_modules)

        assert len(renames) == 2
        rename_map = {r.old_module.name: r for r in renames}

        # incrx -> incrementx should be detected as abbreviation
        assert "incrx" in rename_map
        assert rename_map["incrx"].new_module.name == "incrementx"
        assert rename_map["incrx"].detection_method == "abbreviation"

    def test_rename_detection_no_match(self, mock_github_client, mock_config_manager):
        """Test rename detection when modules don't match."""
        comparator = ModuleComparator(mock_github_client, mock_config_manager)

        removed_modules = [
            ModuleInfo(
                name="completely",
                path="modules/completelyBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added_modules = [
            ModuleInfo(
                name="different",
                path="modules/differentBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed_modules, added_modules
        )

        # Should not detect any renames
        assert len(renames) == 0
        assert len(remaining_removed) == 1
        assert len(remaining_added) == 1
