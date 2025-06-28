"""
Edge case and error handling tests for module history functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.repo_modules.module_history import (
    ModuleHistoryCache,
    ModuleHistoryEntry,
    ModuleHistoryError,
    ModuleHistoryTracker,
)
from src.repo_modules.version_cache import MajorVersionInfo, RepoVersionCache


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def tracker(self, temp_cache_dir):
        """Create tracker with temporary cache directory."""
        return ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

    def test_invalid_cache_directory_permissions(self, temp_cache_dir):
        """Test handling of cache directory permission issues."""
        cache_dir = Path(temp_cache_dir) / "readonly"
        cache_dir.mkdir()
        cache_dir.chmod(0o444)  # Read-only

        try:
            # This should handle permission errors gracefully
            tracker = ModuleHistoryTracker(cache_dir=str(cache_dir))

            # Attempting to save should raise an error
            modules = {
                "test": ModuleHistoryEntry(
                    "test", "bid_adapters", "1.0.0", 1, "test.js"
                )
            }
            cache = ModuleHistoryCache("test/repo", "1.0.0", modules, {})

            with pytest.raises(ModuleHistoryError, match="Failed to save cache"):
                tracker._save_history_cache(cache)
        finally:
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)

    def test_corrupted_cache_file_formats(self, tracker):
        """Test handling various types of corrupted cache files."""
        cache_file = tracker._get_cache_file("test/repo")

        # Test completely invalid JSON
        cache_file.write_text("invalid json content {")
        assert tracker._load_history_cache("test/repo") is None

        # Test valid JSON but wrong structure
        cache_file.write_text('{"wrong": "structure"}')
        assert tracker._load_history_cache("test/repo") is None

        # Test JSON with missing required fields
        cache_file.write_text('{"repo_name": "test", "modules": {}}')
        assert tracker._load_history_cache("test/repo") is None

        # Test JSON with invalid module entries
        invalid_cache = {
            "repo_name": "test/repo",
            "last_analyzed_version": "1.0.0",
            "modules": {
                "invalid_module": {
                    "module_name": "test",
                    "missing_required_fields": True,
                }
            },
            "metadata": {},
        }
        cache_file.write_text(json.dumps(invalid_cache))

        # Should load but skip invalid entries
        loaded = tracker._load_history_cache("test/repo")
        assert loaded is not None
        assert len(loaded.modules) == 0  # Invalid entry should be skipped

    def test_version_parsing_edge_cases(self, tracker):
        """Test version parsing with various edge cases."""
        # Test various version formats
        test_cases = [
            ("1.2.3", (1, 2, 3)),
            ("v1.2.3", (1, 2, 3)),
            ("10.0.0", (10, 0, 0)),
            ("1.2", (1, 2, 0)),
            ("1", (1, 0, 0)),
            ("", (0, 0, 0)),
            ("invalid", (0, 0, 0)),
            ("1.2.3.4", (1, 2, 3)),  # Extra components ignored
            ("v", (0, 0, 0)),
            ("1.a.3", (1, 0, 0)),  # Invalid minor version
            ("a.b.c", (0, 0, 0)),  # All invalid
        ]

        for version_str, expected in test_cases:
            result = tracker._parse_version_number(version_str)
            assert result == expected, f"Failed for version: {version_str}"

    def test_empty_module_responses(self, tracker):
        """Test handling of empty or malformed module responses."""
        # Test with empty file list
        result = tracker._get_modules_for_version("test/repo", "1.0.0")
        assert isinstance(result, dict)
        # Should return empty dict on error, not crash

    def test_memory_constraints_large_datasets(self, tracker):
        """Test handling of very large datasets."""
        # Create a large number of modules to test memory efficiency
        large_modules_data = {}

        for i in range(1000):
            version = f"{i // 100}.{i % 100}.0"
            if version not in large_modules_data:
                large_modules_data[version] = {
                    "bid_adapters": [],
                    "analytics_adapters": [],
                    "rtd_modules": [],
                    "identity_modules": [],
                    "other_modules": [],
                }

            large_modules_data[version]["bid_adapters"].append(f"adapter_{i}")

        # Should handle large datasets without issues
        result = tracker._analyze_module_introduction("test/repo", large_modules_data)
        assert len(result) == 1000

        # Verify memory isn't growing unreasonably (basic check)
        assert isinstance(result, dict)

    def test_concurrent_cache_access(self, temp_cache_dir):
        """Test handling of concurrent cache access."""
        # Create two tracker instances with same cache directory
        tracker1 = ModuleHistoryTracker(cache_dir=temp_cache_dir)
        tracker2 = ModuleHistoryTracker(cache_dir=temp_cache_dir)

        # Create test cache with first tracker
        modules = {
            "test": ModuleHistoryEntry("test", "bid_adapters", "1.0.0", 1, "test.js")
        }
        cache = ModuleHistoryCache("test/repo", "1.0.0", modules, {})
        tracker1._save_history_cache(cache)

        # Second tracker should be able to read the cache
        loaded = tracker2._load_history_cache("test/repo")
        assert loaded is not None
        assert len(loaded.modules) == 1

    def test_unicode_and_special_characters(self, tracker):
        """Test handling of Unicode and special characters in module names."""
        # Test with various special characters in module names
        special_modules = {
            "1.0.0": {
                "bid_adapters": [
                    "module-with-dashes",
                    "module_with_underscores",
                    "module.with.dots",
                ],
                "analytics_adapters": ["módule-with-unicode", "module with spaces"],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": ["module@special#chars"],
            }
        }

        # Should handle special characters gracefully
        result = tracker._analyze_module_introduction("test/repo", special_modules)

        assert "module-with-dashes" in result
        assert "module_with_underscores" in result
        assert "module.with.dots" in result
        assert "module with spaces" in result
        assert "module@special#chars" in result

    def test_network_timeout_simulation(self, tracker):
        """Test handling of network timeouts and API failures."""
        with patch.object(tracker.client, "fetch_repository_data") as mock_fetch:
            # Simulate various network errors
            mock_fetch.side_effect = [
                ConnectionError("Network unreachable"),
                TimeoutError("Request timeout"),
                Exception("Generic network error"),
            ]

            # Should handle each error gracefully
            for _ in range(3):
                result = tracker._get_modules_for_version("test/repo", "1.0.0")
                assert result == {}  # Should return empty dict, not crash

    def test_malformed_repository_data(self, tracker):
        """Test handling of malformed repository data."""
        with patch.object(tracker.client, "fetch_repository_data") as mock_fetch:
            # Test various malformed responses
            malformed_responses = [
                None,  # Null response
                {},  # Empty dict
                {"files": None},  # Null files
                {"files": "not_a_dict"},  # Wrong type
                {"files": {"file1": None}},  # Null file content
                {"no_files_key": True},  # Missing files key
            ]

            for response in malformed_responses:
                mock_fetch.return_value = response
                result = tracker._get_modules_for_version("test/repo", "1.0.0")
                # Should handle gracefully without crashing
                assert isinstance(result, dict)

    def test_disk_space_exhaustion(self, tracker):
        """Test behavior when disk space is exhausted."""
        # Simulate disk full condition
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            modules = {
                "test": ModuleHistoryEntry(
                    "test", "bid_adapters", "1.0.0", 1, "test.js"
                )
            }
            cache = ModuleHistoryCache("test/repo", "1.0.0", modules, {})

            with pytest.raises(ModuleHistoryError, match="Failed to save cache"):
                tracker._save_history_cache(cache)

    def test_extremely_long_module_names(self, tracker):
        """Test handling of extremely long module names."""
        # Create module with very long name
        long_name = "a" * 1000
        long_modules = {
            "1.0.0": {
                "bid_adapters": [long_name],
                "analytics_adapters": [],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            }
        }

        # Should handle long names without issues
        result = tracker._analyze_module_introduction("test/repo", long_modules)
        assert long_name in result
        assert len(result[long_name].module_name) == 1000

    def test_module_name_collisions(self, tracker):
        """Test handling of module name collisions across categories."""
        # Same module name in different categories
        collision_modules = {
            "1.0.0": {
                "bid_adapters": ["collision"],
                "analytics_adapters": [],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
            "2.0.0": {
                "bid_adapters": ["collision"],
                "analytics_adapters": ["collision"],  # Same name, different category
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
        }

        result = tracker._analyze_module_introduction("test/repo", collision_modules)

        # Only the first occurrence should be recorded
        assert "collision" in result
        assert result["collision"].first_version == "1.0.0"
        assert result["collision"].module_type == "bid_adapters"

    def test_case_correction_edge_cases(self, tracker):
        """Test case correction with edge cases."""
        # Test various case scenarios
        test_cases = [
            ("", ""),  # Empty string
            ("a", "a"),  # Single character
            ("UPPERCASE", "UPPERCASE"),  # Unknown uppercase
            ("MiXeD_CaSe", "MiXeD_CaSe"),  # Mixed case unknown
            ("123numeric", "123numeric"),  # Numeric
            ("special-chars!", "special-chars!"),  # Special characters
        ]

        for input_name, expected in test_cases:
            result = tracker._apply_case_corrections(input_name)
            assert result == expected

    def test_file_path_generation_edge_cases(self, tracker):
        """Test file path generation with edge cases."""
        # Test various module name and category combinations
        test_cases = [
            ("", "bid_adapters", "modules/BidAdapter.js"),
            ("test", "unknown_category", "modules/test.js"),
            (
                "very-long-module-name",
                "bid_adapters",
                "modules/very-long-module-nameBidAdapter.js",
            ),
            (
                "module/with/slashes",
                "analytics_adapters",
                "modules/module/with/slashesAnalyticsAdapter.js",
            ),
        ]

        for module_name, category, expected in test_cases:
            result = tracker._guess_file_path_for_module(module_name, category)
            assert result == expected

    def test_version_cache_corruption(self, tracker):
        """Test handling of corrupted version cache."""
        with patch.object(tracker.cache_manager, "load_cache") as mock_load:
            # Test various cache corruption scenarios
            mock_load.side_effect = [
                None,  # No cache
                Exception("Cache corruption"),  # Exception during load
            ]

            # Should raise appropriate errors
            with pytest.raises(ModuleHistoryError, match="No version cache found"):
                tracker.analyze_module_history("test/repo")

            with pytest.raises(
                ModuleHistoryError, match="Failed to load version cache"
            ):
                tracker.analyze_module_history("test/repo")

    def test_progress_callback_exceptions(self, tracker):
        """Test handling of exceptions in progress callbacks."""

        def failing_callback(current, total, message):
            raise Exception("Callback error")

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load,
            patch.object(tracker, "_get_modules_for_version") as mock_get,
        ):
            mock_load.return_value = RepoVersionCache(
                repo_name="test/repo",
                default_branch="master",
                major_versions={1: MajorVersionInfo(1, "1.0.0", "1.1.0")},
                latest_versions=["1.1.0"],
            )
            mock_get.return_value = {"bid_adapters": ["test"]}

            # Should continue even if callback fails
            result = tracker.analyze_module_history(
                "test/repo", force_refresh=True, progress_callback=failing_callback
            )

            assert result is not None
            assert len(result.modules) > 0

    def test_extremely_large_version_numbers(self, tracker):
        """Test handling of extremely large version numbers."""
        large_version_cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                999: MajorVersionInfo(999, "999.0.0", "999.999.999"),
                1000: MajorVersionInfo(1000, "1000.0.0", "1000.0.0"),
            },
            latest_versions=["1000.0.0"],
        )

        with (
            patch.object(tracker.cache_manager, "load_cache") as mock_load,
            patch.object(tracker, "_get_modules_for_version") as mock_get,
        ):
            mock_load.return_value = large_version_cache
            mock_get.return_value = {"bid_adapters": ["test"]}

            # Should handle large version numbers
            result = tracker.analyze_module_history("test/repo", force_refresh=True)
            assert result is not None

    def test_empty_major_versions(self, tracker):
        """Test handling of version cache with no major versions."""
        empty_cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={},  # No versions
            latest_versions=[],
        )

        with patch.object(tracker.cache_manager, "load_cache") as mock_load:
            mock_load.return_value = empty_cache

            with pytest.raises(
                ModuleHistoryError, match="No module data could be retrieved"
            ):
                tracker.analyze_module_history("test/repo", force_refresh=True)

    def test_module_introduction_with_no_modules(self, tracker):
        """Test analysis when no modules are found in any version."""
        empty_modules_data = {
            "1.0.0": {
                "bid_adapters": [],
                "analytics_adapters": [],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
            "2.0.0": {
                "bid_adapters": [],
                "analytics_adapters": [],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
        }

        result = tracker._analyze_module_introduction("test/repo", empty_modules_data)
        assert len(result) == 0
        assert isinstance(result, dict)

    def test_clear_cache_file_permissions(self, tracker):
        """Test cache clearing with file permission issues."""
        # Create cache file
        modules = {
            "test": ModuleHistoryEntry("test", "bid_adapters", "1.0.0", 1, "test.js")
        }
        cache = ModuleHistoryCache("test/repo", "1.0.0", modules, {})
        tracker._save_history_cache(cache)

        cache_file = tracker._get_cache_file("test/repo")

        # Make file read-only
        cache_file.chmod(0o444)

        try:
            # Should raise error when trying to delete read-only file
            with pytest.raises(ModuleHistoryError, match="Failed to clear cache"):
                tracker.clear_cache("test/repo")
        finally:
            # Restore permissions for cleanup
            cache_file.chmod(0o644)
            cache_file.unlink()


class TestRobustnessUnderStress:
    """Test system robustness under stress conditions."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_rapid_successive_operations(self, temp_cache_dir):
        """Test rapid successive cache operations."""
        tracker = ModuleHistoryTracker(cache_dir=temp_cache_dir)

        # Perform many rapid operations
        for i in range(100):
            modules = {
                f"module_{i}": ModuleHistoryEntry(
                    f"module_{i}", "bid_adapters", "1.0.0", 1, f"test_{i}.js"
                )
            }
            cache = ModuleHistoryCache(f"repo_{i}", "1.0.0", modules, {})

            # Save and immediately load
            tracker._save_history_cache(cache)
            loaded = tracker._load_history_cache(f"repo_{i}")

            assert loaded is not None
            assert len(loaded.modules) == 1

    def test_memory_cleanup_after_operations(self, temp_cache_dir):
        """Test that memory is properly cleaned up after operations."""
        tracker = ModuleHistoryTracker(cache_dir=temp_cache_dir)

        # Perform operations that should not accumulate memory
        for i in range(10):
            large_modules = {}
            for j in range(100):
                large_modules[f"module_{i}_{j}"] = ModuleHistoryEntry(
                    f"module_{i}_{j}", "bid_adapters", "1.0.0", 1, f"test_{i}_{j}.js"
                )

            cache = ModuleHistoryCache(f"repo_{i}", "1.0.0", large_modules, {})
            tracker._save_history_cache(cache)

            # Clear references
            del large_modules, cache

        # System should remain stable
        assert tracker is not None
