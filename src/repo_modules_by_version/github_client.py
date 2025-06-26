"""
GitHub API client for fetching repository data
"""

import os
import re
from typing import Any

from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository

from .version_cache import MajorVersionInfo, RepoVersionCache, VersionCacheManager


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

        # Initialize version cache manager
        self.cache_manager = VersionCacheManager()

    def fetch_repository_data(
        self,
        repo_name: str,
        version: str,
        directory: str | None = None,
        modules_path: str | None = None,
        paths: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Fetch repository data for a specific version and directory/directories.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository (for backward compatibility)
            modules_path: Optional additional directory path for modules
            paths: Dictionary of category names to directory paths (for multi-directory parsing)

        Returns:
            Dictionary containing file paths and content
        """
        try:
            repo = self.github.get_repo(repo_name)

            # Get the commit/reference
            ref = self._get_reference(repo, version)

            # Handle multi-path fetching for new parsers like prebid-server
            if paths:
                paths_data = {}
                all_files = {}
                total_files = 0

                for path in paths.values():
                    # For multi-path parsing, fetch directory names or file names depending on repo
                    if repo_name == "prebid/prebid.github.io":
                        # For docs repo, we need file names not directory names
                        path_items = self._fetch_file_names(repo, path, ref)
                    else:
                        # For other repos, fetch directory names (much faster)
                        path_items = self._fetch_directory_names(repo, path, ref)
                    paths_data[path] = path_items
                    all_files.update(path_items)
                    total_files += len(path_items)

                return {
                    "repo": repo_name,
                    "version": version,
                    "paths": paths_data,
                    "files": all_files,
                    "metadata": {"commit_sha": ref, "total_files": total_files},
                }

            # Handle legacy single directory/modules_path
            target_directory = modules_path if modules_path else directory

            if not target_directory:
                raise Exception("No directory specified for repository parsing")

            if modules_path:
                # For modules parsing, only fetch filenames (much faster)
                files_data = self._fetch_directory_filenames(
                    repo, target_directory, ref, [".js"]
                )
            else:
                # For regular parsing, fetch full content
                files_data = self._fetch_directory_contents(repo, target_directory, ref)

            return {
                "repo": repo_name,
                "version": version,
                "directory": target_directory,
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

    def _handle_github_exception(self, e: GithubException, directory: str) -> None:
        """
        Handle GitHub API exceptions consistently across fetch methods.

        Args:
            e: The GitHub exception to handle
            directory: The directory path that caused the exception

        Raises:
            Exception: Wrapped exception with appropriate error message
        """
        if e.status == 404:
            raise Exception(f"Directory '{directory}' not found in repository") from e
        else:
            raise Exception(f"GitHub API error: {e}") from e

    def _fetch_directory_filenames(
        self,
        repo: Repository,
        directory: str,
        ref: str,
        file_extensions: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Fetch only filenames from a directory without content (for modules parsing).

        Args:
            repo: GitHub repository object
            directory: Directory path to fetch from
            ref: Git reference (commit SHA, branch, tag)
            file_extensions: Optional list of file extensions to filter (e.g., ['.js', '.py'])

        Returns:
            Dictionary mapping file paths to empty strings (for compatibility)
        """
        files_data = {}

        try:
            contents = repo.get_contents(directory, ref=ref)

            # Handle single file case
            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "file":
                    # Check file extension filter
                    if file_extensions:
                        if not any(
                            content.name.endswith(ext) for ext in file_extensions
                        ):
                            continue  # Skip files that don't match the extension filter

                    # Only store filename, no content (much faster)
                    files_data[content.path] = ""
                # Skip subdirectories for modules parsing (we only want root level files)

        except GithubException as e:
            self._handle_github_exception(e, directory)

        return files_data

    def _fetch_directory_names(
        self,
        repo: Repository,
        directory: str,
        ref: str,
    ) -> dict[str, str]:
        """
        Fetch subdirectory names up to 2 levels deep (for structure parsing).

        Args:
            repo: GitHub repository object
            directory: Directory path to fetch from
            ref: Git reference (commit SHA, branch, tag)

        Returns:
            Dictionary mapping directory paths to empty strings (for compatibility)
        """
        directories_data = {}

        try:
            # Get first level directories
            contents = repo.get_contents(directory, ref=ref)

            # Handle single file case
            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "dir":
                    # Store first level directory
                    directories_data[content.path] = ""

                    # Get second level directories for modules (needed for fiftyonedegrees/devicedetection)
                    if directory == "modules":
                        try:
                            sub_contents = repo.get_contents(content.path, ref=ref)
                            if not isinstance(sub_contents, list):
                                sub_contents = [sub_contents]

                            for sub_content in sub_contents:
                                if sub_content.type == "dir":
                                    directories_data[sub_content.path] = ""
                        except GithubException:
                            # If subdirectory can't be accessed, skip it
                            pass

        except GithubException as e:
            self._handle_github_exception(e, directory)

        return directories_data

    def _fetch_file_names(
        self,
        repo: Repository,
        directory: str,
        ref: str,
    ) -> dict[str, str]:
        """
        Fetch only file names from a directory (for documentation parsing).

        Args:
            repo: GitHub repository object
            directory: Directory path to fetch from
            ref: Git reference (commit SHA, branch, tag)

        Returns:
            Dictionary mapping file paths to empty strings (for compatibility)
        """
        files_data = {}

        try:
            # Get files from directory
            contents = repo.get_contents(directory, ref=ref)

            # Handle single file case
            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "file":
                    # Store file name/path with empty content
                    files_data[content.path] = ""

        except GithubException as e:
            self._handle_github_exception(e, directory)

        return files_data

    def _fetch_directory_contents(
        self,
        repo: Repository,
        directory: str,
        ref: str,
        file_extensions: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Recursively fetch files from a directory, optionally filtered by extensions.

        Args:
            repo: GitHub repository object
            directory: Directory path to fetch from
            ref: Git reference (commit SHA, branch, tag)
            file_extensions: Optional list of file extensions to filter (e.g., ['.js', '.py'])

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
                    # Check file extension filter
                    if file_extensions:
                        if not any(
                            content.name.endswith(ext) for ext in file_extensions
                        ):
                            continue  # Skip files that don't match the extension filter

                    # Fetch file content
                    file_content = self._get_file_content(content)
                    files_data[content.path] = file_content
                elif content.type == "dir":
                    # Recursively fetch subdirectory
                    subdir_files = self._fetch_directory_contents(
                        repo, content.path, ref, file_extensions
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

    def get_semantic_versions(self, repo_name: str) -> list[str]:
        """
        Get semantic versions for a repository with caching.
        Returns master/main branch + 5 latest versions + first/last of each major release.
        Uses caching to minimize API calls - only updates when new major versions are detected.
        """
        try:
            # Try to load from cache first
            cache = self.cache_manager.load_cache(repo_name)

            # Get basic repo info (always needed)
            repo = self.github.get_repo(repo_name)
            default_branch = repo.default_branch

            # Get recent tags to check for new versions (minimal API call)
            recent_tags = list(repo.get_tags())[:10]  # Only get first 10 tags

            # Parse recent tags to find current latest major version
            semver_pattern = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-.*)?$")
            current_latest_major = 0
            latest_versions = []

            for tag in recent_tags:
                match = semver_pattern.match(tag.name)
                if match:
                    major, minor, patch = map(int, match.groups())
                    current_latest_major = max(current_latest_major, major)
                    latest_versions.append(
                        {
                            "name": tag.name,
                            "major": major,
                            "minor": minor,
                            "patch": patch,
                        }
                    )

            # Sort latest versions
            latest_versions.sort(
                key=lambda x: (x["major"], x["minor"], x["patch"]), reverse=True
            )

            # Check if we can use cached data or need to rebuild
            if cache and not self.cache_manager.needs_update(
                cache, current_latest_major
            ):
                # Update current and previous major versions if they have newer releases
                updated_cache = self._update_recent_major_versions(
                    cache, latest_versions, current_latest_major
                )

                # Build chronological version list with context
                return self._build_chronological_version_list(
                    default_branch, updated_cache.latest_versions, updated_cache
                )

            # Need to rebuild cache - fetch more comprehensive data
            return self._rebuild_version_cache(
                repo_name, repo, default_branch, semver_pattern
            )

        except GithubException as e:
            raise Exception(
                f"Error getting semantic versions: {e.data.get('message', str(e))}"
            ) from e

    def _rebuild_version_cache(
        self, repo_name: str, repo, default_branch: str, semver_pattern
    ) -> list[str]:
        """Rebuild version cache from scratch."""
        print(f"Rebuilding version cache for {repo_name}...")

        # Get comprehensive tag list
        all_tags = list(repo.get_tags())
        semantic_tags = []

        # Process all tags to get complete picture
        for tag in all_tags:
            match = semver_pattern.match(tag.name)
            if match:
                major, minor, patch = map(int, match.groups())
                semantic_tags.append(
                    {
                        "name": tag.name,
                        "major": major,
                        "minor": minor,
                        "patch": patch,
                    }
                )

        # Sort by version
        semantic_tags.sort(
            key=lambda x: (x["major"], x["minor"], x["patch"]), reverse=True
        )

        # Build major version mapping
        major_versions: dict[int, list] = {}
        for tag in semantic_tags:
            major = tag["major"]
            if major not in major_versions:
                major_versions[major] = []
            major_versions[major].append(tag)

        # Create major version info
        major_version_info = {}
        for major, tags_in_major in major_versions.items():
            # Sort by version (newest first)
            tags_in_major.sort(
                key=lambda x: (x["major"], x["minor"], x["patch"]), reverse=True
            )

            first_version = tags_in_major[-1]["name"]  # Oldest (lowest version)
            last_version = tags_in_major[0]["name"]  # Newest (highest version)

            major_version_info[major] = MajorVersionInfo(
                major=major, first_version=first_version, last_version=last_version
            )

        # Get latest 5 versions overall
        latest_5 = [tag["name"] for tag in semantic_tags[:5]]

        # Save to cache
        cache = RepoVersionCache(
            repo_name=repo_name,
            default_branch=default_branch,
            major_versions=major_version_info,
            latest_versions=latest_5,
        )
        self.cache_manager.save_cache(cache)

        # Build chronological version list with context
        return self._build_chronological_version_list(default_branch, latest_5, cache)

    def _update_recent_major_versions(
        self, cache: RepoVersionCache, latest_versions: list, current_latest_major: int
    ) -> RepoVersionCache:
        """
        Update current and previous major versions' last versions if they have newer releases.
        Only updates current major (maintenance active) and previous major (maintenance period).
        """
        updated_major_versions = cache.major_versions.copy()
        cache_updated = False

        # Check current major and previous major only
        majors_to_check = [current_latest_major, current_latest_major - 1]

        for major in majors_to_check:
            if major < 0 or major not in cache.major_versions:
                continue

            # Find latest version for this major in recent releases
            latest_for_major = None
            for version_info in latest_versions:
                if version_info["major"] == major:
                    if latest_for_major is None or (
                        version_info["minor"],
                        version_info["patch"],
                    ) > (latest_for_major["minor"], latest_for_major["patch"]):
                        latest_for_major = version_info

            if latest_for_major:
                cached_info = cache.major_versions[major]
                if latest_for_major["name"] != cached_info.last_version:
                    print(
                        f"Updating {cache.repo_name} v{major}.x: {cached_info.last_version} → {latest_for_major['name']}"
                    )

                    updated_major_versions[major] = MajorVersionInfo(
                        major=cached_info.major,
                        first_version=cached_info.first_version,  # Never change
                        last_version=latest_for_major["name"],  # Update to newer
                    )
                    cache_updated = True

        # Create updated cache
        updated_cache = RepoVersionCache(
            repo_name=cache.repo_name,
            default_branch=cache.default_branch,
            major_versions=updated_major_versions,
            latest_versions=[v["name"] for v in latest_versions[:5]],
        )

        # Save if updated
        if cache_updated:
            self.cache_manager.save_cache(updated_cache)

        return updated_cache

    def _build_chronological_version_list(
        self, default_branch: str, latest_5: list[str], cache: RepoVersionCache
    ) -> list[str]:
        """
        Build a chronologically ordered version list with contextual labels.
        Order: master -> latest 5 -> major versions (newest to oldest)
        """
        versions = [default_branch]

        # Add latest 5 versions with context for the most recent
        for i, version in enumerate(latest_5):
            if i == 0:
                versions.append(f"{version} (current latest)")
            else:
                versions.append(version)

        # Sort major versions by major number (newest first)
        sorted_majors = sorted(
            cache.major_versions.items(), key=lambda x: int(x[0]), reverse=True
        )

        # Add first/last of each major version with context
        for major_str, major_info in sorted_majors:
            major_num = int(major_str)

            # Add last version of this major (if not already included)
            if major_info.last_version not in versions:
                # Check if this is already labeled as current latest
                version_without_label = major_info.last_version
                already_has_current_label = any(
                    v.startswith(f"{version_without_label} (current latest)")
                    for v in versions
                )

                if not already_has_current_label:
                    # Only add if it's not already the current latest
                    versions.append(
                        f"{major_info.last_version} (latest v{major_num}.x)"
                    )

            # Add first version of this major (if not already included and different from last)
            if (
                major_info.first_version not in versions
                and major_info.first_version != major_info.last_version.split(" ")[0]
            ):  # Remove context for comparison
                versions.append(f"{major_info.first_version} (first v{major_num}.x)")

        return versions
