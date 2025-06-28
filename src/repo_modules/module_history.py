"""
Module history tracking for repository analysis
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from loguru import logger

from ..shared_utilities import global_rate_limit_manager
from .github_client import GitHubClient


@dataclass
class ModuleHistoryInfo:
    """Information about when a module was first added."""

    name: str
    first_commit_date: str
    first_commit_sha: str
    first_release_version: str | None = None
    first_release_date: str | None = None
    file_path: str | None = None


class ModuleHistoryTracker:
    """Track when modules were first added to repositories."""

    def __init__(self, repo: str, cache_dir: Path | None = None):
        """Initialize the history tracker.

        Args:
            repo: Repository in format "owner/name"
            cache_dir: Directory for caching historical data
        """
        self.repo = repo
        self.cache_dir = cache_dir or Path("cache/history")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{repo.replace('/', '_')}_history.json"
        self.github_client = GitHubClient()

        # Load existing cache (now uses file paths as keys)
        self._cache: dict[str, ModuleHistoryInfo] = self._load_cache()

        # Tag cache for version detection
        self._tags_cache: list[dict[str, Any]] | None = None

        # Rate limiting handled by shared rate limit manager
        self.rate_limit_manager = global_rate_limit_manager

    def _load_cache(self) -> dict[str, ModuleHistoryInfo]:
        """Load cached module history data."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            # Handle both old format (module name keys) and new format (file path keys)
            cache = {}
            migration_needed = False

            for key, info in data.items():
                # Create ModuleHistoryInfo object
                history_info = ModuleHistoryInfo(**info)

                # Determine the correct file_path key to use
                file_path = info.get("file_path")

                if file_path and file_path != key:
                    # Old format: key is module name, file_path contains the actual path
                    cache[file_path] = history_info
                    migration_needed = True
                    logger.debug(f"Migrated cache entry: {key} -> {file_path}")
                elif file_path:
                    # New format: key is already the file path
                    cache[key] = history_info
                else:
                    # Legacy format: no file_path available, generate one if possible
                    module_name = info.get("name", key)

                    # Try to generate file_path based on module name and known patterns
                    guessed_path = self._guess_file_path_for_migration(module_name)
                    if guessed_path:
                        # Update the history info with the guessed path
                        history_info.file_path = guessed_path
                        cache[guessed_path] = history_info
                        migration_needed = True
                        logger.debug(
                            f"Generated file_path for migration: {key} -> {guessed_path}"
                        )
                    else:
                        # Can't determine file path, use module name as fallback
                        fallback_path = f"modules/{module_name}.js"
                        history_info.file_path = fallback_path
                        cache[fallback_path] = history_info
                        migration_needed = True
                        logger.warning(
                            f"Cache entry {key} missing file_path, using fallback: {fallback_path}"
                        )

            # If migration occurred, save the updated cache format
            if migration_needed:
                logger.info("Cache migration detected, saving updated format...")
                self._cache = cache
                self._save_cache()

            logger.info(f"Loaded {len(cache)} cached module histories")
            return cache

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return {}

    def _save_cache(self) -> None:
        """Save module history cache to disk using file paths as keys."""
        try:
            # Cache now uses file paths as keys to prevent collisions
            data = {file_path: asdict(info) for file_path, info in self._cache.items()}

            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)

        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _rate_limit(self, response: requests.Response | None = None) -> None:
        """Implement intelligent rate limiting using shared rate limit manager."""
        self.rate_limit_manager.wait_if_needed(response, tool_name="module_history")

    def _get_file_creation_info(self, file_path: str) -> ModuleHistoryInfo | None:
        """Get creation information for a specific file."""
        self._rate_limit()

        try:
            # Get commits for this file, ordered oldest first
            url = f"https://api.github.com/repos/{self.repo}/commits"
            params = {"path": file_path, "per_page": "1", "page": "1"}

            # Use authenticated request if available
            headers = {}
            if (
                hasattr(self.github_client, "_github")
                and self.github_client._github._Github__requester._Requester__authorizationHeader
            ):
                auth_header = (
                    self.github_client._github._Github__requester._Requester__authorizationHeader
                )
                headers["Authorization"] = auth_header

            logger.debug(f"API call: Getting commits for {file_path}")
            response = self.rate_limit_manager.make_rate_limited_request(
                requests.get,
                "module_history",
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            commits = response.json()

            if not commits:
                logger.warning(
                    f"No commits found for {file_path} - file may not exist or be accessible"
                )
                return None

            # Get the last commit (oldest) - this gives us the file creation
            # We need to paginate to get the actual first commit
            total_commits = self._get_total_commits_for_file(file_path, headers)
            if total_commits > 1:
                # Get the last page
                last_page = (total_commits + 29) // 30  # 30 per page, round up
                params["page"] = str(last_page)

                response = self.rate_limit_manager.make_rate_limited_request(
                    requests.get,
                    "module_history",
                    url,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
                commits = response.json()

            # Get the last commit from the last page (chronologically first)
            first_commit = commits[-1] if commits else None

            if not first_commit:
                return None

            # Extract module name from file path
            module_name = self._extract_module_name(file_path)

            # Get version information for this commit
            commit_date = first_commit["commit"]["author"]["date"]
            commit_sha = first_commit["sha"]

            # Temporarily disable version detection to preserve rate limit
            # TODO: Re-enable with better batching or when rate limits are more stable
            # version_info = self._get_first_version_for_commit(commit_sha, commit_date)
            # first_release_version = version_info[0] if version_info else None
            # first_release_date = version_info[1] if version_info else None
            first_release_version = None
            first_release_date = None

            return ModuleHistoryInfo(
                name=module_name,
                first_commit_date=commit_date,
                first_commit_sha=commit_sha,
                first_release_version=first_release_version,
                first_release_date=first_release_date,
                file_path=file_path,
            )

        except Exception as e:
            logger.error(f"Failed to get creation info for {file_path}: {e}")
            return None

    def _get_total_commits_for_file(self, file_path: str, headers: dict) -> int:
        """Get total number of commits for a file."""
        try:
            url = f"https://api.github.com/repos/{self.repo}/commits"
            params = {"path": file_path, "per_page": "1"}

            response = self.rate_limit_manager.make_rate_limited_request(
                requests.get,
                "module_history",
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            # GitHub provides total count in Link header for pagination
            link_header = response.headers.get("Link", "")
            if "last" in link_header:
                # Extract page number from last page link
                import re

                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    last_page = int(match.group(1))
                    return last_page * 30  # Approximate, good enough

            # Fallback: count commits manually (less efficient)
            commits = response.json()
            return len(commits)

        except Exception as e:
            logger.warning(f"Failed to get commit count for {file_path}: {e}")
            return 1

    def _extract_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        filename = Path(file_path).name

        # Handle different naming patterns
        if filename.endswith("BidAdapter.js"):
            return filename.replace("BidAdapter.js", "")
        elif filename.endswith("AnalyticsAdapter.js"):
            return filename.replace("AnalyticsAdapter.js", "")
        elif filename.endswith("RtdProvider.js"):
            return filename.replace("RtdProvider.js", "")
        elif filename.endswith("IdSystem.js"):
            return filename.replace("IdSystem.js", "")
        elif filename.endswith(".js"):
            return filename.replace(".js", "")
        else:
            return filename

    def _guess_file_path_for_migration(self, module_name: str) -> str | None:
        """
        Try to guess the file path for a module during cache migration.

        Args:
            module_name: The module name to generate a path for

        Returns:
            Guessed file path or None if unable to determine
        """
        # Apply case corrections for known problematic module names
        corrected_name = self._apply_case_corrections(module_name)

        # Try common patterns
        possible_paths = [
            f"modules/{corrected_name}BidAdapter.js",
            f"modules/{corrected_name}AnalyticsAdapter.js",
            f"modules/{corrected_name}RtdProvider.js",
            f"modules/{corrected_name}IdSystem.js",
            f"modules/{corrected_name}.js",
        ]

        # Return the first one (bid adapter is most common)
        # Note: During migration we can't validate file existence without making API calls
        # So we use the most likely pattern
        return possible_paths[0]

    def _get_repository_tags(self) -> list[dict[str, Any]]:
        """Get all repository tags sorted by date (oldest first)."""
        if self._tags_cache is not None:
            return self._tags_cache

        try:
            # Get all tags from repository
            url = f"https://api.github.com/repos/{self.repo}/tags"
            params = {"per_page": "100"}

            # Use authenticated request if available
            headers = {}
            if (
                hasattr(self.github_client, "_github")
                and self.github_client._github._Github__requester._Requester__authorizationHeader
            ):
                auth_header = (
                    self.github_client._github._Github__requester._Requester__authorizationHeader
                )
                headers["Authorization"] = auth_header

            all_tags = []
            page = 1

            while True:
                params["page"] = str(page)
                response = self.rate_limit_manager.make_rate_limited_request(
                    requests.get,
                    "module_history",
                    url,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()

                tags = response.json()
                if not tags:
                    break

                all_tags.extend(tags)
                page += 1

            # Get commit dates for tags to sort chronologically
            enriched_tags = []
            for tag in all_tags:
                try:
                    commit_url = f"https://api.github.com/repos/{self.repo}/commits/{tag['commit']['sha']}"
                    commit_response = self.rate_limit_manager.make_rate_limited_request(
                        requests.get,
                        "module_history",
                        commit_url,
                        headers=headers,
                        timeout=30,
                    )
                    commit_response.raise_for_status()

                    commit_data = commit_response.json()
                    tag_info = {
                        "name": tag["name"],
                        "commit_sha": tag["commit"]["sha"],
                        "commit_date": commit_data["commit"]["author"]["date"],
                    }
                    enriched_tags.append(tag_info)

                except Exception as e:
                    logger.warning(
                        f"Failed to get commit date for tag {tag['name']}: {e}"
                    )
                    continue

            # Sort by commit date (oldest first)
            enriched_tags.sort(key=lambda x: x["commit_date"])

            # Cache the results
            self._tags_cache = enriched_tags
            logger.info(f"Cached {len(enriched_tags)} repository tags")

            return self._tags_cache

        except Exception as e:
            logger.error(f"Failed to get repository tags: {e}")
            return []

    def _get_first_version_for_commit(
        self, commit_sha: str, commit_date: str
    ) -> tuple[str, str] | None:
        """Find the first version tag that contains or comes after the given commit."""
        try:
            tags = self._get_repository_tags()

            # Find the first tag that comes after this commit date
            for tag in tags:
                if tag["commit_date"] >= commit_date:
                    return tag["name"], tag["commit_date"]

            # If no tag found after the commit, it might be unreleased
            return None

        except Exception as e:
            logger.warning(f"Failed to find version for commit {commit_sha}: {e}")
            return None

    def get_module_history(
        self,
        module_names: list[str],
        file_paths: list[str] | None = None,
        component_types: list[str] | None = None,
    ) -> dict[str, ModuleHistoryInfo]:
        """Get historical information for a list of modules.

        Args:
            module_names: List of module names to look up
            file_paths: Optional list of file paths corresponding to modules
            component_types: Optional list of component types (bidder, analytics, rtd, userId)

        Returns:
            Dictionary mapping module names to their history info
        """
        results = {}
        new_entries = 0

        for i, module_name in enumerate(module_names):
            # Determine file path first
            if file_paths and i < len(file_paths):
                file_path = file_paths[i]
            else:
                # Determine file path based on module name and component type
                component_type = (
                    component_types[i]
                    if component_types and i < len(component_types)
                    else None
                )
                file_path = self._guess_file_path(module_name, component_type)

            if file_path is None:
                logger.warning(
                    f"No valid file path found for module: {module_name} (checked multiple patterns)"
                )
                continue

            # Check cache using file path as key (prevents name collisions)
            if file_path in self._cache:
                results[module_name] = self._cache[file_path]
                continue

            # Get creation info
            try:
                history_info = self._get_file_creation_info(file_path)
                if history_info:
                    # Cache using file path as key to prevent collisions between module types
                    self._cache[file_path] = history_info
                    results[module_name] = history_info
                    new_entries += 1
            except Exception as e:
                logger.warning(f"Failed to get history for {module_name}: {e}")
                continue

            # Progress logging
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(module_names)} modules")

        # Save cache if we added new entries
        if new_entries > 0:
            self._save_cache()
            logger.info(f"Added {new_entries} new entries to cache")

        return results

    def _guess_file_path(
        self, module_name: str, component_type: str | None = None
    ) -> str | None:
        """
        Determine the file path for a module based on its component type.
        Returns None if no valid file path can be determined.
        """
        # Apply case corrections for known problematic modules
        corrected_name = self._apply_case_corrections(module_name)

        # Generate possible file paths based on component type
        possible_paths = self._generate_possible_paths(corrected_name, component_type)

        # Try to find the actual file path that exists
        return self._find_existing_file_path(possible_paths)

    def _apply_case_corrections(self, module_name: str) -> str:
        """Apply known case corrections for problematic module names."""
        case_corrections = {
            "a1media": "a1Media",
            "neuwo": "neuwo",  # Already correct case
            # Add more case corrections as needed
        }
        return case_corrections.get(module_name, module_name)

    def _generate_possible_paths(
        self, module_name: str, component_type: str | None = None
    ) -> list[str]:
        """Generate list of possible file paths for a module."""
        possible_paths = []

        # Primary paths based on component type
        if component_type == "bidder":
            possible_paths.append(f"modules/{module_name}BidAdapter.js")
        elif component_type == "analytics":
            possible_paths.append(f"modules/{module_name}AnalyticsAdapter.js")
        elif component_type == "rtd":
            possible_paths.append(f"modules/{module_name}RtdProvider.js")
        elif component_type == "userId":
            possible_paths.append(f"modules/{module_name}IdSystem.js")
        elif component_type == "other":
            possible_paths.append(f"modules/{module_name}.js")

        # Always add common fallback patterns for unknown or misclassified types
        fallback_patterns = [
            f"modules/{module_name}BidAdapter.js",
            f"modules/{module_name}RtdProvider.js",
            f"modules/{module_name}AnalyticsAdapter.js",
            f"modules/{module_name}IdSystem.js",
            f"modules/{module_name}.js",
        ]

        # Add fallbacks that aren't already in the list
        for pattern in fallback_patterns:
            if pattern not in possible_paths:
                possible_paths.append(pattern)

        return possible_paths

    def _find_existing_file_path(self, possible_paths: list[str]) -> str | None:
        """
        Determine the most likely file path without making API calls to preserve rate limit.
        Uses heuristics based on component type and naming patterns.
        """
        # Temporarily disable file existence checking to prevent rate limit exhaustion
        # TODO: Re-enable with better rate limit management or use Git Tree API

        if not possible_paths:
            return None

        # Return the first path - our path generation logic should be accurate enough
        # and file existence will be verified when we try to get commit history
        logger.debug(f"Using heuristic file path selection: {possible_paths[0]}")
        return possible_paths[0]

    def enrich_module_data(
        self, modules_data: dict[str, list[str]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Enrich module data with historical information.

        Args:
            modules_data: Dictionary with module categories and lists of names

        Returns:
            Enhanced dictionary with historical data included
        """
        enriched_data: dict[str, list[dict[str, Any]]] = {}

        for category, module_names in modules_data.items():
            if not module_names:
                enriched_data[category] = []
                continue

            # Get historical data for this category
            history_data = self.get_module_history(module_names)

            # Create enriched module entries
            enriched_modules = []
            for module_name in module_names:
                module_info = {
                    "name": module_name,
                    "first_added": None,
                    "first_version": None,
                    "first_commit_sha": None,
                }

                if module_name in history_data:
                    history = history_data[module_name]
                    module_info.update(
                        {
                            "first_added": history.first_commit_date,
                            "first_version": history.first_release_version,
                            "first_commit_sha": history.first_commit_sha,
                        }
                    )

                enriched_modules.append(module_info)

            enriched_data[category] = enriched_modules

        return enriched_data
