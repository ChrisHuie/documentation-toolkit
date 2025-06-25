"""
Tests for the config module.
"""

import json
from unittest.mock import mock_open, patch

import pytest

from src.repo_modules_by_version.config import (
    RepoConfig,
    add_repo_config,
    get_available_repos,
    get_repo_config,
)

# Sample JSON content to be used in mocks
SAMPLE_REPOS_JSON = """
{
    "prebid-js": {
        "repo": "prebid/Prebid.js",
        "directory": "modules",
        "description": "Prebid.js - Header bidding wrapper for publishers",
        "versions": ["master"],
        "parser_type": "default"
    },
    "prebid-server": {
        "repo": "prebid/prebid-server",
        "directory": "adapters",
        "description": "Prebid Server Go implementation",
        "versions": ["master"],
        "parser_type": "default"
    }
}
"""

MOCK_CONFIG_PATH = "src.repo_modules_by_version.config.CONFIG_FILE"


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


@patch(f"{MOCK_CONFIG_PATH}.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_REPOS_JSON)
class TestGetAvailableRepos:
    """Test get_available_repos function with mocked file."""

    def test_returns_dict_of_repo_configs(self, mock_file, mock_exists):
        """Test that get_available_repos returns a dictionary of RepoConfig objects."""
        repos = get_available_repos()
        assert isinstance(repos, dict)
        assert len(repos) == 2

        for name, config in repos.items():
            assert isinstance(name, str)
            assert isinstance(config, RepoConfig)

    def test_contains_expected_repos(self, mock_file, mock_exists):
        """Test that the correct repos are loaded from the mock JSON."""
        repos = get_available_repos()
        assert "prebid-js" in repos
        assert "prebid-server" in repos
        assert repos["prebid-js"].repo == "prebid/Prebid.js"


@patch(f"{MOCK_CONFIG_PATH}.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_REPOS_JSON)
class TestGetRepoConfig:
    """Test get_repo_config function with mocked file."""

    def test_get_existing_repo_config(self, mock_file, mock_exists):
        """Test getting configuration for an existing repository."""
        config = get_repo_config("prebid-js")
        assert isinstance(config, RepoConfig)
        assert config.repo == "prebid/Prebid.js"

    def test_get_nonexistent_repo_config_raises_error(self, mock_file, mock_exists):
        """Test that getting a non-existent repo raises ValueError."""
        with pytest.raises(ValueError, match="Repository 'nonexistent' not found"):
            get_repo_config("nonexistent")


@patch(f"{MOCK_CONFIG_PATH}.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_REPOS_JSON)
class TestAddRepoConfig:
    """Test add_repo_config function with mocked file."""

    def test_add_new_repo_config(self, mock_file, mock_exists):
        """Test that add_repo_config writes the new config to the file."""
        new_config = RepoConfig(
            repo="test/new-repo",
            directory="src",
            description="A new test repo",
            versions=["1.0"],
            parser_type="default",
        )

        add_repo_config("new-repo", new_config)

        # Check that open was called in write mode to the correct path
        # The mock_open needs to be configured to handle the path object
        mock_file.assert_called_with("src/repo_modules_by_version/repos.json", "w")

        # Check that the written data is correct
        handle = mock_file()
        written_data = handle.write.call_args[0][0]

        expected_data = json.loads(SAMPLE_REPOS_JSON)
        expected_data["new-repo"] = {
            "repo": "test/new-repo",
            "directory": "src",
            "description": "A new test repo",
            "versions": ["1.0"],
            "parser_type": "default",
        }

        assert json.loads(written_data) == expected_data

    def test_update_existing_repo_config(self, mock_file, mock_exists):
        """Test that add_repo_config updates an existing config."""
        updated_config = RepoConfig(
            repo="prebid/Prebid.js",
            directory="modules/updated",
            description="Updated description",
            versions=["master", "9.0"],
            parser_type="default",
        )

        add_repo_config("prebid-js", updated_config)

        handle = mock_file()
        written_data = handle.write.call_args[0][0]

        expected_data = json.loads(SAMPLE_REPOS_JSON)
        expected_data["prebid-js"] = {
            "repo": "prebid/Prebid.js",
            "directory": "modules/updated",
            "description": "Updated description",
            "versions": ["master", "9.0"],
            "parser_type": "default",
        }

        assert json.loads(written_data) == expected_data
