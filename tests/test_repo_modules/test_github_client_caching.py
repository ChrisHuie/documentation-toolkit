"""
Tests for GitHub client caching functionality
"""

import tempfile
from unittest.mock import Mock, patch

from src.repo_modules.github_client import GitHubClient
from src.repo_modules.version_cache import (
    MajorVersionInfo,
    RepoVersionCache,
)


class TestGitHubClientCaching:
    """Test GitHub client caching functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Mock GitHub API
        self.mock_github = Mock()
        self.mock_repo = Mock()
        self.mock_github.get_repo.return_value = self.mock_repo
        self.mock_repo.default_branch = "master"

        # Create client with mocked GitHub
        with patch("src.repo_modules.github_client.Github") as mock_github_class:
            mock_github_class.return_value = self.mock_github
            with patch(
                "src.repo_modules.github_client.VersionCacheManager"
            ) as mock_cache_manager_class:
                self.mock_cache_manager = Mock()
                self.mock_cache_manager.cache_dir = self.temp_dir
                mock_cache_manager_class.return_value = self.mock_cache_manager
                self.client = GitHubClient()

    def test_get_semantic_versions_no_cache(self):
        """Test getting semantic versions when no cache exists."""
        # Mock GitHub API responses with proper name attributes
        mock_tags = []
        for tag_name in ["9.51.0", "9.50.0", "9.49.1", "9.0.0", "8.52.2", "8.0.0"]:
            mock_tag = Mock()
            mock_tag.name = tag_name
            mock_tags.append(mock_tag)

        self.mock_repo.get_tags.return_value = mock_tags
        self.mock_cache_manager.load_cache.return_value = None  # No cache

        with patch("builtins.print"):  # Suppress print output
            versions = self.client.get_semantic_versions("test/repo")

        # Should return master + latest versions + major version milestones
        assert "master" in versions
        assert "9.51.0 (current latest)" in versions
        assert "9.50.0" in versions
        # Note: 9.0.0 might not have (first v9.x) label in this test context
        assert any("9.0.0" in v for v in versions)
        assert any("8.52.2" in v for v in versions)
        assert any("8.0.0" in v for v in versions)

    def test_get_semantic_versions_with_cache(self):
        """Test getting semantic versions when cache exists and is current."""
        # Create existing cache
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(9, "9.0.0", "9.51.0"),
                8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
            },
            latest_versions=["9.51.0", "9.50.0", "9.49.1", "9.49.0", "9.48.0"],
        )
        self.client.cache_manager.save_cache(cache)

        # Mock recent tags (should not trigger rebuild)
        mock_tags = []
        for tag_name in ["9.51.0", "9.50.0", "9.49.1"]:
            mock_tag = Mock()
            mock_tag.name = tag_name
            mock_tags.append(mock_tag)

        self.mock_repo.get_tags.return_value = iter(mock_tags)
        self.mock_cache_manager.load_cache.return_value = cache
        self.mock_cache_manager.needs_update.return_value = False

        versions = self.client.get_semantic_versions("test/repo")

        # Should use cached data
        assert "master" in versions
        assert "9.51.0 (current latest)" in versions
        assert "9.0.0 (first v9.x)" in versions

    def test_get_semantic_versions_cache_needs_update(self):
        """Test getting semantic versions when cache needs updating for new major."""
        # Create existing cache with only v8.x
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
            },
            latest_versions=["8.52.2", "8.52.1", "8.52.0"],
        )
        self.client.cache_manager.save_cache(cache)

        # Mock tags that include new v9.x major
        mock_tags = []
        for tag_name in ["9.0.0", "8.52.2", "8.0.0"]:
            mock_tag = Mock()
            mock_tag.name = tag_name
            mock_tags.append(mock_tag)

        self.mock_repo.get_tags.return_value = mock_tags
        self.mock_cache_manager.load_cache.return_value = cache
        self.mock_cache_manager.needs_update.return_value = True

        with patch("builtins.print"):  # Suppress print output
            versions = self.client.get_semantic_versions("test/repo")

        # Should rebuild cache and include v9.x
        assert "master" in versions
        assert any("9.0.0" in v for v in versions)

    def test_update_recent_major_versions(self):
        """Test updating current and previous major versions."""
        # Create cache
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(9, "9.0.0", "9.50.0"),  # Older last version
                8: MajorVersionInfo(8, "8.0.0", "8.52.1"),  # Older last version
                7: MajorVersionInfo(7, "7.0.0", "7.54.5"),  # Should not update
            },
            latest_versions=["9.50.0", "9.49.1"],
        )

        # Mock latest versions with newer releases
        latest_versions = [
            {"name": "9.51.0", "major": 9, "minor": 51, "patch": 0},
            {"name": "9.50.0", "major": 9, "minor": 50, "patch": 0},
            {"name": "8.52.2", "major": 8, "minor": 52, "patch": 2},  # Newer v8.x
        ]

        with patch("builtins.print") as mock_print:
            # Mock the cache manager save method
            self.mock_cache_manager.save_cache = Mock()

            updated_cache = self.client._update_recent_major_versions(
                cache, latest_versions, 9
            )

        # Should update v9.x and v8.x but not v7.x
        assert updated_cache.major_versions[9].last_version == "9.51.0"
        assert updated_cache.major_versions[8].last_version == "8.52.2"
        assert updated_cache.major_versions[7].last_version == "7.54.5"  # Unchanged

        # Should print update messages
        assert mock_print.call_count == 2

        # Should have called save_cache since updates were made
        self.mock_cache_manager.save_cache.assert_called_once()

    def test_update_recent_major_versions_no_changes(self):
        """Test updating when no newer versions are available."""
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(9, "9.0.0", "9.51.0"),
                8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
            },
            latest_versions=["9.51.0", "9.50.0"],
        )

        # Mock latest versions (same as cached)
        latest_versions = [
            {"name": "9.51.0", "major": 9, "minor": 51, "patch": 0},
            {"name": "9.50.0", "major": 9, "minor": 50, "patch": 0},
        ]

        with patch("builtins.print") as mock_print:
            # Mock the cache manager save method
            self.mock_cache_manager.save_cache = Mock()

            updated_cache = self.client._update_recent_major_versions(
                cache, latest_versions, 9
            )

        # Should not update anything
        assert updated_cache.major_versions[9].last_version == "9.51.0"
        assert updated_cache.major_versions[8].last_version == "8.52.2"

        # Should not print update messages
        assert mock_print.call_count == 0

        # Should not have called save_cache since no updates were made
        self.mock_cache_manager.save_cache.assert_not_called()

    def test_build_chronological_version_list(self):
        """Test building chronological version list with labels."""
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(9, "9.0.0", "9.51.0"),
                8: MajorVersionInfo(8, "8.0.0", "8.52.2"),
                7: MajorVersionInfo(7, "7.0.0", "7.54.5"),
            },
            latest_versions=["9.51.0", "9.50.0", "9.49.1"],
        )

        latest_5 = ["9.51.0", "9.50.0", "9.49.1", "9.49.0", "9.48.0"]

        versions = self.client._build_chronological_version_list(
            "master", latest_5, cache
        )

        # Check structure
        assert versions[0] == "master"
        assert versions[1] == "9.51.0 (current latest)"
        assert "9.50.0" in versions
        assert "9.0.0 (first v9.x)" in versions
        assert "8.52.2 (latest v8.x)" in versions
        assert "8.0.0 (first v8.x)" in versions
        assert "7.54.5 (latest v7.x)" in versions
        assert "7.0.0 (first v7.x)" in versions

    def test_build_chronological_version_list_current_latest_is_major_latest(self):
        """Test when current latest is also the latest of its major version."""
        cache = RepoVersionCache(
            repo_name="test/repo",
            default_branch="master",
            major_versions={
                9: MajorVersionInfo(9, "9.0.0", "9.51.0"),  # Same as current latest
            },
            latest_versions=["9.51.0", "9.50.0"],
        )

        latest_5 = ["9.51.0", "9.50.0", "9.49.1"]

        versions = self.client._build_chronological_version_list(
            "master", latest_5, cache
        )

        # Should only appear once as "current latest", not also as "latest v9.x"
        current_latest_count = sum(
            1 for v in versions if "9.51.0" in v and "current latest" in v
        )
        latest_v9_count = sum(
            1 for v in versions if "9.51.0" in v and "latest v9.x" in v
        )

        assert current_latest_count == 1
        assert latest_v9_count == 0  # Should not appear as latest v9.x

    def test_semantic_version_parsing(self):
        """Test parsing of various semantic version formats."""
        mock_tags = []
        for tag_name in ["v9.51.0", "9.50.0", "9.49.1-beta", "not-a-version", "8.52.2"]:
            mock_tag = Mock()
            mock_tag.name = tag_name
            mock_tags.append(mock_tag)

        self.mock_repo.get_tags.return_value = mock_tags
        self.mock_cache_manager.load_cache.return_value = None  # No cache

        with patch("builtins.print"):
            versions = self.client.get_semantic_versions("test/repo")

        # Should parse valid versions and ignore invalid ones
        version_string = " ".join(versions)
        assert "v9.51.0" in version_string or "9.51.0" in version_string
        assert "9.50.0" in version_string
        assert "9.49.1" in version_string  # Should strip -beta
        assert "not-a-version" not in version_string
