"""Core comparison logic for module comparison tool."""

from collections import defaultdict
from collections.abc import Callable

from src.shared_utilities import get_logger
from src.shared_utilities.github_client import GitHubClient
from src.shared_utilities.repository_config import RepositoryConfigManager
from src.shared_utilities.telemetry import trace_operation
from src.shared_utilities.version_cache import VersionCacheManager

from .data_models import (
    CategoryComparison,
    ComparisonMode,
    ComparisonResult,
    CumulativeComparisonResult,
    CumulativeModuleChange,
    ModuleInfo,
)

logger = get_logger(__name__)


class ModuleComparator:
    """Compares modules between versions or repositories."""

    def __init__(
        self, github_client: GitHubClient, config_manager: RepositoryConfigManager
    ):
        """Initialize the comparator.

        Args:
            github_client: GitHub client for API interactions
            config_manager: Repository configuration manager
        """
        self.github_client = github_client
        self.config_manager = config_manager
        self.version_cache = VersionCacheManager()

    @trace_operation("compare_modules")
    def compare(
        self,
        source_repo: str,
        source_version: str,
        target_repo: str,
        target_version: str,
        cumulative: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ComparisonResult:
        """Compare modules between two sources.

        Args:
            source_repo: Source repository identifier
            source_version: Source version/tag/branch
            target_repo: Target repository identifier
            target_version: Target version/tag/branch
            progress_callback: Optional callback for progress updates

        Returns:
            ComparisonResult with detailed comparison data
        """
        # Determine comparison mode
        if source_repo != target_repo:
            comparison_mode = ComparisonMode.REPOSITORY_COMPARISON
            cumulative = False  # Can't do cumulative for cross-repo
        elif cumulative:
            comparison_mode = ComparisonMode.CUMULATIVE_COMPARISON
        else:
            comparison_mode = ComparisonMode.VERSION_COMPARISON

        logger.info(
            "Starting module comparison",
            comparison_mode=comparison_mode.value,
            source_repo=source_repo,
            source_version=source_version,
            target_repo=target_repo,
            target_version=target_version,
        )

        # Fetch modules from both sources
        if progress_callback:
            progress_callback("Fetching source modules...")
        source_modules = self._fetch_modules(source_repo, source_version)

        if progress_callback:
            progress_callback("Fetching target modules...")
        target_modules = self._fetch_modules(target_repo, target_version)

        # Perform comparison
        if progress_callback:
            progress_callback("Comparing modules...")

        if comparison_mode == ComparisonMode.VERSION_COMPARISON:
            result = self._compare_versions(
                source_repo,
                source_version,
                source_modules,
                target_repo,
                target_version,
                target_modules,
            )
        elif comparison_mode == ComparisonMode.CUMULATIVE_COMPARISON:
            result = self._compare_cumulative(
                source_repo,
                source_version,
                target_version,
                progress_callback,
            )
        else:
            result = self._compare_repositories(
                source_repo,
                source_version,
                source_modules,
                target_repo,
                target_version,
                target_modules,
            )

        logger.info("Comparison completed", summary=result.summary_stats)

        return result

    def _fetch_modules(
        self, repo_key: str, version: str
    ) -> dict[str, list[ModuleInfo]]:
        """Fetch modules from a repository at a specific version.

        Args:
            repo_key: Repository identifier (from config)
            version: Version/tag/branch to fetch

        Returns:
            Dictionary mapping category names to lists of modules
        """
        # Get repository configuration
        config = self.config_manager.get_config(repo_key)
        if not config:
            raise ValueError(f"Unknown repository: {repo_key}")

        # Handle version override if configured
        actual_version = config.get("version_override") or version

        # Fetch repository data
        repo_data = self.github_client.fetch_repository_data(
            repo_name=config["repo"],
            version=actual_version,
            paths=config.get("paths", {}),
            fetch_strategy=config.get("fetch_strategy", "full_content"),
        )

        # Organize modules by category
        modules_by_category = defaultdict(list)

        # Handle the response structure from GitHub client
        if "paths" in repo_data:
            # Multi-path structure
            paths_data = repo_data["paths"]
            # Map paths to categories from config
            path_to_category = {v: k for k, v in config.get("paths", {}).items()}

            for path, files in paths_data.items():
                category = path_to_category.get(path, "Other")
                for file_path, _ in files.items():
                    # Extract filename from full path
                    filename = file_path.split("/")[-1]
                    module_name = self._extract_module_name(
                        filename, config.get("parser_type")
                    )
                    module_info = ModuleInfo(
                        name=module_name,
                        path=file_path,
                        category=category,
                        repo=repo_key,
                    )
                    modules_by_category[category].append(module_info)
        else:
            # Legacy single directory structure - shouldn't happen with our conversion
            logger.warning(f"Unexpected repo_data structure for {repo_key}")
            # Try to handle it as a flat dictionary
            for file_path, _ in repo_data.get("files", {}).items():
                filename = file_path.split("/")[-1]
                module_name = self._extract_module_name(
                    filename, config.get("parser_type")
                )
                module_info = ModuleInfo(
                    name=module_name,
                    path=file_path,
                    category="Modules",
                    repo=repo_key,
                )
                modules_by_category["Modules"].append(module_info)

        return dict(modules_by_category)

    def _extract_module_name(self, filename: str, parser_type: str | None) -> str:
        """Extract module name from filename based on parser type.

        Args:
            filename: The filename to extract from
            parser_type: The parser type for the repository

        Returns:
            Extracted module name
        """
        # Remove file extensions
        name = (
            filename.replace(".js", "")
            .replace(".go", "")
            .replace(".java", "")
            .replace(".md", "")
        )

        # Handle specific parser types
        if parser_type == "prebid_js":
            # Remove "BidAdapter" suffix for bid adapters
            if name.endswith("BidAdapter"):
                name = name[:-10]
            # Remove "AnalyticsAdapter" suffix
            elif name.endswith("AnalyticsAdapter"):
                name = name[:-16]
            # Remove "RtdProvider" suffix
            elif name.endswith("RtdProvider"):
                name = name[:-11]
            # Remove "IdSystem" suffix
            elif name.endswith("IdSystem"):
                name = name[:-8]

        return name

    def _compare_versions(
        self,
        source_repo: str,
        source_version: str,
        source_modules: dict[str, list[ModuleInfo]],
        target_repo: str,
        target_version: str,
        target_modules: dict[str, list[ModuleInfo]],
    ) -> ComparisonResult:
        """Compare modules between two versions of the same repository.

        Returns:
            ComparisonResult with added/removed/unchanged modules
        """
        result = ComparisonResult(
            source_repo=source_repo,
            source_version=source_version,
            target_repo=target_repo,
            target_version=target_version,
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        # Get all categories
        all_categories = set(source_modules.keys()) | set(target_modules.keys())

        for category in sorted(all_categories):
            source_mods = set(source_modules.get(category, []))
            target_mods = set(target_modules.get(category, []))

            # Calculate differences
            added = target_mods - source_mods
            removed = source_mods - target_mods
            unchanged = source_mods & target_mods

            category_comparison = CategoryComparison(
                category=category,
                comparison_mode=ComparisonMode.VERSION_COMPARISON,
                added=sorted(added, key=lambda x: x.name),
                removed=sorted(removed, key=lambda x: x.name),
                unchanged=sorted(unchanged, key=lambda x: x.name),
            )

            result.categories[category] = category_comparison

        return result

    def _compare_repositories(
        self,
        source_repo: str,
        source_version: str,
        source_modules: dict[str, list[ModuleInfo]],
        target_repo: str,
        target_version: str,
        target_modules: dict[str, list[ModuleInfo]],
    ) -> ComparisonResult:
        """Compare modules between different repositories.

        Returns:
            ComparisonResult with only_in_source/only_in_target/in_both modules
        """
        result = ComparisonResult(
            source_repo=source_repo,
            source_version=source_version,
            target_repo=target_repo,
            target_version=target_version,
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Get all categories (some may only exist in one repo)
        all_categories = set(source_modules.keys()) | set(target_modules.keys())

        for category in sorted(all_categories):
            source_mods = set(source_modules.get(category, []))
            target_mods = set(target_modules.get(category, []))

            # For cross-repo comparison, match by module name only
            source_names = {mod.name: mod for mod in source_mods}
            target_names = {mod.name: mod for mod in target_mods}

            # Calculate differences
            only_in_source = []
            only_in_target = []
            in_both = []

            # Find modules only in source
            for name, mod in source_names.items():
                if name not in target_names:
                    only_in_source.append(mod)
                else:
                    in_both.append(mod)

            # Find modules only in target
            for name, mod in target_names.items():
                if name not in source_names:
                    only_in_target.append(mod)

            category_comparison = CategoryComparison(
                category=category,
                comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
                only_in_source=sorted(only_in_source, key=lambda x: x.name),
                only_in_target=sorted(only_in_target, key=lambda x: x.name),
                in_both=sorted(in_both, key=lambda x: x.name),
            )

            result.categories[category] = category_comparison

        return result

    def _compare_cumulative(
        self,
        repo: str,
        source_version: str,
        target_version: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> CumulativeComparisonResult:
        """Compare modules cumulatively across all versions between source and target.

        This tracks ALL module changes that occurred between two versions,
        not just the direct difference between endpoints.

        Args:
            repo: Repository identifier
            source_version: Starting version
            target_version: Ending version
            progress_callback: Optional callback for progress updates

        Returns:
            CumulativeComparisonResult with all module changes tracked
        """
        logger.info(
            "Starting cumulative comparison",
            repo=repo,
            source_version=source_version,
            target_version=target_version,
        )

        # Get version cache to find intermediate versions
        version_cache = self.version_cache.load_cache(
            self.config_manager.get_config(repo)["repo"]
        )
        if not version_cache:
            # Fall back to empty cumulative result if no cache
            logger.warning(
                "No version cache available, returning empty cumulative result"
            )
            return CumulativeComparisonResult(
                source_repo=repo,
                source_version=source_version,
                target_repo=repo,
                target_version=target_version,
                comparison_mode=ComparisonMode.CUMULATIVE_COMPARISON,
                cumulative_changes={},
                versions_analyzed=[source_version, target_version],
            )

        # Parse version numbers for comparison
        def parse_version(v: str) -> tuple[int, int, int]:
            clean = v.lstrip("v")
            parts = clean.split(".")
            try:
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            except (ValueError, IndexError):
                return (0, 0, 0)

        source_parsed = parse_version(source_version)
        target_parsed = parse_version(target_version)

        # Get all versions between source and target
        all_versions = []
        for version in version_cache.latest_versions:
            v_parsed = parse_version(version)
            if source_parsed <= v_parsed <= target_parsed:
                all_versions.append(version)

        # Also check major versions for any missing versions
        for major_info in version_cache.major_versions.values():
            for v in [major_info.first_version, major_info.last_version]:
                v_parsed = parse_version(v)
                if source_parsed <= v_parsed <= target_parsed and v not in all_versions:
                    all_versions.append(v)

        # Sort versions
        all_versions.sort(key=parse_version)

        if not all_versions:
            all_versions = [source_version, target_version]

        # Ensure source and target are included
        if source_version not in all_versions:
            all_versions.insert(0, source_version)
        if target_version not in all_versions:
            all_versions.append(target_version)

        logger.info(f"Analyzing {len(all_versions)} versions for cumulative changes")

        # Track all modules seen across versions
        cumulative_changes = defaultdict(list)
        all_modules_by_version = {}

        # Fetch modules for each version
        for i, version in enumerate(all_versions):
            if progress_callback:
                progress_callback(
                    f"Analyzing version {version} ({i + 1}/{len(all_versions)})"
                )

            modules = self._fetch_modules(repo, version)
            all_modules_by_version[version] = modules

        # Track module lifecycle
        module_first_seen = {}
        module_last_seen = {}
        all_modules_ever = set()

        # Process versions in order to track when modules appear/disappear
        for version in all_versions:
            modules = all_modules_by_version[version]

            # Flatten all modules with category info
            current_modules = set()
            for category, mod_list in modules.items():
                for mod in mod_list:
                    key = (mod.name, category)
                    current_modules.add(key)
                    all_modules_ever.add(key)

                    if key not in module_first_seen:
                        module_first_seen[key] = version
                    module_last_seen[key] = version

        # Get final state modules
        target_modules = all_modules_by_version[target_version]
        target_module_keys = set()
        for category, mod_list in target_modules.items():
            for mod in mod_list:
                target_module_keys.add((mod.name, category))

        # Create cumulative change entries
        for module_key in all_modules_ever:
            name, category = module_key
            first_version = module_first_seen[module_key]

            # Skip if module existed in source version
            source_modules = all_modules_by_version[source_version]
            existed_in_source = any(
                mod.name == name
                for cat_mods in source_modules.values()
                for mod in cat_mods
                if cat_mods
            )

            if existed_in_source:
                continue

            # This module was added after source version
            module_info = ModuleInfo(
                name=name,
                path="",  # Path will be filled from actual module data
                category=category,
                repo=repo,
            )

            # Find actual module info from when it was first seen
            for mod_list in all_modules_by_version[first_version].values():
                for mod in mod_list:
                    if mod.name == name:
                        module_info = mod
                        break

            # Check if module was removed
            removed_version = None
            if module_key not in target_module_keys:
                # Module was removed - find when
                last_version = module_last_seen[module_key]
                last_idx = all_versions.index(last_version)
                if last_idx < len(all_versions) - 1:
                    removed_version = all_versions[last_idx + 1]

            change = CumulativeModuleChange(
                module=module_info,
                added_in_version=first_version,
                removed_in_version=removed_version,
                is_present_in_target=module_key in target_module_keys,
            )

            cumulative_changes[category].append(change)

        # Sort changes by module name
        for changes in cumulative_changes.values():
            changes.sort(key=lambda x: x.module.name)

        # Create result
        result = CumulativeComparisonResult(
            source_repo=repo,
            source_version=source_version,
            target_repo=repo,
            target_version=target_version,
            comparison_mode=ComparisonMode.CUMULATIVE_COMPARISON,
            cumulative_changes=dict(cumulative_changes),
            versions_analyzed=all_versions,
        )

        logger.info(
            "Cumulative comparison completed",
            total_changes=sum(len(changes) for changes in cumulative_changes.values()),
            versions_analyzed=len(all_versions),
        )

        return result
