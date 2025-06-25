"""
Tests for updated config with Prebid repositories
"""

from unittest.mock import Mock, patch

import pytest

from src.repo_modules_by_version.config import (
    get_available_repos,
    get_repo_config,
    get_repo_config_with_versions,
)


class TestPrebidRepoConfig:
    """Test configuration for Prebid repositories."""

    def test_get_available_repos_structure(self):
        """Test that available repos have correct structure."""
        repos = get_available_repos()

        # Should have 4 Prebid repos
        assert len(repos) == 4
        assert "prebid-js" in repos
        assert "prebid-server-java" in repos
        assert "prebid-server" in repos
        assert "prebid-docs" in repos

    def test_prebid_js_config(self):
        """Test Prebid.js configuration."""
        repos = get_available_repos()
        config = repos["prebid-js"]

        assert config.repo == "prebid/Prebid.js"
        assert config.directory == "modules"
        assert config.description == "Prebid.js - Header bidding wrapper for publishers"
        assert config.parser_type == "default"
        assert "master" in config.versions

    def test_prebid_server_java_config(self):
        """Test Prebid Server Java configuration."""
        repos = get_available_repos()
        config = repos["prebid-server-java"]

        assert config.repo == "prebid/prebid-server-java"
        assert config.directory == "src/main/java/org/prebid/server"
        assert config.description == "Prebid Server Java implementation"
        assert config.parser_type == "default"
        assert "master" in config.versions

    def test_prebid_server_go_config(self):
        """Test Prebid Server Go configuration."""
        repos = get_available_repos()
        config = repos["prebid-server"]

        assert config.repo == "prebid/prebid-server"
        assert config.directory == "adapters"
        assert config.description == "Prebid Server Go implementation"
        assert config.parser_type == "default"
        assert "master" in config.versions

    def test_prebid_docs_config(self):
        """Test Prebid documentation configuration."""
        repos = get_available_repos()
        config = repos["prebid-docs"]

        assert config.repo == "prebid/prebid.github.io"
        assert config.directory == "dev-docs"
        assert config.description == "Prebid documentation site"
        assert config.parser_type == "markdown"
        assert config.versions == ["master"]  # Special case - no semantic versioning

    def test_get_repo_config_existing(self):
        """Test getting configuration for existing repository."""
        config = get_repo_config("prebid-js")

        assert config.repo == "prebid/Prebid.js"
        assert config.directory == "modules"

    def test_get_repo_config_nonexistent(self):
        """Test getting configuration for non-existent repository."""
        with pytest.raises(ValueError, match="Repository 'nonexistent' not found"):
            get_repo_config("nonexistent")

    @patch("src.repo_modules_by_version.config.GitHubClient")
    def test_get_repo_config_with_versions_prebid_js(self, mock_client_class):
        """Test getting Prebid.js config with dynamic versions."""
        # Mock GitHubClient
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_semantic_versions.return_value = [
            "master",
            "9.51.0",
            "9.50.0",
            "9.0.0",
            "8.52.2",
            "8.0.0",
        ]

        config = get_repo_config_with_versions("prebid-js")

        assert config.repo == "prebid/Prebid.js"
        assert len(config.versions) == 6
        assert "master" in config.versions
        assert "9.51.0" in config.versions

        # Should have called GitHub client
        mock_client.get_semantic_versions.assert_called_once_with("prebid/Prebid.js")

    @patch("src.repo_modules_by_version.config.GitHubClient")
    def test_get_repo_config_with_versions_prebid_docs(self, mock_client_class):
        """Test getting Prebid docs config (should skip version discovery)."""
        # Mock GitHubClient (should not be called)
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        config = get_repo_config_with_versions("prebid-docs")

        assert config.repo == "prebid/prebid.github.io"
        assert config.versions == ["master"]

        # Should NOT have called GitHub client
        mock_client.get_semantic_versions.assert_not_called()

    @patch("src.repo_modules_by_version.config.GitHubClient")
    def test_get_repo_config_with_versions_fallback_on_error(self, mock_client_class):
        """Test fallback when version discovery fails."""
        # Mock GitHubClient to raise exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_semantic_versions.side_effect = Exception("API error")

        config = get_repo_config_with_versions("prebid-js")

        # Should return original config with fallback versions
        assert config.repo == "prebid/Prebid.js"
        assert "master" in config.versions

    def test_get_repo_config_with_versions_nonexistent(self):
        """Test getting config with versions for non-existent repository."""
        with pytest.raises(ValueError, match="Repository 'nonexistent' not found"):
            get_repo_config_with_versions("nonexistent")

    def test_all_repos_have_required_fields(self):
        """Test that all repository configurations have required fields."""
        repos = get_available_repos()

        for config in repos.values():
            assert isinstance(config.repo, str)
            assert "/" in config.repo  # Should be in owner/repo format
            assert isinstance(config.directory, str)
            assert isinstance(config.description, str)
            assert isinstance(config.versions, list)
            assert len(config.versions) > 0
            assert isinstance(config.parser_type, str)
            assert config.parser_type in ["default", "markdown", "openapi"]

    def test_repo_naming_consistency(self):
        """Test that repository names follow consistent patterns."""
        repos = get_available_repos()

        # All Prebid repos should start with "prebid-" except docs
        for name, config in repos.items():
            if name != "prebid-docs":
                assert name.startswith("prebid-")

            # All actual repos should be under "prebid/" org
            assert config.repo.startswith("prebid/")

    def test_directory_paths_are_valid(self):
        """Test that directory paths are reasonable."""
        repos = get_available_repos()

        for name, config in repos.items():
            # Directory should not start with /
            assert not config.directory.startswith("/")

            # Directory should not be empty for server repos
            if "server" in name:
                assert len(config.directory) > 0
