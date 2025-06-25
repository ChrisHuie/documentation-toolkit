"""
Tests for version caching system
"""

import json
import tempfile
from pathlib import Path

from src.repo_modules_by_version.version_cache import (
    MajorVersionInfo,
    RepoVersionCache,
    VersionCacheManager,
)


class TestMajorVersionInfo:
    """Test MajorVersionInfo dataclass."""

    def test_major_version_info_creation(self):
        """Test creating MajorVersionInfo."""
        info = MajorVersionInfo(major=9, first_version="9.0.0", last_version="9.51.0")

        assert info.major == 9
        assert info.first_version == "9.0.0"
        assert info.last_version == "9.51.0"


class TestRepoVersionCache:
    """Test RepoVersionCache dataclass."""

    def test_repo_version_cache_creation(self):
        """Test creating RepoVersionCache."""
        major_versions = {
            9: MajorVersionInfo(9, "9.0.0", "9.51.0"),
            8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
        }

        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions=major_versions,
            latest_versions=["9.51.0", "9.50.0", "9.49.1"],
        )

        assert cache.repo_name == "test/repo"
        assert cache.default_branch == "master"
        assert len(cache.major_versions) == 2
        assert cache.major_versions[9].last_version == "9.51.0"
        assert len(cache.latest_versions) == 3


class TestVersionCacheManager:
    """Test VersionCacheManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = VersionCacheManager(self.temp_dir)

        # Sample cache data
        self.major_versions = {
            9: MajorVersionInfo(9, "9.0.0", "9.51.0"),
            8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
        }

        self.sample_cache = RepoVersionCache(
            repo_name="prebid/Prebid.js",
            default_branch="master",
            major_versions=self.major_versions,
            latest_versions=["9.51.0", "9.50.0", "9.49.1", "9.49.0", "9.48.0"],
        )

    def test_cache_manager_initialization_with_custom_dir(self):
        """Test cache manager initializes with custom directory."""
        assert self.cache_manager.cache_dir == Path(self.temp_dir)
        assert self.cache_manager.cache_dir.exists()

    def test_cache_manager_initialization_with_default_dir(self):
        """Test cache manager initializes with default repo directory."""
        manager = VersionCacheManager()
        # Should point to cache/versions relative to the repo root
        assert manager.cache_dir.name == "versions"
        assert manager.cache_dir.parent.name == "cache"

    def test_get_cache_file_path(self):
        """Test cache file path generation."""
        cache_file = self.cache_manager._get_cache_file("prebid/Prebid.js")
        expected_path = Path(self.temp_dir) / "prebid_Prebid.js.json"
        assert cache_file == expected_path

    def test_save_and_load_cache(self):
        """Test saving and loading cache."""
        # Save cache
        self.cache_manager.save_cache(self.sample_cache)

        # Verify file exists
        cache_file = self.cache_manager._get_cache_file("prebid/Prebid.js")
        assert cache_file.exists()

        # Load cache
        loaded_cache = self.cache_manager.load_cache("prebid/Prebid.js")

        assert loaded_cache is not None
        assert loaded_cache.repo_name == "prebid/Prebid.js"
        assert loaded_cache.default_branch == "master"
        assert len(loaded_cache.major_versions) == 2
        assert loaded_cache.major_versions[9].last_version == "9.51.0"
        assert loaded_cache.latest_versions == [
            "9.51.0",
            "9.50.0",
            "9.49.1",
            "9.49.0",
            "9.48.0",
        ]

    def test_load_nonexistent_cache(self):
        """Test loading cache that doesn't exist."""
        cache = self.cache_manager.load_cache("nonexistent/repo")
        assert cache is None

    def test_load_invalid_cache_file(self):
        """Test loading invalid cache file."""
        # Create invalid JSON file
        cache_file = self.cache_manager._get_cache_file("invalid/repo")
        cache_file.write_text("invalid json content")

        cache = self.cache_manager.load_cache("invalid/repo")
        assert cache is None

    def test_needs_update_new_major_version(self):
        """Test cache needs update when new major version detected."""
        needs_update = self.cache_manager.needs_update(self.sample_cache, 10)
        assert needs_update is True

    def test_needs_update_same_major_version(self):
        """Test cache doesn't need update for same major version."""
        needs_update = self.cache_manager.needs_update(self.sample_cache, 9)
        assert needs_update is False

    def test_needs_update_older_major_version(self):
        """Test cache doesn't need update for older major version."""
        needs_update = self.cache_manager.needs_update(self.sample_cache, 8)
        assert needs_update is False

    def test_needs_update_empty_cache(self):
        """Test cache needs update when major_versions is empty."""
        empty_cache = RepoVersionCache(
            repo_name="empty/repo",
            default_branch="main",
            major_versions={},
            latest_versions=[],
        )

        needs_update = self.cache_manager.needs_update(empty_cache, 1)
        assert needs_update is True

    def test_clear_specific_cache(self):
        """Test clearing cache for specific repository."""
        # Save cache
        self.cache_manager.save_cache(self.sample_cache)
        cache_file = self.cache_manager._get_cache_file("prebid/Prebid.js")
        assert cache_file.exists()

        # Clear specific cache
        self.cache_manager.clear_cache("prebid/Prebid.js")
        assert not cache_file.exists()

    def test_clear_all_caches(self):
        """Test clearing all caches."""
        # Save multiple caches
        self.cache_manager.save_cache(self.sample_cache)

        cache2 = RepoVersionCache(
            repo_name="other/repo",
            default_branch="main",
            major_versions={1: MajorVersionInfo(1, "1.0.0", "1.5.0")},
            latest_versions=["1.5.0"],
        )
        self.cache_manager.save_cache(cache2)

        # Verify both exist
        assert self.cache_manager._get_cache_file("prebid/Prebid.js").exists()
        assert self.cache_manager._get_cache_file("other/repo").exists()

        # Clear all
        self.cache_manager.clear_cache()

        # Verify both are gone
        assert not self.cache_manager._get_cache_file("prebid/Prebid.js").exists()
        assert not self.cache_manager._get_cache_file("other/repo").exists()

    def test_cache_json_structure(self):
        """Test that saved cache has correct JSON structure."""
        self.cache_manager.save_cache(self.sample_cache)

        cache_file = self.cache_manager._get_cache_file("prebid/Prebid.js")
        with open(cache_file) as f:
            data = json.load(f)

        # Verify JSON structure
        assert "repo_name" in data
        assert "default_branch" in data
        assert "major_versions" in data
        assert "latest_versions" in data

        # Verify major versions are string keys (for JSON compatibility)
        assert "9" in data["major_versions"]
        assert "8" in data["major_versions"]

        # Verify major version info structure
        v9_info = data["major_versions"]["9"]
        assert v9_info["major"] == 9
        assert v9_info["first_version"] == "9.0.0"
        assert v9_info["last_version"] == "9.51.0"
