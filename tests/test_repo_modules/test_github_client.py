"""
Tests for the github_client module.
"""

import os
from unittest.mock import Mock, patch

import pytest
from github import GithubException

from src.repo_modules.github_client import GitHubClient


class TestGitHubClientInit:
    """Test GitHubClient initialization."""

    @patch("src.repo_modules.github_client.Github")
    def test_init_with_token(self, mock_github):
        """Test initialization with explicit token."""
        client = GitHubClient(token="test_token")
        assert client.token == "test_token"
        mock_github.assert_called_once_with("test_token")

    @patch("src.repo_modules.github_client.Github")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"})
    def test_init_with_env_token(self, mock_github):
        """Test initialization with environment variable token."""
        client = GitHubClient()
        assert client.token == "env_token"
        mock_github.assert_called_once_with("env_token")

    @patch("src.repo_modules.github_client.Github")
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_token(self, mock_github):
        """Test initialization without token (unauthenticated)."""
        client = GitHubClient()
        assert client.token is None
        mock_github.assert_called_once_with()


class TestFetchRepositoryData:
    """Test fetch_repository_data method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GitHubClient(token="test_token")
        self.mock_repo = Mock()
        self.client.github = Mock()
        self.client.github.get_repo.return_value = self.mock_repo

    def test_successful_fetch(self):
        """Test successful repository data fetch."""
        # Mock the _get_reference method
        with patch.object(self.client, "_get_reference", return_value="commit_sha"):
            # Mock the _fetch_directory_contents method
            with patch.object(
                self.client,
                "_fetch_directory_contents",
                return_value={"file1.txt": "content1", "file2.txt": "content2"},
            ):
                result = self.client.fetch_repository_data(
                    "owner/repo", "v1.0.0", "docs"
                )

                expected = {
                    "repo": "owner/repo",
                    "version": "v1.0.0",
                    "directory": "docs",
                    "files": {"file1.txt": "content1", "file2.txt": "content2"},
                    "metadata": {"commit_sha": "commit_sha", "total_files": 2},
                }

                assert result == expected
                self.client.github.get_repo.assert_called_once_with("owner/repo")

    def test_github_exception_handling(self):
        """Test handling of GitHub API exceptions."""
        self.client.github.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )

        with pytest.raises(Exception, match="GitHub API error: Not Found"):
            self.client.fetch_repository_data("owner/repo", "v1.0.0", "docs")

    def test_general_exception_handling(self):
        """Test handling of general exceptions."""
        self.client.github.get_repo.side_effect = ValueError("Test error")

        with pytest.raises(
            Exception, match="Error fetching repository data: Test error"
        ):
            self.client.fetch_repository_data("owner/repo", "v1.0.0", "docs")


class TestGetReference:
    """Test _get_reference method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GitHubClient(token="test_token")
        self.mock_repo = Mock()

    def test_get_reference_as_branch(self):
        """Test getting reference as branch."""
        mock_branch = Mock()
        mock_branch.commit.sha = "branch_sha"
        self.mock_repo.get_branch.return_value = mock_branch

        result = self.client._get_reference(self.mock_repo, "main")
        assert result == "branch_sha"

    def test_get_reference_as_tag(self):
        """Test getting reference as tag when branch fails."""
        self.mock_repo.get_branch.side_effect = GithubException(404, {}, None)

        mock_ref = Mock()
        mock_ref.object.sha = "tag_sha"
        self.mock_repo.get_git_ref.return_value = mock_ref

        result = self.client._get_reference(self.mock_repo, "v1.0.0")
        assert result == "tag_sha"

    def test_get_reference_as_commit(self):
        """Test getting reference as commit SHA when branch and tag fail."""
        self.mock_repo.get_branch.side_effect = GithubException(404, {}, None)
        self.mock_repo.get_git_ref.side_effect = GithubException(404, {}, None)

        mock_commit = Mock()
        mock_commit.sha = "commit_sha"
        self.mock_repo.get_commit.return_value = mock_commit

        result = self.client._get_reference(self.mock_repo, "abc123")
        assert result == "commit_sha"

    def test_get_reference_not_found(self):
        """Test exception when reference is not found."""
        self.mock_repo.get_branch.side_effect = GithubException(404, {}, None)
        self.mock_repo.get_git_ref.side_effect = GithubException(404, {}, None)
        self.mock_repo.get_commit.side_effect = GithubException(404, {}, None)

        with pytest.raises(Exception, match="Could not find reference 'invalid'"):
            self.client._get_reference(self.mock_repo, "invalid")


class TestGetFileContent:
    """Test _get_file_content method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GitHubClient(token="test_token")

    def test_get_base64_encoded_content(self):
        """Test getting base64 encoded content."""
        mock_content = Mock()
        mock_content.encoding = "base64"
        mock_content.decoded_content = b"Hello, World!"
        mock_content.name = "test.txt"

        result = self.client._get_file_content(mock_content)
        assert result == "Hello, World!"

    def test_get_plain_content(self):
        """Test getting plain text content."""
        mock_content = Mock()
        mock_content.encoding = "utf-8"
        mock_content.content = "Plain text content"
        mock_content.name = "test.txt"

        result = self.client._get_file_content(mock_content)
        assert result == "Plain text content"

    def test_unicode_decode_error_handling(self):
        """Test handling of Unicode decode errors."""
        mock_content = Mock()
        mock_content.encoding = "base64"
        mock_content.decoded_content = b"\xff\xfe"  # Invalid UTF-8
        mock_content.name = "binary.bin"

        result = self.client._get_file_content(mock_content)
        assert result == "[Binary file: binary.bin]"

    def test_general_error_handling(self):
        """Test handling of general errors."""
        mock_content = Mock()
        mock_content.encoding = "base64"
        mock_content.decoded_content.decode.side_effect = Exception("Read error")
        mock_content.name = "error.txt"

        result = self.client._get_file_content(mock_content)
        assert result == "[Error reading file error.txt: Read error]"


class TestRepositoryInfo:
    """Test repository info methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = GitHubClient(token="test_token")
        self.client.github = Mock()

    def test_get_repository_info(self, mock_github_repo):
        """Test getting repository information."""
        self.client.github.get_repo.return_value = mock_github_repo

        result = self.client.get_repository_info("test/repo")

        expected = {
            "name": "repo",
            "full_name": "test/repo",
            "description": "Test repository",
            "default_branch": "main",
            "language": "Python",
            "topics": ["documentation", "testing"],
        }

        assert result == expected

    def test_list_branches(self):
        """Test listing repository branches."""
        mock_repo = Mock()
        mock_branch1 = Mock()
        mock_branch1.name = "main"
        mock_branch2 = Mock()
        mock_branch2.name = "develop"
        mock_repo.get_branches.return_value = [mock_branch1, mock_branch2]

        self.client.github.get_repo.return_value = mock_repo

        result = self.client.list_branches("test/repo")
        assert result == ["main", "develop"]

    def test_list_tags(self):
        """Test listing repository tags."""
        mock_repo = Mock()
        mock_tag1 = Mock()
        mock_tag1.name = "v1.0.0"
        mock_tag2 = Mock()
        mock_tag2.name = "v2.0.0"
        mock_repo.get_tags.return_value = [mock_tag1, mock_tag2]

        self.client.github.get_repo.return_value = mock_repo

        result = self.client.list_tags("test/repo")
        assert result == ["v1.0.0", "v2.0.0"]
