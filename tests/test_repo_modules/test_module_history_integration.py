"""
Integration tests for module history functionality with mocked GitHub responses.
"""

import tempfile
from unittest.mock import patch

import pytest

from src.repo_modules.module_history import ModuleHistoryTracker
from src.repo_modules.version_cache import MajorVersionInfo, RepoVersionCache


class TestModuleHistoryIntegration:
    """Integration tests for module history analysis."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_version_cache(self):
        """Create comprehensive mock version cache."""
        return RepoVersionCache(
            repo_name="prebid/Prebid.js",
            default_branch="master",
            major_versions={
                0: MajorVersionInfo(
                    major=0, first_version="0.1.1", last_version="0.34.22"
                ),
                1: MajorVersionInfo(
                    major=1, first_version="1.0.0", last_version="1.40.0"
                ),
                2: MajorVersionInfo(
                    major=2, first_version="2.0.0", last_version="2.44.7"
                ),
                3: MajorVersionInfo(
                    major=3, first_version="3.0.0", last_version="3.27.1"
                ),
                4: MajorVersionInfo(
                    major=4, first_version="4.0.0", last_version="4.43.4"
                ),
            },
            latest_versions=["4.43.4", "4.43.3", "4.43.2", "4.43.1", "4.43.0"],
        )

    @pytest.fixture
    def mock_github_responses(self):
        """Mock GitHub API responses for different versions."""
        return {
            "0.1.1": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus adapter v0.1.1",
                    "modules/rubiconBidAdapter.js": "// Rubicon adapter v0.1.1",
                },
                "metadata": {"total_files": 2},
            },
            "1.0.0": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus adapter v1.0.0",
                    "modules/rubiconBidAdapter.js": "// Rubicon adapter v1.0.0",
                    "modules/pubmaticBidAdapter.js": "// PubMatic adapter v1.0.0",
                    "modules/gaAnalyticsAdapter.js": "// Google Analytics adapter v1.0.0",
                },
                "metadata": {"total_files": 4},
            },
            "2.0.0": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus adapter v2.0.0",
                    "modules/rubiconBidAdapter.js": "// Rubicon adapter v2.0.0",
                    "modules/pubmaticBidAdapter.js": "// PubMatic adapter v2.0.0",
                    "modules/gaAnalyticsAdapter.js": "// Google Analytics adapter v2.0.0",
                    "modules/33acrossBidAdapter.js": "// 33Across adapter v2.0.0",
                    "modules/adagioAnalyticsAdapter.js": "// Adagio analytics v2.0.0",
                    "modules/rtdModule.js": "// RTD module v2.0.0",
                },
                "metadata": {"total_files": 7},
            },
            "3.0.0": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus adapter v3.0.0",
                    "modules/rubiconBidAdapter.js": "// Rubicon adapter v3.0.0",
                    "modules/pubmaticBidAdapter.js": "// PubMatic adapter v3.0.0",
                    "modules/gaAnalyticsAdapter.js": "// Google Analytics adapter v3.0.0",
                    "modules/33acrossBidAdapter.js": "// 33Across adapter v3.0.0",
                    "modules/adagioAnalyticsAdapter.js": "// Adagio analytics v3.0.0",
                    "modules/rtdModule.js": "// RTD module v3.0.0",
                    "modules/unifiedIdSystem.js": "// Unified ID system v3.0.0",
                    "modules/amazonBidAdapter.js": "// Amazon adapter v3.0.0",
                },
                "metadata": {"total_files": 9},
            },
            "4.0.0": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus adapter v4.0.0",
                    "modules/rubiconBidAdapter.js": "// Rubicon adapter v4.0.0",
                    "modules/pubmaticBidAdapter.js": "// PubMatic adapter v4.0.0",
                    "modules/gaAnalyticsAdapter.js": "// Google Analytics adapter v4.0.0",
                    "modules/33acrossBidAdapter.js": "// 33Across adapter v4.0.0",
                    "modules/adagioAnalyticsAdapter.js": "// Adagio analytics v4.0.0",
                    "modules/rtdModule.js": "// RTD module v4.0.0",
                    "modules/unifiedIdSystem.js": "// Unified ID system v4.0.0",
                    "modules/amazonBidAdapter.js": "// Amazon adapter v4.0.0",
                    "modules/criteoRtdProvider.js": "// Criteo RTD v4.0.0",
                    "modules/id5IdSystem.js": "// ID5 ID system v4.0.0",
                },
                "metadata": {"total_files": 11},
            },
        }

    def mock_fetch_repository_data(self, responses):
        """Create a mock fetch_repository_data function."""

        def _fetch(
            repo_name, version, directory, fetch_strategy="filenames_only", **kwargs
        ):
            if version in responses:
                response_data = responses[version].copy()
                response_data.update(
                    {"repo": repo_name, "version": version, "directory": directory}
                )
                return response_data
            return {"files": {}, "metadata": {"total_files": 0}}

        return _fetch

    @patch("time.sleep")  # Speed up tests by skipping rate limiting
    def test_full_module_history_analysis(
        self, mock_sleep, temp_cache_dir, mock_version_cache, mock_github_responses
    ):
        """Test complete module history analysis with realistic data."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
        ):
            # Setup mocks
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(
                mock_github_responses
            )

            # Run analysis
            result = tracker.analyze_module_history(
                "prebid/Prebid.js", force_refresh=True
            )

            # Verify results structure
            assert result.repo_name == "prebid/Prebid.js"
            assert result.last_analyzed_version == "4.43.4"
            assert len(result.modules) > 0

            # Verify specific module introductions
            modules = result.modules

            # Modules introduced in v0.1.1
            assert "appnexus" in modules
            assert modules["appnexus"].first_version == "0.1.1"
            assert modules["appnexus"].first_major_version == 0
            assert modules["appnexus"].module_type == "bid_adapters"

            assert "rubicon" in modules
            assert modules["rubicon"].first_version == "0.1.1"
            assert modules["rubicon"].first_major_version == 0

            # Modules introduced in v1.0.0
            assert "pubmatic" in modules
            assert modules["pubmatic"].first_version == "1.0.0"
            assert modules["pubmatic"].first_major_version == 1

            assert "ga" in modules
            assert modules["ga"].first_version == "1.0.0"
            assert modules["ga"].module_type == "analytics_adapters"

            # Modules introduced in v2.0.0
            assert "33across" in modules
            assert modules["33across"].first_version == "2.0.0"
            assert modules["33across"].first_major_version == 2

            assert "adagio" in modules
            assert modules["adagio"].module_type == "analytics_adapters"

            assert "rtdModule" in modules
            assert modules["rtdModule"].module_type == "other_modules"

            # Modules introduced in v3.0.0
            assert "unifiedId" in modules
            assert modules["unifiedId"].first_version == "3.0.0"
            assert modules["unifiedId"].module_type == "identity_modules"

            assert "amazon" in modules
            assert modules["amazon"].first_version == "3.0.0"

            # Modules introduced in v4.0.0
            assert "criteo" in modules
            assert modules["criteo"].first_version == "4.0.0"
            assert modules["criteo"].module_type == "rtd_modules"

            assert "id5" in modules
            assert modules["id5"].first_version == "4.0.0"
            assert modules["id5"].module_type == "identity_modules"

            # Verify metadata
            assert "analysis_date" in result.metadata
            assert "analyzed_versions" in result.metadata
            assert "total_modules" in result.metadata
            assert result.metadata["total_modules"] == len(modules)

    def test_module_timeline_generation(
        self, temp_cache_dir, mock_version_cache, mock_github_responses
    ):
        """Test generating module timeline from analysis."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(
                mock_github_responses
            )

            # Run analysis first
            tracker.analyze_module_history("prebid/Prebid.js", force_refresh=True)

            # Get timeline
            timeline = tracker.get_module_timeline("prebid/Prebid.js")

            # Verify timeline structure
            expected_majors = [0, 1, 2, 3, 4]
            for major in expected_majors:
                assert major in timeline
                assert len(timeline[major]) > 0

            # Verify specific version contents
            v0_modules = [entry.module_name for entry in timeline[0]]
            assert "appnexus" in v0_modules
            assert "rubicon" in v0_modules

            v1_modules = [entry.module_name for entry in timeline[1]]
            assert "pubmatic" in v1_modules
            assert "ga" in v1_modules

            v2_modules = [entry.module_name for entry in timeline[2]]
            assert "33across" in v2_modules
            assert "adagio" in v2_modules
            assert "rtdModule" in v2_modules

            # Verify modules are sorted alphabetically within each version
            for entries in timeline.values():
                module_names = [entry.module_name for entry in entries]
                assert module_names == sorted(module_names)

    def test_version_filtering(
        self, temp_cache_dir, mock_version_cache, mock_github_responses
    ):
        """Test filtering modules by major version."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(
                mock_github_responses
            )

            # Run analysis first
            tracker.analyze_module_history("prebid/Prebid.js", force_refresh=True)

            # Test filtering by different major versions
            v0_modules = tracker.get_modules_by_version(
                "prebid/Prebid.js", major_version=0
            )
            v1_modules = tracker.get_modules_by_version(
                "prebid/Prebid.js", major_version=1
            )
            v2_modules = tracker.get_modules_by_version(
                "prebid/Prebid.js", major_version=2
            )

            # Verify counts and contents
            assert len(v0_modules) == 2  # appnexus, rubicon
            assert len(v1_modules) == 2  # pubmatic, ga
            assert len(v2_modules) == 3  # 33across, adagio, rtdModule

            assert "appnexus" in v0_modules
            assert "rubicon" in v0_modules
            assert "pubmatic" in v1_modules
            assert "ga" in v1_modules
            assert "33across" in v2_modules

    def test_cache_persistence(
        self, temp_cache_dir, mock_version_cache, mock_github_responses
    ):
        """Test that cache persists across tracker instances."""
        # First tracker instance
        tracker1 = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        with (
            patch.object(tracker1.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker1.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(
                mock_github_responses
            )

            # Run analysis
            result1 = tracker1.analyze_module_history(
                "prebid/Prebid.js", force_refresh=True
            )

        # Second tracker instance (should use cache)
        tracker2 = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        # This should load from cache, not re-analyze
        result2 = tracker2.analyze_module_history(
            "prebid/Prebid.js", force_refresh=False
        )

        # Results should be identical
        assert result1.repo_name == result2.repo_name
        assert result1.last_analyzed_version == result2.last_analyzed_version
        assert len(result1.modules) == len(result2.modules)

        for module_name in result1.modules:
            assert module_name in result2.modules
            entry1 = result1.modules[module_name]
            entry2 = result2.modules[module_name]
            assert entry1.first_version == entry2.first_version
            assert entry1.module_type == entry2.module_type

    def test_progress_callback_integration(
        self, temp_cache_dir, mock_version_cache, mock_github_responses
    ):
        """Test progress callback during full analysis."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)
        progress_calls = []

        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(
                mock_github_responses
            )

            # Run analysis with progress callback
            tracker.analyze_module_history(
                "prebid/Prebid.js",
                force_refresh=True,
                progress_callback=progress_callback,
            )

            # Verify progress callbacks
            assert len(progress_calls) > 0

            # Check progression
            progress_values = [call[0] for call in progress_calls]
            assert progress_values[0] <= progress_values[-1]  # Should progress

            # Final call should indicate completion
            final_call = progress_calls[-1]
            assert final_call[0] == final_call[1]  # current == total
            assert "complete" in final_call[2].lower()

    def test_github_api_error_handling(self, temp_cache_dir, mock_version_cache):
        """Test handling of GitHub API errors during analysis."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        def failing_fetch(*args, **kwargs):
            raise Exception("GitHub API error")

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = failing_fetch

            # Analysis should handle errors gracefully
            from src.repo_modules.module_history import ModuleHistoryError

            with pytest.raises(
                ModuleHistoryError, match="No module data could be retrieved"
            ):
                tracker.analyze_module_history("prebid/Prebid.js", force_refresh=True)

    def test_partial_version_data(self, temp_cache_dir, mock_version_cache):
        """Test analysis when some versions have no data."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        # Only return data for some versions
        partial_responses = {
            "0.1.1": {
                "files": {"modules/appnexusBidAdapter.js": "// AppNexus v0.1.1"},
                "metadata": {"total_files": 1},
            },
            "2.0.0": {
                "files": {
                    "modules/appnexusBidAdapter.js": "// AppNexus v2.0.0",
                    "modules/pubmaticBidAdapter.js": "// PubMatic v2.0.0",
                },
                "metadata": {"total_files": 2},
            },
            # Missing data for versions 1.0.0, 3.0.0, 4.0.0
        }

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch.object(tracker.client, "fetch_repository_data") as mock_fetch,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_fetch.side_effect = self.mock_fetch_repository_data(partial_responses)

            # Analysis should continue with available data
            result = tracker.analyze_module_history(
                "prebid/Prebid.js", force_refresh=True
            )

            # Should have modules from available versions
            assert "appnexus" in result.modules
            assert result.modules["appnexus"].first_version == "0.1.1"

            assert "pubmatic" in result.modules
            assert result.modules["pubmatic"].first_version == "2.0.0"

            # Should only have modules from versions with data
            assert len(result.modules) == 2

    def test_empty_repository(self, temp_cache_dir):
        """Test analysis of repository with no modules."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        # Mock version cache with no major versions
        empty_version_cache = RepoVersionCache(
            repo_name="empty/repo",
            default_branch="master",
            major_versions={},  # No versions
            latest_versions=[],
        )

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load_cache,
            patch("time.sleep"),
        ):
            mock_load_cache.return_value = empty_version_cache

            # Should handle empty repository gracefully
            from src.repo_modules.module_history import ModuleHistoryError

            with pytest.raises(
                ModuleHistoryError, match="No module data could be retrieved"
            ):
                tracker.analyze_module_history("empty/repo", force_refresh=True)
