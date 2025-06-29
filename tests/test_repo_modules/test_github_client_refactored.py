"""
Tests for refactored GitHubClient with configuration-driven fetch strategies.

This test suite validates:
- Configuration-driven fetch strategy system
- Removal of hardcoded repository logic
- All fetch strategy types work correctly
- Error handling and edge cases
"""

from unittest.mock import Mock, patch

import pytest
from github import GithubException

from src.shared_utilities.github_client import GitHubClient


class TestFetchStrategies:
    """Test the configuration-driven fetch strategy system."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("src.shared_utilities.github_client.Github"):
            self.client = GitHubClient()

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_full_content(self, mock_github_class):
        """Test fetch_strategy='full_content' uses _fetch_directory_contents."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock the internal methods
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client,
                "_fetch_directory_contents",
                return_value={"file1.txt": "content"},
            ) as mock_fetch,
        ):
            result = client.fetch_repository_data(
                "test/repo", "v1.0.0", directory="src", fetch_strategy="full_content"
            )

            # Verify _fetch_directory_contents was called
            mock_fetch.assert_called_once_with(mock_repo, "src", "abc123")
            assert "files" in result
            assert result["files"] == {"file1.txt": "content"}

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_filenames_only(self, mock_github_class):
        """Test fetch_strategy='filenames_only' uses _fetch_directory_filenames."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock the internal methods
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client, "_fetch_directory_filenames", return_value={"file1.js": ""}
            ) as mock_fetch,
        ):
            result = client.fetch_repository_data(
                "test/repo",
                "v1.0.0",
                modules_path="modules",
                fetch_strategy="filenames_only",
            )

            # Verify _fetch_directory_filenames was called with .js extension
            mock_fetch.assert_called_once_with(
                mock_repo,
                "modules",
                "abc123",
                [".js"],
                20,
                0.5,
                ".test_repo_v1.0.0_modules_checkpoint.json",
                None,
            )
            assert result["files"] == {"file1.js": ""}

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_directory_names(self, mock_github_class):
        """Test fetch_strategy='directory_names' uses _fetch_directory_names."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock the internal methods
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client, "_fetch_directory_names", return_value={"dir1": "", "dir2": ""}
            ) as mock_fetch,
        ):
            result = client.fetch_repository_data(
                "test/repo",
                "v1.0.0",
                directory="adapters",
                fetch_strategy="directory_names",
            )

            # Verify _fetch_directory_names was called
            mock_fetch.assert_called_once_with(mock_repo, "adapters", "abc123")
            assert result["files"] == {"dir1": "", "dir2": ""}

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_multi_path_filenames_only(self, mock_github_class):
        """Test multi-path fetching with filenames_only strategy."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock the internal methods
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client, "_fetch_file_names", return_value={"file1.md": ""}
            ) as mock_fetch,
        ):
            result = client.fetch_repository_data(
                "test/repo",
                "v1.0.0",
                paths={"Category": "docs"},
                fetch_strategy="filenames_only",
            )

            # Verify _fetch_file_names was called for multi-path
            mock_fetch.assert_called_once_with(mock_repo, "docs", "abc123")
            assert "paths" in result
            assert result["paths"]["docs"] == {"file1.md": ""}

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_multi_path_directory_names(self, mock_github_class):
        """Test multi-path fetching with directory_names strategy."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock the internal methods
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client,
                "_fetch_directory_names",
                return_value={"subdir1": "", "subdir2": ""},
            ) as mock_fetch,
        ):
            result = client.fetch_repository_data(
                "test/repo",
                "v1.0.0",
                paths={"Adapters": "adapters", "Modules": "modules"},
                fetch_strategy="directory_names",
            )

            # Verify _fetch_directory_names was called for each path
            assert mock_fetch.call_count == 2
            assert "paths" in result
            assert len(result["paths"]) == 2

    @patch("src.shared_utilities.github_client.Github")
    def test_invalid_fetch_strategy_raises_error(self, mock_github_class):
        """Test that invalid fetch strategy raises ValueError."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        with patch.object(client, "_get_reference", return_value="abc123"):
            with pytest.raises(
                Exception, match="Unsupported fetch strategy: invalid_strategy"
            ):
                client.fetch_repository_data(
                    "test/repo",
                    "v1.0.0",
                    directory="src",
                    fetch_strategy="invalid_strategy",
                )


class TestHardcodedLogicRemoval:
    """Test that hardcoded repository-specific logic has been removed."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("src.shared_utilities.github_client.Github"):
            self.client = GitHubClient()

    @patch("src.shared_utilities.github_client.Github")
    def test_no_hardcoded_prebid_github_io_logic(self, mock_github_class):
        """Test that prebid.github.io is not treated specially in GitHubClient."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Mock internal methods to track calls
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(client, "_fetch_file_names") as mock_file_names,
            patch.object(client, "_fetch_directory_names") as mock_dir_names,
        ):
            # Test that prebid.github.io uses fetch_strategy, not hardcoded logic
            client.fetch_repository_data(
                "prebid/prebid.github.io",  # This was hardcoded before
                "v1.0.0",
                paths={"Docs": "dev-docs"},
                fetch_strategy="directory_names",  # Should use directory_names, not filenames
            )

            # Should call _fetch_directory_names because of fetch_strategy, not _fetch_file_names
            mock_dir_names.assert_called_once()
            mock_file_names.assert_not_called()

    @patch("src.shared_utilities.github_client.Github")
    def test_any_repo_can_use_any_strategy(self, mock_github_class):
        """Test that any repository can use any fetch strategy."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        test_repos = ["owner/repo1", "different/repo2", "third/repo3"]
        test_strategies = ["full_content", "filenames_only", "directory_names"]

        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(client, "_fetch_directory_contents", return_value={}),
            patch.object(client, "_fetch_directory_filenames", return_value={}),
            patch.object(client, "_fetch_directory_names", return_value={}),
        ):
            # Test that all combinations work
            for repo in test_repos:
                for strategy in test_strategies:
                    result = client.fetch_repository_data(
                        repo, "v1.0.0", directory="test", fetch_strategy=strategy
                    )

                    # Should succeed without repository-specific errors
                    assert "repo" in result
                    assert result["repo"] == repo


