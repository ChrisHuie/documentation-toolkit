"""
GitHub API client for fetching repository data
"""

import os
from typing import Any

from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: str | None = None):
        """Initialize GitHub client with optional token."""
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if self.token:
            self.github = Github(self.token)
        else:
            # Use unauthenticated client (rate limited)
            self.github = Github()

    def fetch_repository_data(
        self, repo_name: str, version: str, directory: str
    ) -> dict[str, Any]:
        """
        Fetch repository data for a specific version and directory.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository

        Returns:
            Dictionary containing file paths and content
        """
        try:
            repo = self.github.get_repo(repo_name)

            # Get the commit/reference
            ref = self._get_reference(repo, version)

            # Fetch directory contents
            files_data = self._fetch_directory_contents(repo, directory, ref)

            return {
                "repo": repo_name,
                "version": version,
                "directory": directory,
                "files": files_data,
                "metadata": {"commit_sha": ref, "total_files": len(files_data)},
            }

        except GithubException as e:
            raise Exception(f"GitHub API error: {e.data.get('message', str(e))}") from e
        except Exception as e:
            raise Exception(f"Error fetching repository data: {str(e)}") from e

    def _get_reference(self, repo: Repository, version: str) -> str:
        """Get the commit SHA for a given version reference."""
        try:
            # Try as branch first
            branch = repo.get_branch(version)
            return branch.commit.sha
        except GithubException:
            pass

        try:
            # Try as tag
            ref = repo.get_git_ref(f"tags/{version}")
            return ref.object.sha
        except GithubException:
            pass

        try:
            # Try as commit SHA
            commit = repo.get_commit(version)
            return commit.sha
        except GithubException as e:
            raise Exception(
                f"Could not find reference '{version}' in repository"
            ) from e

    def _fetch_directory_contents(
        self, repo: Repository, directory: str, ref: str
    ) -> dict[str, str]:
        """
        Recursively fetch all files from a directory.

        Returns:
            Dictionary mapping file paths to their content
        """
        files_data = {}

        try:
            contents = repo.get_contents(directory, ref=ref)

            # Handle single file case
            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "file":
                    # Fetch file content
                    file_content = self._get_file_content(content)
                    files_data[content.path] = file_content
                elif content.type == "dir":
                    # Recursively fetch subdirectory
                    subdir_files = self._fetch_directory_contents(
                        repo, content.path, ref
                    )
                    files_data.update(subdir_files)

        except GithubException as e:
            if e.status == 404:
                raise Exception(
                    f"Directory '{directory}' not found in repository"
                ) from e
            raise Exception(
                f"Error accessing directory '{directory}': {e.data.get('message', str(e))}"
            ) from e

        return files_data

    def _get_file_content(self, content_file: ContentFile) -> str:
        """Get decoded content from a ContentFile object."""
        try:
            # Handle text files
            if content_file.encoding == "base64":
                return content_file.decoded_content.decode("utf-8")
            else:
                return content_file.content
        except UnicodeDecodeError:
            # Handle binary files or unsupported encodings
            return f"[Binary file: {content_file.name}]"
        except Exception as e:
            return f"[Error reading file {content_file.name}: {str(e)}]"

    def get_repository_info(self, repo_name: str) -> dict[str, Any]:
        """Get basic repository information."""
        try:
            repo = self.github.get_repo(repo_name)
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "topics": list(repo.get_topics()),
            }
        except GithubException as e:
            raise Exception(
                f"Error fetching repository info: {e.data.get('message', str(e))}"
            ) from e

    def list_branches(self, repo_name: str) -> list[str]:
        """List all branches in a repository."""
        try:
            repo = self.github.get_repo(repo_name)
            return [branch.name for branch in repo.get_branches()]
        except GithubException as e:
            raise Exception(
                f"Error listing branches: {e.data.get('message', str(e))}"
            ) from e

    def list_tags(self, repo_name: str) -> list[str]:
        """List all tags in a repository."""
        try:
            repo = self.github.get_repo(repo_name)
            return [tag.name for tag in repo.get_tags()]
        except GithubException as e:
            raise Exception(
                f"Error listing tags: {e.data.get('message', str(e))}"
            ) from e
