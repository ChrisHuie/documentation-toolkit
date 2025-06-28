"""
Module history tracking for repository analysis.

Provides comprehensive analysis of when modules were first introduced,
combining version-based analysis with commit-level tracking.
"""

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from ..shared_utilities import get_logger, global_rate_limit_manager, trace_function
from .github_client import GitHubClient
from .parser_factory import ParserFactory, PrebidJSParser
from .version_cache import VersionCacheManager


@dataclass
class ModuleHistoryInfo:
    """Information about when a module was first added."""

    name: str
    first_commit_date: str
    first_commit_sha: str
    first_release_version: str | None = None
    first_release_date: str | None = None
    file_path: str | None = None


@dataclass
class ModuleHistoryEntry:
    """Information about when a module was first introduced."""

    module_name: str
    module_type: str  # bid_adapter, analytics_adapter, etc.
    first_version: str  # e.g., "2.15.0"
    first_major_version: int  # e.g., 2
    file_path: str  # e.g., "modules/exampleBidAdapter.js"


@dataclass
class ModuleHistoryCache:
    """Cached module history information for a repository."""

    repo_name: str
    last_analyzed_version: str
    modules: dict[str, ModuleHistoryEntry]  # module_name -> entry
    metadata: dict[str, Any]  # analysis metadata


class ModuleHistoryError(Exception):
    """Base exception for module history operations."""

    pass


