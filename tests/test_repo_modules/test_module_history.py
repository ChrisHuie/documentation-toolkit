"""
Tests for ModuleHistoryTracker functionality
"""

import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory

from src.repo_modules.module_history import ModuleHistoryInfo, ModuleHistoryTracker


class TestModuleHistoryTracker:
    """Test ModuleHistoryTracker implementation."""

    def test_module_history_info_creation(self):
        """Test ModuleHistoryInfo dataclass creation."""
        info = ModuleHistoryInfo(
            name="test_module",
            first_commit_date="2020-06-22T12:53:52Z",
            first_commit_sha="abc123",
            first_release_version="v5.0.0",
            first_release_date="2020-07-01T00:00:00Z",
            file_path="modules/testBidAdapter.js",
        )

        assert info.name == "test_module"
        assert info.first_commit_date == "2020-06-22T12:53:52Z"
        assert info.first_commit_sha == "abc123"
        assert info.first_release_version == "v5.0.0"
        assert info.file_path == "modules/testBidAdapter.js"

    def test_tracker_initialization(self):
        """Test ModuleHistoryTracker initialization."""
        with TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            tracker = ModuleHistoryTracker("test/repo", cache_dir)

            assert tracker.repo == "test/repo"
            assert tracker.cache_dir == cache_dir
            assert tracker.cache_file == cache_dir / "test_repo_history.json"

    def test_cache_loading_and_saving(self):
        """Test cache persistence."""
        with TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create initial tracker and add data
            tracker1 = ModuleHistoryTracker("test/repo", cache_dir)
            test_info = ModuleHistoryInfo(
                name="test_module",
                first_commit_date="2020-06-22T12:53:52Z",
                first_commit_sha="abc123",
            )
            tracker1._cache["test_module"] = test_info
            tracker1._save_cache()

            # Create new tracker and verify data persisted
            tracker2 = ModuleHistoryTracker("test/repo", cache_dir)
            assert "test_module" in tracker2._cache
            cached_info = tracker2._cache["test_module"]
            assert cached_info.name == "test_module"
            assert cached_info.first_commit_date == "2020-06-22T12:53:52Z"

    def test_extract_module_name(self):
        """Test module name extraction from file paths."""
        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))

            # Test different file patterns
            assert (
                tracker._extract_module_name("modules/appnexusBidAdapter.js")
                == "appnexus"
            )
            assert (
                tracker._extract_module_name(
                    "modules/googleAnalyticsAnalyticsAdapter.js"
                )
                == "googleAnalytics"
            )
            assert (
                tracker._extract_module_name("modules/amazonRtdProvider.js") == "amazon"
            )
            assert (
                tracker._extract_module_name("modules/facebookIdSystem.js")
                == "facebook"
            )
            assert tracker._extract_module_name("modules/currency.js") == "currency"

    def test_guess_file_path(self):
        """Test file path guessing for modules."""
        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))

            # Should default to bid adapter pattern
            path = tracker._guess_file_path("testmodule")
            assert path == "modules/testmoduleBidAdapter.js"

    def test_get_file_creation_info_mock(self):
        """Test file creation info retrieval with mocked API."""
        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))

            # Mock API response
            mock_commits = [
                {
                    "sha": "abc123",
                    "commit": {"author": {"date": "2020-06-22T12:53:52Z"}},
                }
            ]

            with unittest.mock.patch("requests.get") as mock_get:
                mock_response = unittest.mock.Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_commits
                mock_response.headers = {}
                mock_get.return_value = mock_response

                # Mock the total commits method to avoid pagination
                with unittest.mock.patch.object(
                    tracker, "_get_total_commits_for_file", return_value=1
                ):
                    info = tracker._get_file_creation_info("modules/testBidAdapter.js")

                    assert info is not None
                    assert info.name == "test"
                    assert info.first_commit_date == "2020-06-22T12:53:52Z"
                    assert info.first_commit_sha == "abc123"
                    assert info.file_path == "modules/testBidAdapter.js"

    def test_enrich_module_data(self):
        """Test module data enrichment."""
        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))

            # Add some test data to cache
            tracker._cache["module1"] = ModuleHistoryInfo(
                name="module1",
                first_commit_date="2020-06-22T12:53:52Z",
                first_commit_sha="abc123",
            )
            tracker._cache["module2"] = ModuleHistoryInfo(
                name="module2",
                first_commit_date="2021-01-15T10:30:00Z",
                first_commit_sha="def456",
            )

            modules_data = {
                "bid_adapters": ["module1", "module2", "module3"],
                "analytics_adapters": [],
            }

            enriched = tracker.enrich_module_data(modules_data)

            # Check structure
            assert "bid_adapters" in enriched
            assert "analytics_adapters" in enriched
            assert len(enriched["bid_adapters"]) == 3
            assert len(enriched["analytics_adapters"]) == 0

            # Check enriched data
            bid_adapters = enriched["bid_adapters"]
            module1_data = next(
                item for item in bid_adapters if item["name"] == "module1"
            )
            assert module1_data["first_added"] == "2020-06-22T12:53:52Z"
            assert module1_data["first_commit_sha"] == "abc123"

            # Check missing data handling
            module3_data = next(
                item for item in bid_adapters if item["name"] == "module3"
            )
            assert module3_data["first_added"] is None
            assert module3_data["first_commit_sha"] is None

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        import time

        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))
            tracker._min_request_interval = 0.1  # Short interval for testing

            start_time = time.time()
            tracker._rate_limit()
            tracker._rate_limit()
            end_time = time.time()

            # Should have waited at least the interval
            assert (end_time - start_time) >= 0.1

    def test_error_handling_in_get_module_history(self):
        """Test error handling when API calls fail."""
        with TemporaryDirectory() as temp_dir:
            tracker = ModuleHistoryTracker("test/repo", Path(temp_dir))

            with unittest.mock.patch.object(
                tracker, "_get_file_creation_info", side_effect=Exception("API Error")
            ):
                # Should not crash, should return empty results
                result = tracker.get_module_history(["test_module"])
                assert result == {}

    def test_cache_with_corrupted_file(self):
        """Test handling of corrupted cache file."""
        with TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache_file = cache_dir / "test_repo_history.json"

            # Create corrupted cache file
            with open(cache_file, "w") as f:
                f.write("invalid json {")

            # Should handle gracefully and start with empty cache
            tracker = ModuleHistoryTracker("test/repo", cache_dir)
            assert tracker._cache == {}