class TestFetchStrategyEdgeCases:
    """Test edge cases and error conditions for fetch strategies."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("src.shared_utilities.github_client.Github"):
            self.client = GitHubClient()

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_with_no_directory(self, mock_github_class):
        """Test fetch strategy with no directory specified raises appropriate error."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        with patch.object(client, "_get_reference", return_value="abc123"):
            with pytest.raises(Exception, match="No directory specified"):
                client.fetch_repository_data(
                    "test/repo",
                    "v1.0.0",
                    # No directory, modules_path, or paths specified
                    fetch_strategy="full_content",
                )

    @patch("src.shared_utilities.github_client.Github")
    def test_fetch_strategy_with_github_exception(self, mock_github_class):
        """Test fetch strategy error handling with GitHub exceptions."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        # Create a custom exception class for testing
        class TestGithubException(GithubException):
            def __init__(self):
                super().__init__(404, "Not found")
                self._data = {"message": "Repository not found"}

            @property
            def data(self):
                return self._data

        # Mock _fetch_directory_contents to raise GitHub exception
        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client, "_fetch_directory_contents", side_effect=TestGithubException()
            ),
        ):
            with pytest.raises(Exception, match="GitHub API error"):
                client.fetch_repository_data(
                    "test/repo",
                    "v1.0.0",
                    directory="nonexistent",
                    fetch_strategy="full_content",
                )

    @patch("src.shared_utilities.github_client.Github")
    def test_default_fetch_strategy(self, mock_github_class):
        """Test that default fetch_strategy is 'full_content'."""
        # Setup mocks
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient()

        with (
            patch.object(client, "_get_reference", return_value="abc123"),
            patch.object(
                client, "_fetch_directory_contents", return_value={}
            ) as mock_fetch,
        ):
            # Don't specify fetch_strategy - should default to full_content
            client.fetch_repository_data(
                "test/repo",
                "v1.0.0",
                directory="src",
                # fetch_strategy not specified
            )

            # Should call _fetch_directory_contents (full_content strategy)
            mock_fetch.assert_called_once()
