"""Tests for cumulative comparison functionality."""

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import (
    ComparisonMode,
    CumulativeComparisonResult,
    CumulativeModuleChange,
    ModuleInfo,
)
from src.shared_utilities.github_client import GitHubClient
from src.shared_utilities.repository_config import RepositoryConfigManager
from src.shared_utilities.version_cache import (
    MajorVersionInfo,
    RepoVersionCache,
)


class TestCumulativeComparison:
    """Test cumulative comparison logic."""

    def test_cumulative_flag_defaults(self):
        """Test that cumulative defaults correctly based on comparison type."""
        # Same repo should default to cumulative
        from src.module_compare.main import parse_repo_version

        source_repo, source_version = parse_repo_version("prebid-js:v9.0.0")
        target_repo, target_version = parse_repo_version("prebid-js:v9.5.0")

        is_same_repo = source_repo == target_repo
        assert is_same_repo is True

        # Default cumulative should be True for same repo
        cumulative = None
        use_cumulative = cumulative if cumulative is not None else is_same_repo
        assert use_cumulative is True

        # Different repos should not use cumulative
        source_repo2, _ = parse_repo_version("prebid-js:v9.0.0")
        target_repo2, _ = parse_repo_version("prebid-server:v3.0.0")

        is_same_repo2 = source_repo2 == target_repo2
        assert is_same_repo2 is False

        use_cumulative2 = cumulative if cumulative is not None else is_same_repo2
        assert use_cumulative2 is False

    def test_cumulative_module_change(self):
        """Test CumulativeModuleChange data model."""
        module = ModuleInfo(
            name="testAdapter",
            path="modules/testAdapterBidAdapter.js",
            category="Bid Adapters",
            repo="prebid-js",
        )

        # Module added and still present
        change1 = CumulativeModuleChange(
            module=module,
            added_in_version="v9.1.0",
            removed_in_version=None,
            is_present_in_target=True,
        )

        assert not change1.was_removed
        assert not change1.is_transient

        # Module added and then removed
        change2 = CumulativeModuleChange(
            module=module,
            added_in_version="v9.1.0",
            removed_in_version="v9.3.0",
            is_present_in_target=False,
        )

        assert change2.was_removed
        assert change2.is_transient

    def test_cumulative_comparison_result(self):
        """Test CumulativeComparisonResult methods."""
        result = CumulativeComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.5.0",
            comparison_mode=ComparisonMode.CUMULATIVE_COMPARISON,
            cumulative_changes={},
            versions_analyzed=[
                "v9.0.0",
                "v9.1.0",
                "v9.2.0",
                "v9.3.0",
                "v9.4.0",
                "v9.5.0",
            ],
        )

        # Add some test changes
        module1 = ModuleInfo(
            name="adapter1",
            path="modules/adapter1BidAdapter.js",
            category="Bid Adapters",
            repo="prebid-js",
        )
        module2 = ModuleInfo(
            name="adapter2",
            path="modules/adapter2BidAdapter.js",
            category="Bid Adapters",
            repo="prebid-js",
        )

        change1 = CumulativeModuleChange(
            module=module1,
            added_in_version="v9.1.0",
            removed_in_version=None,
            is_present_in_target=True,
        )

        change2 = CumulativeModuleChange(
            module=module2,
            added_in_version="v9.2.0",
            removed_in_version="v9.4.0",
            is_present_in_target=False,
        )

        result.cumulative_changes["Bid Adapters"] = [change1, change2]

        # Test properties
        assert len(result.all_added_modules) == 2
        assert len(result.permanently_added_modules) == 1
        assert len(result.transient_modules) == 1
        assert len(result.removed_modules) == 1

        assert result.permanently_added_modules[0].module.name == "adapter1"
        assert result.transient_modules[0].module.name == "adapter2"

    def test_cumulative_comparison_with_mock_data(self):
        """Test cumulative comparison with mocked GitHub client."""
        from unittest.mock import Mock, patch

        # Mock GitHub client
        github_client = Mock(spec=GitHubClient)
        config_manager = Mock(spec=RepositoryConfigManager)

        # Mock config
        config_manager.get_config.return_value = {
            "repo": "prebid/Prebid.js",
            "description": "Prebid.js",
            "parser_type": "prebid_js",
            "fetch_strategy": "filenames_only",
            "paths": {"modules": "modules"},
        }

        # Mock version cache
        version_cache = RepoVersionCache(
            repo_name="prebid/Prebid.js",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(
                    major=9, first_version="9.0.0", last_version="9.5.0"
                )
            },
            latest_versions=[
                "9.5.0",
                "9.2.0",
                "9.1.0",
                "9.0.0",
            ],  # Only versions we'll actually fetch
        )

        # Mock modules for different versions
        modules_v900 = {
            "Bid Adapters": [
                ModuleInfo(
                    "existingAdapter",
                    "modules/existingAdapterBidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                )
            ]
        }

        modules_v910 = {
            "Bid Adapters": [
                ModuleInfo(
                    "existingAdapter",
                    "modules/existingAdapterBidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
                ModuleInfo(
                    "newAdapter1",
                    "modules/newAdapter1BidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
            ]
        }

        modules_v920 = {
            "Bid Adapters": [
                ModuleInfo(
                    "existingAdapter",
                    "modules/existingAdapterBidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
                ModuleInfo(
                    "newAdapter1",
                    "modules/newAdapter1BidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
                ModuleInfo(
                    "newAdapter2",
                    "modules/newAdapter2BidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
            ]
        }

        modules_v950 = {
            "Bid Adapters": [
                ModuleInfo(
                    "existingAdapter",
                    "modules/existingAdapterBidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
                ModuleInfo(
                    "newAdapter1",
                    "modules/newAdapter1BidAdapter.js",
                    "Bid Adapters",
                    "prebid-js",
                ),
                # newAdapter2 was removed
            ]
        }

        comparator = ModuleComparator(github_client, config_manager)

        with patch.object(
            comparator.version_cache, "load_cache", return_value=version_cache
        ):
            with patch.object(comparator, "_fetch_modules") as mock_fetch:
                # Set up fetch returns
                def fetch_side_effect(repo, version):
                    if version in ["v9.0.0", "9.0.0"]:
                        return modules_v900
                    elif version in ["v9.1.0", "9.1.0"]:
                        return modules_v910
                    elif version in ["v9.2.0", "9.2.0"]:
                        return modules_v920
                    elif version in ["v9.5.0", "9.5.0"]:
                        return modules_v950
                    else:
                        return {}

                mock_fetch.side_effect = fetch_side_effect

                # Run cumulative comparison
                result = comparator.compare(
                    "prebid-js", "v9.0.0", "prebid-js", "v9.5.0", cumulative=True
                )

                assert isinstance(result, CumulativeComparisonResult)
                assert result.comparison_mode == ComparisonMode.CUMULATIVE_COMPARISON

                # Check we have the right versions analyzed
                assert "v9.0.0" in result.versions_analyzed
                assert "v9.5.0" in result.versions_analyzed

                # Check cumulative changes
                changes = result.cumulative_changes.get("Bid Adapters", [])
                adapter_names = [c.module.name for c in changes]

                # Debug: Print what we got
                print(f"Versions analyzed: {result.versions_analyzed}")
                print(f"Adapter names found: {adapter_names}")
                print(f"Number of changes: {len(changes)}")
                for change in changes:
                    print(
                        f"  {change.module.name}: added={change.added_in_version}, removed={change.removed_in_version}, present={change.is_present_in_target}"
                    )

                # The test should find modules that were added between v9.0.0 and v9.5.0
                # existingAdapter was already in v9.0.0, so it shouldn't be in cumulative changes
                # newAdapter1 was added and is still present
                # newAdapter2 was added and then removed

                # We should find both newAdapter1 and newAdapter2
                assert len(changes) == 2
                assert "newAdapter1" in adapter_names
                assert "newAdapter2" in adapter_names

                # Check newAdapter1 is permanently added
                newAdapter1_change = next(
                    c for c in changes if c.module.name == "newAdapter1"
                )
                assert newAdapter1_change.is_present_in_target
                assert not newAdapter1_change.was_removed
                assert (
                    newAdapter1_change.added_in_version == "9.1.0"
                )  # Version without 'v'

                # Check newAdapter2 is transient (added then removed)
                newAdapter2_change = next(
                    c for c in changes if c.module.name == "newAdapter2"
                )
                assert not newAdapter2_change.is_present_in_target
                assert newAdapter2_change.was_removed
                assert (
                    newAdapter2_change.added_in_version == "9.2.0"
                )  # Version without 'v'
                assert (
                    newAdapter2_change.removed_in_version == "9.5.0"
                )  # Version without 'v'

    def test_cumulative_output_formatting(self):
        """Test formatting of cumulative comparison results."""
        from src.module_compare.output_formatter import ModuleCompareOutputFormatter

        result = CumulativeComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.5.0",
            comparison_mode=ComparisonMode.CUMULATIVE_COMPARISON,
            cumulative_changes={
                "Bid Adapters": [
                    CumulativeModuleChange(
                        module=ModuleInfo(
                            "adapter1", "path1", "Bid Adapters", "prebid-js"
                        ),
                        added_in_version="v9.1.0",
                        removed_in_version=None,
                        is_present_in_target=True,
                    ),
                    CumulativeModuleChange(
                        module=ModuleInfo(
                            "adapter2", "path2", "Bid Adapters", "prebid-js"
                        ),
                        added_in_version="v9.2.0",
                        removed_in_version="v9.4.0",
                        is_present_in_target=False,
                    ),
                ]
            },
            versions_analyzed=[
                "v9.0.0",
                "v9.1.0",
                "v9.2.0",
                "v9.3.0",
                "v9.4.0",
                "v9.5.0",
            ],
        )

        formatter = ModuleCompareOutputFormatter()
        output = formatter.format_output(result, "table")

        # Check output contains key information
        assert "Cumulative Module Comparison" in output
        assert "v9.0.0 → v9.5.0" in output
        assert "Total Changes: 2" in output
        assert "Permanently Added: 1" in output
        assert "Removed: 1" in output
        assert "Versions Analyzed: 6" in output
        assert "adapter1 (added in v9.1.0)" in output
        assert "adapter2 (added: v9.2.0, removed: v9.4.0)" in output
