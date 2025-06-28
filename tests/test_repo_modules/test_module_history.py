"""
Tests for module history tracking functionality.
"""

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


class TestModuleHistoryEntry:
    """Test ModuleHistoryEntry dataclass."""

    def test_creation(self):
        """Test creating a module history entry."""
        entry = ModuleHistoryEntry(
            module_name="appnexus",
            module_type="bid_adapters",
            first_version="1.5.0",
            first_major_version=1,
            file_path="modules/appnexusBidAdapter.js",
        )

        assert entry.module_name == "appnexus"
        assert entry.module_type == "bid_adapters"
        assert entry.first_version == "1.5.0"
        assert entry.first_major_version == 1
        assert entry.file_path == "modules/appnexusBidAdapter.js"


class TestModuleHistoryCache:
    """Test ModuleHistoryCache dataclass."""

    def test_creation(self):
        """Test creating a module history cache."""
        modules = {
            "appnexus": ModuleHistoryEntry(
                module_name="appnexus",
                module_type="bid_adapters",
                first_version="1.5.0",
                first_major_version=1,
                file_path="modules/appnexusBidAdapter.js",
            )
        }

        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="9.52.0",
            modules=modules,
            metadata={"analysis_date": "2023-01-01"},
        )

        assert cache.repo_name == "prebid/Prebid.js"
        assert cache.last_analyzed_version == "9.52.0"
        assert len(cache.modules) == 1
        assert "appnexus" in cache.modules
        assert cache.metadata["analysis_date"] == "2023-01-01"