class ModuleHistoryTracker:
    """
    Tracks when modules were first introduced in repositories.
    
    Provides both version-based analysis (for Prebid.js) and commit-level tracking
    with intelligent rate limiting and file path collision prevention.
    """

    def __init__(self, token: str | None = None, cache_dir: str | None = None, repo: str | None = None):
        """
        Initialize module history tracker.
        
        Args:
            token: GitHub token for API access
            cache_dir: Directory for caching historical data
            repo: Repository in format "owner/name" (for commit-level tracking)
        """
        self.client = GitHubClient(token)
        self.cache_manager = VersionCacheManager()
        self.parser_factory = ParserFactory()
        self.logger = get_logger(__name__)
        
        # Repository for commit-level tracking (optional)
        self.repo = repo
        
        # Rate limiting manager from shared utilities
        self.rate_limit_manager = global_rate_limit_manager

        # Cache directory for module history (version-based analysis)
        if cache_dir is None:
            repo_root = Path(__file__).parent.parent.parent
            self.history_cache_dir = repo_root / "cache" / "module_history"
            # Also support commit-level history cache
            self.commit_cache_dir = repo_root / "cache" / "history"
        else:
            cache_path = Path(cache_dir)
            self.history_cache_dir = cache_path / "module_history"
            self.commit_cache_dir = cache_path / "history"

        self.history_cache_dir.mkdir(parents=True, exist_ok=True)
        self.commit_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Commit-level cache setup
        if self.repo:
            self.cache_file = self.commit_cache_dir / f"{self.repo.replace('/', '_')}_history.json"
            self._cache: dict[str, ModuleHistoryInfo] = self._load_commit_cache()
        else:
            self._cache = {}
            
        # Tag cache for version detection  
        self._tags_cache: list[dict[str, Any]] | None = None

    def _get_cache_file(self, repo_name: str) -> Path:
        """Get cache file path for module history."""
        safe_name = repo_name.replace("/", "_")
        return self.history_cache_dir / f"{safe_name}_module_history.json"

    def _load_history_cache(self, repo_name: str) -> ModuleHistoryCache | None:
        """Load cached module history."""
        cache_file = self._get_cache_file(repo_name)

        if not cache_file.exists():
            self.logger.debug("No cache file found", cache_file=str(cache_file))
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Validate required fields
            required_fields = [
                "repo_name",
                "last_analyzed_version",
                "modules",
                "metadata",
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Convert modules dict back to proper format
            modules = {}
            for module_name, entry_data in data["modules"].items():
                try:
                    modules[module_name] = ModuleHistoryEntry(**entry_data)
                except TypeError as e:
                    self.logger.warning(
                        "Invalid module entry in cache",
                        module=module_name,
                        error=str(e),
                    )
                    continue

            cache = ModuleHistoryCache(
                repo_name=data["repo_name"],
                last_analyzed_version=data["last_analyzed_version"],
                modules=modules,
                metadata=data["metadata"],
            )

            self.logger.debug(
                "Loaded module history cache",
                cache_file=str(cache_file),
                module_count=len(modules),
            )

            return cache

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self.logger.warning(
                "Invalid module history cache file",
                cache_file=str(cache_file),
                error=str(e),
            )
            return None

    def _save_history_cache(self, cache: ModuleHistoryCache) -> None:
        """Save module history cache."""
        cache_file = self._get_cache_file(cache.repo_name)

        try:
            # Convert to dict for JSON serialization
            data = asdict(cache)

            # Convert modules to proper dict format
            modules_dict = {}
            for module_name, entry in data["modules"].items():
                modules_dict[module_name] = entry
            data["modules"] = modules_dict

            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.info(
                "Module history cache saved",
                cache_file=str(cache_file),
                module_count=len(cache.modules),
            )

        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(
                "Failed to save module history cache",
                cache_file=str(cache_file),
                error=str(e),
            )
            raise ModuleHistoryError(f"Failed to save cache: {e}") from e

    def _load_commit_cache(self) -> dict[str, ModuleHistoryInfo]:
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
                    self.logger.debug(f"Migrated cache entry: {key} -> {file_path}")
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
                        self.logger.debug(
                            f"Generated file_path for migration: {key} -> {guessed_path}"
                        )
                    else:
                        # Can't determine file path, use module name as fallback
                        fallback_path = f"modules/{module_name}.js"
                        history_info.file_path = fallback_path
                        cache[fallback_path] = history_info
                        migration_needed = True
                        self.logger.warning(
                            f"Cache entry {key} missing file_path, using fallback: {fallback_path}"
                        )

            # If migration occurred, save the updated cache format
            if migration_needed:
                self.logger.info("Cache migration detected, saving updated format...")
                self._cache = cache
                self._save_commit_cache()

            self.logger.info(f"Loaded {len(cache)} cached module histories")
            return cache

        except Exception as e:
            self.logger.warning(f"Failed to load cache: {e}")
            return {}

    def _save_commit_cache(self) -> None:
        """Save module history cache to disk using file paths as keys."""
        try:
            # Cache now uses file paths as keys to prevent collisions
            data = {file_path: asdict(info) for file_path, info in self._cache.items()}

            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)

        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")

    def _get_modules_for_version(
        self, repo_name: str, version: str
    ) -> dict[str, list[str]]:
        """Get modules for a specific version using the Prebid.js parser."""
        try:
            # Create a mock config for the parser
            from .config import RepoConfig

            config = RepoConfig(
                repo="prebid/Prebid.js",
                description="Prebid.js modules",
                versions=[version],
                parser_type="prebid_js",
                fetch_strategy="filenames_only",
                paths={"modules": "modules"},
            )

            # Fetch repository data
            data = self.client.fetch_repository_data(
                repo_name=repo_name,
                version=version,
                directory="modules",
                fetch_strategy="filenames_only",
            )

            # Parse with Prebid.js parser
            parser = PrebidJSParser(config)
            parsed_modules = parser._categorize_modules(data["files"])

            self.logger.debug(
                "Fetched modules for version",
                version=version,
                total_modules=sum(len(modules) for modules in parsed_modules.values()),
            )

            return parsed_modules

        except Exception as e:
            self.logger.error(
                "Failed to fetch modules for version", version=version, error=str(e)
            )
            # Return empty dict instead of raising to allow analysis to continue
            return {}

    def _parse_version_number(self, version: str) -> tuple[int, int, int]:
        """Parse version string into major, minor, patch numbers."""
        try:
            # Handle "v1.2.3" or "1.2.3" format
            clean_version = version.lstrip("v")
            if not clean_version:
                return (0, 0, 0)

            parts = clean_version.split(".")

            # Parse each part individually, if any fails, stop parsing
            major = 0
            minor = 0
            patch = 0

            # Parse major version
            if len(parts) > 0 and parts[0]:
                try:
                    major = int(parts[0])
                except ValueError:
                    return (major, minor, patch)

            # Parse minor version (only if major was successful)
            if len(parts) > 1 and parts[1]:
                try:
                    minor = int(parts[1])
                except ValueError:
                    return (major, minor, patch)

            # Parse patch version (only if major and minor were successful)
            if len(parts) > 2 and parts[2]:
                try:
                    patch = int(parts[2])
                except ValueError:
                    return (major, minor, patch)

            return (major, minor, patch)

        except Exception as e:
            self.logger.warning(
                "Failed to parse version number", version=version, error=str(e)
            )
            return (0, 0, 0)

    def _analyze_module_introduction(
        self, repo_name: str, modules_by_version: dict[str, dict[str, list[str]]]
    ) -> dict[str, ModuleHistoryEntry]:
        """Analyze when each module was first introduced."""
        module_history = {}

        # Sort versions by semantic version (oldest first)
        sorted_versions = sorted(
            modules_by_version.keys(), key=lambda v: self._parse_version_number(v)
        )

        self.logger.info(
            "Analyzing module introduction across versions",
            version_count=len(sorted_versions),
            versions=sorted_versions,
        )

        # Track modules we've seen
        seen_modules = set()

        for version in sorted_versions:
            version_modules = modules_by_version[version]
            major_version = self._parse_version_number(version)[0]

            # Check each category
            for category, modules in version_modules.items():
                for module_name in modules:
                    if module_name not in seen_modules:
                        # This is the first time we've seen this module
                        file_path = self._guess_file_path_for_module(
                            module_name, category
                        )

                        entry = ModuleHistoryEntry(
                            module_name=module_name,
                            module_type=category,
                            first_version=version,
                            first_major_version=major_version,
                            file_path=file_path,
                        )

                        module_history[module_name] = entry
                        seen_modules.add(module_name)

                        self.logger.debug(
                            "Module first appearance",
                            module=module_name,
                            version=version,
                            type=category,
                        )

        return module_history

    def _guess_file_path_for_module(self, module_name: str, category: str) -> str:
        """Guess the file path for a module based on its name and category."""
        # Apply case corrections for known patterns
        corrected_name = self._apply_case_corrections(module_name)

        if category == "bid_adapters":
            return f"modules/{corrected_name}BidAdapter.js"
        elif category == "analytics_adapters":
            return f"modules/{corrected_name}AnalyticsAdapter.js"
        elif category == "rtd_modules":
            return f"modules/{corrected_name}RtdProvider.js"
        elif category == "identity_modules":
            return f"modules/{corrected_name}IdSystem.js"
        else:
            return f"modules/{corrected_name}.js"

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

    def _apply_case_corrections(self, module_name: str) -> str:
        """Apply known case corrections for module names."""
        # Common case corrections based on actual Prebid.js file names
        corrections = {
            "33across": "33across",
            "adpod": "adpod",
            "adagio": "adagio",
            "appnexus": "appnexus",
            "rubicon": "rubicon",
            "a1media": "a1Media",
            "neuwo": "neuwo",  # Already correct case
            # Add more as needed
        }

        return corrections.get(module_name.lower(), module_name)

    @trace_function("analyze_module_history", include_args=True)
    def analyze_module_history(
        self,
        repo_name: str = "prebid/Prebid.js",
        force_refresh: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ModuleHistoryCache:
        """
        Analyze module history for Prebid.js.

        Args:
            repo_name: Repository name (default: prebid/Prebid.js)
            force_refresh: Force refresh even if cache exists
            progress_callback: Optional callback for progress updates (current_step, total_steps, message)

        Returns:
            ModuleHistoryCache with complete module introduction history

        Raises:
            ModuleHistoryError: If analysis fails critically
        """

        def update_progress(current: int, total: int, message: str):
            if progress_callback:
                progress_callback(current, total, message)

        # Check for existing cache
        if not force_refresh:
            cached_history = self._load_history_cache(repo_name)
            if cached_history:
                self.logger.info(
                    "Using cached module history",
                    repo=repo_name,
                    module_count=len(cached_history.modules),
                    last_analyzed=cached_history.last_analyzed_version,
                )
                update_progress(1, 1, "Using cached data")
                return cached_history

        self.logger.info("Starting module history analysis", repo=repo_name)
        update_progress(0, 100, "Starting analysis")

        # Load version cache to get all major versions
        try:
            version_cache = self.cache_manager.load_cache(repo_name)
            if not version_cache:
                error_msg = f"No version cache found for {repo_name}. Run repo-modules first."
                self.logger.error(error_msg)
                raise ModuleHistoryError(error_msg)
        except Exception as e:
            raise ModuleHistoryError(f"Failed to load version cache: {e}") from e

        update_progress(10, 100, "Version cache loaded")

        # Collect modules for each major version (use first version of each major)
        modules_by_version = {}
        total_versions = len(version_cache.major_versions)

        for i, (major, version_info) in enumerate(
            sorted(version_cache.major_versions.items())
        ):
            first_version = version_info.first_version
            update_progress(
                10 + (i * 60 // total_versions),
                100,
                f"Analyzing major version {major} (v{first_version})",
            )

            self.logger.info(f"Analyzing major version {major} (v{first_version})")

            # Add rate limiting to be respectful to GitHub API
            time.sleep(0.5)

            modules = self._get_modules_for_version(repo_name, first_version)
            if modules:
                modules_by_version[first_version] = modules
            else:
                self.logger.warning(
                    "No modules found for version", version=first_version, major=major
                )

        if not modules_by_version:
            error_msg = (
                f"No module data could be retrieved for any version of {repo_name}"
            )
            self.logger.error(error_msg)
            raise ModuleHistoryError(error_msg)

        update_progress(70, 100, "Analyzing module introduction timeline")

        # Analyze when each module was first introduced
        try:
            module_history = self._analyze_module_introduction(
                repo_name, modules_by_version
            )
        except Exception as e:
            raise ModuleHistoryError(
                f"Failed to analyze module introduction: {e}"
            ) from e

        update_progress(85, 100, "Saving results to cache")

        # Create and save cache
        try:
            latest_version = max(
                version_cache.major_versions.values(),
                key=lambda v: self._parse_version_number(v.first_version),
            ).last_version

            history_cache = ModuleHistoryCache(
                repo_name=repo_name,
                last_analyzed_version=latest_version,
                modules=module_history,
                metadata={
                    "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "analyzed_versions": list(modules_by_version.keys()),
                    "total_modules": len(module_history),
                    "version_count": len(modules_by_version),
                },
            )

            self._save_history_cache(history_cache)
        except Exception as e:
            raise ModuleHistoryError(f"Failed to create or save cache: {e}") from e

        update_progress(100, 100, "Analysis complete")

        self.logger.info(
            "Module history analysis complete",
            repo=repo_name,
            total_modules=len(module_history),
            analyzed_versions=len(modules_by_version),
        )

        return history_cache

    def get_modules_by_version(
        self, repo_name: str = "prebid/Prebid.js", major_version: int | None = None
    ) -> dict[str, ModuleHistoryEntry]:
        """
        Get modules that were first introduced in a specific major version.

        Args:
            repo_name: Repository name
            major_version: Major version to filter by (None for all)

        Returns:
            Dictionary of module_name -> ModuleHistoryEntry

        Raises:
            ModuleHistoryError: If no cache exists and analysis fails
        """
        history_cache = self._load_history_cache(repo_name)
        if not history_cache:
            # Analyze if no cache exists
            try:
                history_cache = self.analyze_module_history(repo_name)
            except Exception as e:
                raise ModuleHistoryError(f"Failed to get module history: {e}") from e

        if major_version is None:
            return history_cache.modules

        return {
            name: entry
            for name, entry in history_cache.modules.items()
            if entry.first_major_version == major_version
        }

    def get_module_timeline(
        self, repo_name: str = "prebid/Prebid.js"
    ) -> dict[int, list[ModuleHistoryEntry]]:
        """
        Get a timeline of module introductions by major version.

        Returns:
            Dictionary of major_version -> list of ModuleHistoryEntry

        Raises:
            ModuleHistoryError: If no cache exists and analysis fails
        """
        history_cache = self._load_history_cache(repo_name)
        if not history_cache:
            try:
                history_cache = self.analyze_module_history(repo_name)
            except Exception as e:
                raise ModuleHistoryError(f"Failed to get module timeline: {e}") from e

        timeline: dict[int, list[ModuleHistoryEntry]] = {}
        for entry in history_cache.modules.values():
            major = entry.first_major_version
            if major not in timeline:
                timeline[major] = []
            timeline[major].append(entry)

        # Sort entries within each major version by module name
        for entries in timeline.values():
            entries.sort(key=lambda e: e.module_name)

        return timeline

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
        if not self.repo:
            raise ModuleHistoryError("Repository not set for commit-level tracking")
            
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
                self.logger.warning(
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
                self.logger.warning(f"Failed to get history for {module_name}: {e}")
                continue

            # Progress logging
            if (i + 1) % 10 == 0:
                self.logger.info(f"Processed {i + 1}/{len(module_names)} modules")

        # Save cache if we added new entries
        if new_entries > 0:
            self._save_commit_cache()
            self.logger.info(f"Added {new_entries} new entries to cache")

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
        self.logger.debug(f"Using heuristic file path selection: {possible_paths[0]}")
        return possible_paths[0]

    def _get_file_creation_info(self, file_path: str) -> ModuleHistoryInfo | None:
        """Get creation information for a specific file."""
        if not self.repo:
            return None
            
        try:
            # Get commits for this file, ordered oldest first
            url = f"https://api.github.com/repos/{self.repo}/commits"
            params = {"path": file_path, "per_page": "1", "page": "1"}

            # Use authenticated request if available
            headers = {}
            if (
                hasattr(self.client, "_github")
                and self.client._github._Github__requester._Requester__authorizationHeader
            ):
                auth_header = (
                    self.client._github._Github__requester._Requester__authorizationHeader
                )
                headers["Authorization"] = auth_header

            self.logger.debug(f"API call: Getting commits for {file_path}")
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
                self.logger.warning(
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
            self.logger.error(f"Failed to get creation info for {file_path}: {e}")
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
            self.logger.warning(f"Failed to get commit count for {file_path}: {e}")
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

    def clear_cache(self, repo_name: str | None = None) -> None:
        """
        Clear module history cache.

        Args:
            repo_name: Specific repo to clear (None for all)
        """
        try:
            if repo_name:
                cache_file = self._get_cache_file(repo_name)
                if cache_file.exists():
                    cache_file.unlink()
                    self.logger.info("Cache cleared", repo=repo_name)
            else:
                # Clear all cache files
                for cache_file in self.history_cache_dir.glob("*_module_history.json"):
                    cache_file.unlink()
                self.logger.info("All module history caches cleared")
        except OSError as e:
            self.logger.error("Failed to clear cache", error=str(e))
            raise ModuleHistoryError(f"Failed to clear cache: {e}") from e

    def get_cache_info(self, repo_name: str) -> dict[str, Any] | None:
        """
        Get information about the cache for a repository.

        Returns:
            Cache metadata or None if no cache exists
        """
        cache_file = self._get_cache_file(repo_name)
        if not cache_file.exists():
            return None

        try:
            history_cache = self._load_history_cache(repo_name)
            if history_cache:
                return {
                    "cache_file": str(cache_file),
                    "repo_name": history_cache.repo_name,
                    "last_analyzed_version": history_cache.last_analyzed_version,
                    "module_count": len(history_cache.modules),
                    "metadata": history_cache.metadata,
                }
        except Exception as e:
            self.logger.warning("Failed to load cache info", error=str(e))

        return None