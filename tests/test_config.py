"""
Tests for the config module.
"""

import pytest

from src.repo_modules_by_version.config import (
    RepoConfig,
    add_repo_config,
    get_available_repos,
    get_repo_config,
)


class TestRepoConfig:
    """Test RepoConfig dataclass."""

    def test_repo_config_creation(self):
        """Test RepoConfig can be created with required fields."""
        config = RepoConfig(
            repo="owner/repo",
            directory="docs",
            description="Test repo",
            versions=["v1.0.0"],
        )
        assert config.repo == "owner/repo"
        assert config.directory == "docs"
        assert config.description == "Test repo"
        assert config.versions == ["v1.0.0"]
        assert config.parser_type == "default"

    def test_repo_config_with_custom_parser(self):
        """Test RepoConfig can be created with custom parser type."""
        config = RepoConfig(
            repo="owner/repo",
            directory="docs",
            description="Test repo",
            versions=["v1.0.0"],
            parser_type="markdown",
        )
        assert config.parser_type == "markdown"


class TestGetAvailableRepos:
    """Test get_available_repos function."""

    def test_returns_dict_of_repo_configs(self):
        """Test that get_available_repos returns a dictionary of RepoConfig objects."""
        repos = get_available_repos()
        assert isinstance(repos, dict)

        for name, config in repos.items():
            assert isinstance(name, str)
            assert isinstance(config, RepoConfig)

    def test_contains_expected_default_repos(self):
        """Test that default repositories are included."""
        repos = get_available_repos()

        # Check that we have some repositories configured
        assert len(repos) > 0

        # Check that each repo has the required fields
        for config in repos.values():
            assert config.repo
            assert config.directory is not None  # Can be empty string
            assert config.description
            assert isinstance(config.versions, list)
            assert config.parser_type


class TestGetRepoConfig:
    """Test get_repo_config function."""

    def test_get_existing_repo_config(self):
        """Test getting configuration for an existing repository."""
        available_repos = get_available_repos()
        if available_repos:
            repo_name = list(available_repos.keys())[0]
            config = get_repo_config(repo_name)
            assert isinstance(config, RepoConfig)
            assert config == available_repos[repo_name]

    def test_get_nonexistent_repo_config_raises_error(self):
        """Test that getting a non-existent repo raises ValueError."""
        with pytest.raises(ValueError, match="Repository 'nonexistent' not found"):
            get_repo_config("nonexistent")


class TestAddRepoConfig:
    """Test add_repo_config function."""

    def test_add_repo_config_exists(self):
        """Test that add_repo_config function exists and can be called."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test",
            versions=["v1.0.0"],
        )

        # Function should exist and not raise an error when called
        # Currently it's a placeholder implementation
        add_repo_config("test", config)
