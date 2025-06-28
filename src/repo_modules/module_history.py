"""
Module history tracking for Prebid.js modules.

Analyzes when modules were first introduced across different versions.
"""

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..shared_utilities import get_logger, trace_function
from .github_client import GitHubClient
from .parser_factory import ParserFactory, PrebidJSParser
from .version_cache import VersionCacheManager


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
    """Tracks when modules were first introduced in Prebid.js."""

    def __init__(self, token: str | None = None, cache_dir: str | None = None):
        """Initialize module history tracker."""
        self.client = GitHubClient(token)
        self.cache_manager = VersionCacheManager()
        self.parser_factory = ParserFactory()
        self.logger = get_logger(__name__)

        # Cache directory for module history
        if cache_dir is None:
            repo_root = Path(__file__).parent.parent.parent
            self.history_cache_dir = repo_root / "cache" / "module_history"
        else:
            self.history_cache_dir = Path(cache_dir)

        self.history_cache_dir.mkdir(parents=True, exist_ok=True)

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

    def _apply_case_corrections(self, module_name: str) -> str:
        """Apply known case corrections for module names."""
        # Common case corrections based on actual Prebid.js file names
        corrections = {
            "33across": "33across",
            "adpod": "adpod",
            "adagio": "adagio",
            "appnexus": "appnexus",
            "rubicon": "rubicon",
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
                error_msg = f"No version cache found for {repo_name}. Run repo-modules-by-version first."
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
