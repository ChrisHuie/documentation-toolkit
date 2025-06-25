"""
Pytest configuration and shared fixtures.
"""

from unittest.mock import Mock

import pytest

from src.repo_modules_by_version.config import RepoConfig


@pytest.fixture
def sample_repo_config():
    """Sample repository configuration for testing."""
    return RepoConfig(
        repo="test/repo",
        directory="docs",
        description="Test repository",
        versions=["v1.0.0", "main"],
        parser_type="default",
    )


@pytest.fixture
def sample_github_data():
    """Sample GitHub API response data for testing."""
    return {
        "repo": "test/repo",
        "version": "v1.0.0",
        "directory": "docs",
        "files": {
            "docs/README.md": "# Test Documentation\n\nThis is a test.",
            "docs/api.md": "# API Reference\n\n## Methods\n\n### get_data()",
        },
        "metadata": {"commit_sha": "abc123", "total_files": 2},
    }


@pytest.fixture
def mock_github_repo():
    """Mock GitHub repository object."""
    repo = Mock()
    repo.name = "repo"
    repo.full_name = "test/repo"
    repo.description = "Test repository"
    repo.default_branch = "main"
    repo.language = "Python"
    repo.get_topics.return_value = ["documentation", "testing"]
    return repo


@pytest.fixture
def mock_github_content():
    """Mock GitHub content file object."""
    content = Mock()
    content.path = "docs/test.md"
    content.type = "file"
    content.encoding = "base64"
    content.decoded_content = b"# Test\nContent"
    content.name = "test.md"
    return content