class TestModuleHistoryTracker:
    """Test ModuleHistoryTracker class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def tracker(self, temp_cache_dir):
        """Create tracker with temporary cache directory."""
        return ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

    @pytest.fixture
    def mock_version_cache(self):
        """Create mock version cache."""
        return RepoVersionCache(
            repo_name="prebid/Prebid.js",
            default_branch="master",
            major_versions={
                1: MajorVersionInfo(
                    major=1, first_version="1.0.0", last_version="1.40.0"
                ),
                2: MajorVersionInfo(
                    major=2, first_version="2.0.0", last_version="2.44.7"
                ),
                3: MajorVersionInfo(
                    major=3, first_version="3.0.0", last_version="3.27.1"
                ),
            },
            latest_versions=["3.27.1", "3.27.0", "3.26.0", "3.25.0", "3.24.0"],
        )

    @pytest.fixture
    def sample_modules_data(self):
        """Sample module data for different versions."""
        return {
            "1.0.0": {
                "bid_adapters": ["appnexus", "rubicon"],
                "analytics_adapters": [],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
            "2.0.0": {
                "bid_adapters": ["appnexus", "rubicon", "pubmatic"],
                "analytics_adapters": ["ga"],
                "rtd_modules": [],
                "identity_modules": [],
                "other_modules": [],
            },
            "3.0.0": {
                "bid_adapters": ["appnexus", "rubicon", "pubmatic", "33across"],
                "analytics_adapters": ["ga", "adagio"],
                "rtd_modules": ["rtdModule"],
                "identity_modules": ["unifiedId"],
                "other_modules": [],
            },
        }

    def test_initialization(self, temp_cache_dir):
        """Test tracker initialization."""
        tracker = ModuleHistoryTracker(token="test_token", cache_dir=temp_cache_dir)

        assert tracker.history_cache_dir == Path(temp_cache_dir)
        assert tracker.history_cache_dir.exists()

    def test_get_cache_file(self, tracker):
        """Test cache file path generation."""
        cache_file = tracker._get_cache_file("prebid/Prebid.js")
        expected_name = "prebid_Prebid.js_module_history.json"

        assert cache_file.name == expected_name
        assert cache_file.parent == tracker.history_cache_dir

    def test_save_and_load_cache(self, tracker):
        """Test saving and loading cache."""
        # Create test cache
        modules = {
            "appnexus": ModuleHistoryEntry(
                module_name="appnexus",
                module_type="bid_adapters",
                first_version="1.0.0",
                first_major_version=1,
                file_path="modules/appnexusBidAdapter.js",
            ),
            "ga": ModuleHistoryEntry(
                module_name="ga",
                module_type="analytics_adapters",
                first_version="2.0.0",
                first_major_version=2,
                file_path="modules/gaAnalyticsAdapter.js",
            ),
        }

        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="3.0.0",
            modules=modules,
            metadata={"test": "data"},
        )

        # Save cache
        tracker._save_history_cache(cache)

        # Load cache
        loaded_cache = tracker._load_history_cache("prebid/Prebid.js")

        assert loaded_cache is not None
        assert loaded_cache.repo_name == "prebid/Prebid.js"
        assert loaded_cache.last_analyzed_version == "3.0.0"
        assert len(loaded_cache.modules) == 2
        assert "appnexus" in loaded_cache.modules
        assert "ga" in loaded_cache.modules
        assert loaded_cache.metadata["test"] == "data"

    def test_load_nonexistent_cache(self, tracker):
        """Test loading cache that doesn't exist."""
        cache = tracker._load_history_cache("nonexistent/repo")
        assert cache is None

    def test_load_corrupted_cache(self, tracker):
        """Test loading corrupted cache file."""
        # Create corrupted cache file
        cache_file = tracker._get_cache_file("test/repo")
        cache_file.write_text("invalid json")

        cache = tracker._load_history_cache("test/repo")
        assert cache is None

    def test_parse_version_number(self, tracker):
        """Test version number parsing."""
        # Test various version formats
        assert tracker._parse_version_number("1.2.3") == (1, 2, 3)
        assert tracker._parse_version_number("v1.2.3") == (1, 2, 3)
        assert tracker._parse_version_number("10.0.0") == (10, 0, 0)
        assert tracker._parse_version_number("1.2") == (1, 2, 0)
        assert tracker._parse_version_number("1") == (1, 0, 0)
        assert tracker._parse_version_number("invalid") == (0, 0, 0)

    def test_guess_file_path_for_module(self, tracker):
        """Test file path generation for modules."""
        # Test different module types
        assert (
            tracker._guess_file_path_for_module("appnexus", "bid_adapters")
            == "modules/appnexusBidAdapter.js"
        )
        assert (
            tracker._guess_file_path_for_module("ga", "analytics_adapters")
            == "modules/gaAnalyticsAdapter.js"
        )
        assert (
            tracker._guess_file_path_for_module("rtd", "rtd_modules")
            == "modules/rtdRtdProvider.js"
        )
        assert (
            tracker._guess_file_path_for_module("unified", "identity_modules")
            == "modules/unifiedIdSystem.js"
        )
        assert (
            tracker._guess_file_path_for_module("other", "other_modules")
            == "modules/other.js"
        )

    def test_apply_case_corrections(self, tracker):
        """Test case corrections for module names."""
        # Test known corrections
        assert tracker._apply_case_corrections("appnexus") == "appnexus"
        assert tracker._apply_case_corrections("APPNEXUS") == "appnexus"

        # Test unknown module (should pass through)
        assert tracker._apply_case_corrections("unknownModule") == "unknownModule"

    def test_analyze_module_introduction(self, tracker, sample_modules_data):
        """Test module introduction analysis."""
        history = tracker._analyze_module_introduction(
            "prebid/Prebid.js", sample_modules_data
        )

        # Check that all modules are tracked
        expected_modules = {
            "appnexus": "1.0.0",
            "rubicon": "1.0.0",
            "pubmatic": "2.0.0",
            "ga": "2.0.0",
            "33across": "3.0.0",
            "adagio": "3.0.0",
            "rtdModule": "3.0.0",
            "unifiedId": "3.0.0",
        }

        assert len(history) == len(expected_modules)

        for module_name, expected_version in expected_modules.items():
            assert module_name in history
            entry = history[module_name]
            assert entry.first_version == expected_version
            assert entry.module_name == module_name

    @patch(
        "src.repo_modules.module_history.ModuleHistoryTracker._get_modules_for_version"
    )
    @patch("src.repo_modules.module_history.VersionCacheManager.load_cache")
    def test_analyze_module_history_success(
        self,
        mock_load_cache,
        mock_get_modules,
        tracker,
        mock_version_cache,
        sample_modules_data,
    ):
        """Test successful module history analysis."""
        # Setup mocks
        mock_load_cache.return_value = mock_version_cache
        mock_get_modules.side_effect = lambda repo, version: sample_modules_data.get(
            version, {}
        )

        # Run analysis
        result = tracker.analyze_module_history("prebid/Prebid.js", force_refresh=True)

        # Verify results
        assert isinstance(result, ModuleHistoryCache)
        assert result.repo_name == "prebid/Prebid.js"
        assert len(result.modules) > 0
        assert "appnexus" in result.modules
        assert result.modules["appnexus"].first_version == "1.0.0"

    @patch("src.repo_modules.module_history.VersionCacheManager.load_cache")
    def test_analyze_module_history_no_version_cache(self, mock_load_cache, tracker):
        """Test analysis when no version cache exists."""
        mock_load_cache.return_value = None

        with pytest.raises(ModuleHistoryError, match="No version cache found"):
            tracker.analyze_module_history("prebid/Prebid.js")

    @patch(
        "src.repo_modules.module_history.ModuleHistoryTracker._get_modules_for_version"
    )
    @patch("src.repo_modules.module_history.VersionCacheManager.load_cache")
    def test_analyze_module_history_no_modules(
        self, mock_load_cache, mock_get_modules, tracker, mock_version_cache
    ):
        """Test analysis when no modules can be retrieved."""
        mock_load_cache.return_value = mock_version_cache
        mock_get_modules.return_value = {}  # No modules found

        with pytest.raises(
            ModuleHistoryError, match="No module data could be retrieved"
        ):
            tracker.analyze_module_history("prebid/Prebid.js", force_refresh=True)

    def test_get_modules_by_version(self, tracker):
        """Test getting modules by version filter."""
        # Create test cache
        modules = {
            "appnexus": ModuleHistoryEntry(
                "appnexus", "bid_adapters", "1.0.0", 1, "modules/appnexusBidAdapter.js"
            ),
            "pubmatic": ModuleHistoryEntry(
                "pubmatic", "bid_adapters", "2.0.0", 2, "modules/pubmaticBidAdapter.js"
            ),
            "33across": ModuleHistoryEntry(
                "33across", "bid_adapters", "3.0.0", 3, "modules/33acrossBidAdapter.js"
            ),
        }

        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="3.0.0",
            modules=modules,
            metadata={},
        )

        tracker._save_history_cache(cache)

        # Test filtering by major version
        v1_modules = tracker.get_modules_by_version("prebid/Prebid.js", major_version=1)
        assert len(v1_modules) == 1
        assert "appnexus" in v1_modules

        v2_modules = tracker.get_modules_by_version("prebid/Prebid.js", major_version=2)
        assert len(v2_modules) == 1
        assert "pubmatic" in v2_modules

        # Test getting all modules
        all_modules = tracker.get_modules_by_version(
            "prebid/Prebid.js", major_version=None
        )
        assert len(all_modules) == 3

    def test_get_module_timeline(self, tracker):
        """Test getting module timeline."""
        # Create test cache with modules across different versions
        modules = {
            "appnexus": ModuleHistoryEntry(
                "appnexus", "bid_adapters", "1.0.0", 1, "modules/appnexusBidAdapter.js"
            ),
            "rubicon": ModuleHistoryEntry(
                "rubicon", "bid_adapters", "1.5.0", 1, "modules/rubiconBidAdapter.js"
            ),
            "pubmatic": ModuleHistoryEntry(
                "pubmatic", "bid_adapters", "2.0.0", 2, "modules/pubmaticBidAdapter.js"
            ),
            "ga": ModuleHistoryEntry(
                "ga", "analytics_adapters", "2.0.0", 2, "modules/gaAnalyticsAdapter.js"
            ),
        }

        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="3.0.0",
            modules=modules,
            metadata={},
        )

        tracker._save_history_cache(cache)

        # Get timeline
        timeline = tracker.get_module_timeline("prebid/Prebid.js")

        # Verify structure
        assert 1 in timeline
        assert 2 in timeline
        assert len(timeline[1]) == 2  # appnexus, rubicon
        assert len(timeline[2]) == 2  # pubmatic, ga

        # Verify sorting (should be alphabetical by module name)
        v1_modules = [entry.module_name for entry in timeline[1]]
        assert v1_modules == ["appnexus", "rubicon"]

    def test_clear_cache(self, tracker):
        """Test clearing cache."""
        # Create test cache
        modules = {
            "test": ModuleHistoryEntry(
                "test", "bid_adapters", "1.0.0", 1, "modules/test.js"
            )
        }
        cache = ModuleHistoryCache("prebid/Prebid.js", "1.0.0", modules, {})
        tracker._save_history_cache(cache)

        # Verify cache exists
        assert tracker._get_cache_file("prebid/Prebid.js").exists()

        # Clear specific cache
        tracker.clear_cache("prebid/Prebid.js")

        # Verify cache is gone
        assert not tracker._get_cache_file("prebid/Prebid.js").exists()

    def test_clear_all_caches(self, tracker):
        """Test clearing all caches."""
        # Create multiple test caches
        for repo in ["repo1/test", "repo2/test"]:
            modules = {
                "test": ModuleHistoryEntry(
                    "test", "bid_adapters", "1.0.0", 1, "modules/test.js"
                )
            }
            cache = ModuleHistoryCache(repo, "1.0.0", modules, {})
            tracker._save_history_cache(cache)

        # Verify caches exist
        assert len(list(tracker.history_cache_dir.glob("*_module_history.json"))) == 2

        # Clear all caches
        tracker.clear_cache()

        # Verify all caches are gone
        assert len(list(tracker.history_cache_dir.glob("*_module_history.json"))) == 0

    def test_get_cache_info(self, tracker):
        """Test getting cache information."""
        # Test when no cache exists
        info = tracker.get_cache_info("nonexistent/repo")
        assert info is None

        # Create test cache
        modules = {
            "test": ModuleHistoryEntry(
                "test", "bid_adapters", "1.0.0", 1, "modules/test.js"
            )
        }
        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="1.0.0",
            modules=modules,
            metadata={"analysis_date": "2023-01-01"},
        )
        tracker._save_history_cache(cache)

        # Get cache info
        info = tracker.get_cache_info("prebid/Prebid.js")

        assert info is not None
        assert info["repo_name"] == "prebid/Prebid.js"
        assert info["last_analyzed_version"] == "1.0.0"
        assert info["module_count"] == 1
        assert info["metadata"]["analysis_date"] == "2023-01-01"
        assert "cache_file" in info

    def test_progress_callback(self, tracker, mock_version_cache, sample_modules_data):
        """Test progress callback functionality."""
        progress_calls = []

        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))

        with (
            patch(
                "src.repo_modules.module_history.VersionCacheManager.load_cache"
            ) as mock_load_cache,
            patch(
                "src.repo_modules.module_history.ModuleHistoryTracker._get_modules_for_version"
            ) as mock_get_modules,
        ):
            mock_load_cache.return_value = mock_version_cache
            mock_get_modules.side_effect = (
                lambda repo, version: sample_modules_data.get(version, {})
            )

            tracker.analyze_module_history(
                "prebid/Prebid.js",
                force_refresh=True,
                progress_callback=progress_callback,
            )

            # Verify progress callbacks were called
            assert len(progress_calls) > 0

            # Check that final call indicates completion
            final_call = progress_calls[-1]
            assert final_call[0] == final_call[1]  # current == total
            assert "complete" in final_call[2].lower()


class TestModuleHistoryError:
    """Test ModuleHistoryError exception."""

    def test_creation(self):
        """Test creating module history error."""
        error = ModuleHistoryError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
