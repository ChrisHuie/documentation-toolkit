"""Tests for module history data models."""

from src.module_history.data_models import (
    HistoryCache,
    ModuleHistoryEntry,
    ModuleHistoryResult,
)


class TestModuleHistoryEntry:
    """Test ModuleHistoryEntry dataclass."""

    def test_basic_entry_creation(self):
        """Test creating a basic module history entry."""
        entry = ModuleHistoryEntry(
            module_name="appnexus",
            module_type="bid_adapters",
            first_version="2.15.0",
            first_major_version=2,
            file_path="modules/appnexusBidAdapter.js",
        )

        assert entry.module_name == "appnexus"
        assert entry.module_type == "bid_adapters"
        assert entry.first_version == "2.15.0"
        assert entry.first_major_version == 2
        assert entry.file_path == "modules/appnexusBidAdapter.js"
        assert entry.first_commit_date is None
        assert entry.first_commit_sha is None

    def test_entry_with_commit_info(self):
        """Test creating entry with commit information."""
        entry = ModuleHistoryEntry(
            module_name="rubicon",
            module_type="bid_adapters",
            first_version="1.0.0",
            first_major_version=1,
            file_path="modules/rubiconBidAdapter.js",
            first_commit_date="2023-01-01T00:00:00Z",
            first_commit_sha="abc123",
        )

        assert entry.first_commit_date == "2023-01-01T00:00:00Z"
        assert entry.first_commit_sha == "abc123"


class TestModuleHistoryResult:
    """Test ModuleHistoryResult dataclass."""

    def test_result_creation(self):
        """Test creating a module history result."""
        entries = [
            ModuleHistoryEntry(
                module_name="appnexus",
                module_type="bid_adapters",
                first_version="2.15.0",
                first_major_version=2,
                file_path="modules/appnexusBidAdapter.js",
            ),
            ModuleHistoryEntry(
                module_name="google",
                module_type="analytics_adapters",
                first_version="3.0.0",
                first_major_version=3,
                file_path="modules/googleAnalyticsAdapter.js",
            ),
        ]

        modules_by_type = {
            "bid_adapters": [entries[0]],
            "analytics_adapters": [entries[1]],
        }

        modules_by_version = {2: [entries[0]], 3: [entries[1]]}

        result = ModuleHistoryResult(
            repo_name="prebid/Prebid.js",
            total_modules=2,
            modules_by_type=modules_by_type,
            modules_by_version=modules_by_version,
            metadata={"analysis_date": "2023-01-01"},
        )

        assert result.repo_name == "prebid/Prebid.js"
        assert result.total_modules == 2
        assert len(result.modules_by_type) == 2
        assert len(result.modules_by_version) == 2
        assert result.metadata["analysis_date"] == "2023-01-01"


class TestHistoryCache:
    """Test HistoryCache dataclass."""

    def test_cache_creation(self):
        """Test creating a history cache."""
        entry = ModuleHistoryEntry(
            module_name="test",
            module_type="bid_adapters",
            first_version="1.0.0",
            first_major_version=1,
            file_path="modules/testBidAdapter.js",
        )

        modules = {"test": entry}

        cache = HistoryCache(
            repo_name="test/repo",
            last_analyzed_version="1.2.0",
            modules=modules,
            metadata={"cache_date": "2023-01-01"},
        )

        assert cache.repo_name == "test/repo"
        assert cache.last_analyzed_version == "1.2.0"
        assert len(cache.modules) == 1
        assert "test" in cache.modules
        assert cache.modules["test"] == entry
        assert cache.metadata["cache_date"] == "2023-01-01"
