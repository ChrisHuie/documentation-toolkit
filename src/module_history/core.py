"""
Core module history tracking functionality.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..repo_modules.parser_factory import ParserFactory
from ..shared_utilities import get_logger, global_rate_limit_manager
from ..shared_utilities.github_client import GitHubClient
from ..shared_utilities.telemetry import trace_function, trace_operation
from ..shared_utilities.version_cache import VersionCacheManager
from .config import HistoryConfig, HistoryConfigManager
from .data_models import HistoryCache, ModuleHistoryEntry, ModuleHistoryResult


class ModuleHistoryError(Exception):
    """Base exception for module history operations."""

    pass


class ModuleHistoryTracker:
    """
    Configuration-driven module history tracker.

    Supports multiple repositories through configuration and uses shared utilities
    for consistent behavior across the toolkit.
    """

    def __init__(
        self,
        token: str | None = None,
        cache_dir: str | None = None,
        config_file: str | None = None,
    ):
        """Initialize module history tracker.

        Args:
            token: GitHub token for API access
            cache_dir: Directory for caching data
            config_file: Path to configuration file
        """
        self.logger = get_logger(__name__)
        self.client = GitHubClient(token)
        self.cache_manager = VersionCacheManager()
        self.parser_factory = ParserFactory()
        self.config_manager = HistoryConfigManager(config_file)
        self.rate_limit_manager = global_rate_limit_manager

        # Setup cache directory
        if cache_dir is None:
            repo_root = Path(__file__).parent.parent.parent
            self.cache_dir = repo_root / "cache" / "module_history"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, repo_name: str) -> Path:
        """Get cache file path for a repository."""
        safe_name = repo_name.replace("/", "_")
        return self.cache_dir / f"{safe_name}_history.json"

    def _load_cache(self, repo_name: str) -> HistoryCache | None:
        """Load cached history data."""
        cache_file = self._get_cache_file(repo_name)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Convert modules dict back to proper format
            modules = {}
            for module_name, entry_data in data["modules"].items():
                try:
                    modules[module_name] = ModuleHistoryEntry(**entry_data)
                except TypeError as e:
                    self.logger.warning(f"Invalid cache entry for {module_name}: {e}")
                    continue

            return HistoryCache(
                repo_name=data["repo_name"],
                last_analyzed_version=data["last_analyzed_version"],
                modules=modules,
                metadata=data["metadata"],
            )

        except Exception as e:
            self.logger.warning(f"Failed to load cache for {repo_name}: {e}")
            return None

    def _save_cache(self, cache: HistoryCache) -> None:
        """Save cache data."""
        cache_file = self._get_cache_file(cache.repo_name)

        try:
            # Convert to dict for JSON serialization
            data = {
                "repo_name": cache.repo_name,
                "last_analyzed_version": cache.last_analyzed_version,
                "modules": {
                    name: entry.__dict__ for name, entry in cache.modules.items()
                },
                "metadata": cache.metadata,
            }

            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Cache saved for {cache.repo_name}")

        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
            raise ModuleHistoryError(f"Failed to save cache: {e}") from e

    def _parse_version_number(self, version: str) -> tuple[int, int, int]:
        """Parse version string into major, minor, patch numbers."""
        try:
            clean_version = version.lstrip("v")
            if not clean_version:
                return (0, 0, 0)

            parts = clean_version.split(".")
            major = int(parts[0]) if len(parts) > 0 and parts[0] else 0
            minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
            patch = int(parts[2]) if len(parts) > 2 and parts[2] else 0

            return (major, minor, patch)

        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to parse version {version}: {e}")
            return (0, 0, 0)

    def _get_modules_for_version(
        self, config: HistoryConfig, version: str, module_type: str | None = None
    ) -> dict[str, list[str]]:
        """Get modules for a specific version using configured parser."""
        try:
            with trace_operation(
                "fetch_modules_for_version",
                {"repo": config.repo_name, "version": version},
            ):
                # Create a temporary config for the parser
                from ..repo_modules.config import RepoConfig

                temp_config = RepoConfig(
                    repo=config.repo_name,
                    description=config.description,
                    versions=[version],
                    parser_type=config.parser_type,
                    fetch_strategy=config.fetch_strategy,
                    paths={"modules": "modules"},  # Default path
                )

                # Fetch repository data
                data = self.client.fetch_repository_data(
                    repo_name=config.repo_name,
                    version=version,
                    directory="modules",
                    fetch_strategy=config.fetch_strategy,
                )

                # Parse with configured parser
                parser = self.parser_factory.get_parser(temp_config)
                if hasattr(parser, "_categorize_modules"):
                    parsed_modules = parser._categorize_modules(data["files"])
                else:
                    # Fallback for parsers without categorization
                    parsed_modules = {"modules": data["files"]}

                # Filter by module type if specified
                if module_type and module_type in parsed_modules:
                    filtered_modules = {module_type: parsed_modules[module_type]}
                    self.logger.debug(
                        f"Filtered to {module_type}: {len(filtered_modules[module_type])} modules"
                    )
                    return filtered_modules
                elif module_type and module_type not in parsed_modules:
                    self.logger.warning(
                        f"Module type '{module_type}' not found in parsed modules"
                    )
                    return {}

                self.logger.debug(
                    f"Fetched modules for {version}",
                    total=sum(len(modules) for modules in parsed_modules.values()),
                )

                return parsed_modules

        except Exception as e:
            self.logger.error(f"Failed to fetch modules for {version}: {e}")
            return {}

    def _analyze_module_introduction(
        self, config: HistoryConfig, modules_by_version: dict[str, dict[str, list[str]]]
    ) -> dict[str, ModuleHistoryEntry]:
        """Analyze when each module was first introduced."""
        module_history = {}

        # Sort versions by semantic version (oldest first)
        sorted_versions = sorted(
            modules_by_version.keys(), key=lambda v: self._parse_version_number(v)
        )

        self.logger.info(
            f"Analyzing module introduction across {len(sorted_versions)} versions"
        )

        seen_modules = set()

        for version in sorted_versions:
            version_modules = modules_by_version[version]
            major_version = self._parse_version_number(version)[0]

            # Check each category
            for category, modules in version_modules.items():
                for module_name in modules:
                    if module_name not in seen_modules:
                        # First time seeing this module
                        file_path = self._guess_file_path(module_name, category, config)

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
                            f"Module {module_name} first seen in {version}"
                        )

        return module_history

    def _guess_file_path(
        self, module_name: str, category: str, config: HistoryConfig
    ) -> str:
        """Guess file path based on module name, category, and configuration."""
        patterns = config.module_patterns or {}

        # Apply case corrections for known patterns
        corrected_name = self._apply_case_corrections(module_name)

        if category == "bid_adapters":
            pattern = patterns.get("bid_adapters", "*BidAdapter.js")
            return pattern.replace("*", f"modules/{corrected_name}")
        elif category == "analytics_adapters":
            pattern = patterns.get("analytics_adapters", "*AnalyticsAdapter.js")
            return pattern.replace("*", f"modules/{corrected_name}")
        elif category == "rtd_modules":
            pattern = patterns.get("rtd_modules", "*RtdProvider.js")
            return pattern.replace("*", f"modules/{corrected_name}")
        elif category == "identity_modules":
            pattern = patterns.get("identity_modules", "*IdSystem.js")
            return pattern.replace("*", f"modules/{corrected_name}")
        else:
            pattern = patterns.get("other_modules", "*.js")
            return pattern.replace("*", f"modules/{corrected_name}")

    def _apply_case_corrections(self, module_name: str) -> str:
        """Apply known case corrections for module names."""
        corrections = {
            "33across": "33across",
            "a1media": "a1Media",
            # Add more as needed
        }
        return corrections.get(module_name.lower(), module_name)

    def _analyze_module_introduction_for_version(
        self,
        config: HistoryConfig,
        current_modules: dict[str, list[str]],
        version_cache: Any,
        update_progress: Callable[[int, int, str], None],
        module_type_filter: str | None = None,
    ) -> dict[str, ModuleHistoryEntry]:
        """
        Analyze when each module in the current version was first introduced.

        This method gets the modules from a specific version and then uses
        existing history cache or GitHub API to find when each was first introduced.
        """
        module_history = {}

        # Try to load existing history cache
        history_cache_path = (
            Path(__file__).parent.parent.parent
            / "cache"
            / "history"
            / f"{config.repo_name.replace('/', '_')}_history.json"
        )
        existing_history = {}

        if history_cache_path.exists():
            try:
                with open(history_cache_path) as f:
                    existing_history = json.load(f)
                self.logger.info(
                    f"Loaded existing history cache with {len(existing_history)} entries"
                )
            except Exception as e:
                self.logger.warning(f"Failed to load history cache: {e}")

        # Process each module
        total_processed = 0
        for category, modules in current_modules.items():
            for module_name in modules:
                total_processed += 1
                progress = 40 + (
                    total_processed
                    * 40
                    // sum(len(m) for m in current_modules.values())
                )
                update_progress(progress, 100, f"Processing {module_name}")

                file_path = self._guess_file_path(module_name, category, config)

                # Check if we have this module in the existing history cache
                first_commit_date = None
                first_commit_sha = None

                if module_name in existing_history:
                    history_data = existing_history[module_name]
                    first_commit_date = history_data.get("first_commit_date")
                    first_commit_sha = history_data.get("first_commit_sha")

                    # Find which version this commit date belongs to
                    if first_commit_date:
                        # Parse the date
                        from datetime import datetime

                        commit_date = datetime.fromisoformat(
                            first_commit_date.replace("Z", "+00:00")
                        )

                        # Find the appropriate version based on date
                        first_version = self._find_version_by_date(
                            commit_date, version_cache
                        )
                        first_major = self._parse_version_number(first_version)[0]
                    else:
                        first_version = "master"
                        first_major = 0
                else:
                    # Module not in cache, need to fetch from GitHub
                    self.logger.debug(
                        f"Module {module_name} not in history cache, fetching from GitHub"
                    )

                    first_commit_info = self._get_first_commit_for_file(
                        config.repo_name, file_path
                    )

                    if first_commit_info:
                        first_commit_date = (
                            first_commit_info["date"].isoformat()
                            if hasattr(first_commit_info["date"], "isoformat")
                            else str(first_commit_info["date"])
                        )
                        first_commit_sha = first_commit_info["sha"]
                        first_version = self._find_version_by_date(
                            first_commit_info["date"], version_cache
                        )
                        first_major = self._parse_version_number(first_version)[0]
                    else:
                        first_version = "master"
                        first_major = 0

                entry = ModuleHistoryEntry(
                    module_name=module_name,
                    module_type=category,
                    first_version=first_version,
                    first_major_version=first_major,
                    file_path=file_path,
                    first_commit_date=first_commit_date,
                    first_commit_sha=first_commit_sha,
                )

                module_history[module_name] = entry

        return module_history

    def _find_version_by_date(self, commit_date: Any, version_cache: Any) -> str:
        """Find which version a commit belongs to based on its date."""
        # This is a simplified implementation
        # In reality, we'd need to check actual release dates
        # For now, we'll just use major version boundaries

        # If we have version cache with dates, use that
        # Otherwise default to a simple heuristic

        # Simple heuristic based on year
        from datetime import datetime

        if isinstance(commit_date, str):
            commit_date = datetime.fromisoformat(commit_date.replace("Z", "+00:00"))

        year = commit_date.year

        # Rough mapping based on Prebid.js release history
        if year < 2017:
            return "v0.1.0"
        elif year == 2017:
            return "v1.0.0"
        elif year == 2018:
            return "v2.0.0"
        elif year == 2019:
            return "v3.0.0"
        elif year == 2020:
            return "v4.0.0"
        elif year == 2021:
            return "v5.0.0"
        elif year == 2022:
            return "v6.0.0"
        elif year == 2023:
            return "v7.0.0"
        elif year == 2024:
            return "v8.0.0"
        else:
            return "v9.0.0"

    def _get_first_commit_for_file(self, repo_name: str, file_path: str) -> dict | None:
        """Get the first commit that introduced a file."""
        try:
            # Apply rate limiting before making request
            self.rate_limit_manager.wait_if_needed(tool_name="module_history")
            
            # Use GitHub API to get commit history for the file
            repo = self.client.github.get_repo(repo_name)

            # Get commits for this file, starting from the oldest
            commits = repo.get_commits(path=file_path)

            # Get the last page (oldest commits)
            if commits.totalCount > 0:
                # Navigate to last page to get oldest commit
                last_page = (commits.totalCount - 1) // 30  # GitHub uses 30 per page
                oldest_commits = commits.get_page(last_page)

                if oldest_commits:
                    first_commit = oldest_commits[-1]  # Last item is oldest
                    return {
                        "sha": first_commit.sha,
                        "date": first_commit.commit.author.date,
                        "message": first_commit.commit.message,
                    }

            return None

        except Exception as e:
            self.logger.warning(f"Failed to get commit history for {file_path}: {e}")
            return None

    def _find_version_for_commit(
        self, commit_sha: str, commit_date: Any, version_cache: Any
    ) -> str:
        """Find which version a commit belongs to based on date."""
        # For now, use a simple approach based on major versions
        # In a more complete implementation, we'd check tags

        for major in sorted(version_cache.major_versions.keys()):
            version_info = version_cache.major_versions[major]
            # This is a simplification - ideally we'd check actual release dates
            # For now, just return the first version of the major version
            return version_info.first_version

        return "master"

    @trace_function("analyze_module_history", include_args=True)
    def analyze_module_history(
        self,
        repo_id: str,
        version: str | None = None,
        module_type: str | None = None,
        force_refresh: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ModuleHistoryResult:
        """
        Analyze module history for a configured repository.

        Args:
            repo_id: Repository ID from configuration
            version: Specific version to analyze (default: master)
            module_type: Filter to specific module type (e.g., 'analytics_adapters')
            force_refresh: Force refresh even if cache exists
            progress_callback: Optional progress callback

        Returns:
            ModuleHistoryResult with complete analysis

        Raises:
            ModuleHistoryError: If analysis fails
        """

        def update_progress(current: int, total: int, message: str):
            if progress_callback:
                progress_callback(current, total, message)

        # Get configuration
        config = self.config_manager.get_config(repo_id)
        if not config:
            raise ModuleHistoryError(
                f"No configuration found for repository: {repo_id}"
            )

        update_progress(0, 100, "Starting analysis")

        # Check cache
        if not force_refresh:
            cached = self._load_cache(config.repo_name)
            if cached:
                self.logger.info(f"Using cached data for {config.repo_name}")
                update_progress(100, 100, "Using cached data")
                return self._create_result_from_cache(cached)

        # Load version cache
        try:
            version_cache = self.cache_manager.load_cache(config.repo_name)
            if not version_cache:
                raise ModuleHistoryError(
                    f"No version cache found for {config.repo_name}. "
                    "Run repo-modules first."
                )
        except Exception as e:
            raise ModuleHistoryError(f"Failed to load version cache: {e}") from e

        update_progress(10, 100, "Version cache loaded")

        # Determine which version to analyze
        target_version = version or config.version_override or "master"

        update_progress(20, 100, f"Fetching modules from {target_version}")

        # Get modules from the specified version
        current_modules = self._get_modules_for_version(
            config, target_version, module_type
        )

        if not current_modules:
            raise ModuleHistoryError(
                f"No modules found in {target_version} for {config.repo_name}"
            )

        self.logger.info(
            f"Found {sum(len(m) for m in current_modules.values())} modules in {target_version}"
        )

        update_progress(40, 100, "Analyzing module introduction timeline")

        # Now analyze when each current module was first introduced
        # by checking historical versions
        module_history = self._analyze_module_introduction_for_version(
            config, current_modules, version_cache, update_progress, module_type
        )

        update_progress(85, 100, "Saving cache")

        # Create and save cache
        cache = HistoryCache(
            repo_name=config.repo_name,
            last_analyzed_version=target_version,
            modules=module_history,
            metadata={
                "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "analyzed_version": target_version,
                "total_modules": len(module_history),
                "version_count": len(version_cache.major_versions),
                "repo_id": repo_id,
            },
        )

        self._save_cache(cache)

        update_progress(100, 100, "Analysis complete")

        self.logger.info(
            f"Analysis complete for {config.repo_name}: {len(module_history)} modules"
        )

        return self._create_result_from_cache(cache)

    def _create_result_from_cache(self, cache: HistoryCache) -> ModuleHistoryResult:
        """Create result object from cache data."""
        # Group by type
        modules_by_type: dict[str, list[ModuleHistoryEntry]] = {}
        modules_by_version: dict[int, list[ModuleHistoryEntry]] = {}

        for entry in cache.modules.values():
            # Group by type
            if entry.module_type not in modules_by_type:
                modules_by_type[entry.module_type] = []
            modules_by_type[entry.module_type].append(entry)

            # Group by major version
            major = entry.first_major_version
            if major not in modules_by_version:
                modules_by_version[major] = []
            modules_by_version[major].append(entry)

        # Sort entries
        for entries in modules_by_type.values():
            entries.sort(key=lambda e: e.module_name)
        for entries in modules_by_version.values():
            entries.sort(key=lambda e: e.module_name)

        return ModuleHistoryResult(
            repo_name=cache.repo_name,
            total_modules=len(cache.modules),
            modules_by_type=modules_by_type,
            modules_by_version=modules_by_version,
            metadata=cache.metadata,
        )

    def get_available_repositories(self) -> list[str]:
        """Get list of available repository IDs."""
        return self.config_manager.get_available_repos()

    def clear_cache(self, repo_name: str | None = None) -> None:
        """Clear cache for a repository or all repositories."""
        try:
            if repo_name:
                cache_file = self._get_cache_file(repo_name)
                if cache_file.exists():
                    cache_file.unlink()
                    self.logger.info(f"Cache cleared for {repo_name}")
            else:
                for cache_file in self.cache_dir.glob("*_history.json"):
                    cache_file.unlink()
                self.logger.info("All caches cleared")
        except OSError as e:
            raise ModuleHistoryError(f"Failed to clear cache: {e}") from e

    def get_cache_info(self, repo_name: str) -> dict[str, Any] | None:
        """Get cache information for a repository."""
        cache_file = self._get_cache_file(repo_name)
        if not cache_file.exists():
            return None

        try:
            cache = self._load_cache(repo_name)
            if cache:
                return {
                    "cache_file": str(cache_file),
                    "repo_name": cache.repo_name,
                    "last_analyzed_version": cache.last_analyzed_version,
                    "module_count": len(cache.modules),
                    "metadata": cache.metadata,
                }
        except Exception as e:
            self.logger.warning(f"Failed to load cache info: {e}")

        return None
