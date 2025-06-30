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
        comparison_mode = (
            ComparisonMode.VERSION_COMPARISON
            if source_repo == target_repo
            else ComparisonMode.REPOSITORY_COMPARISON
        )

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
        config = self.config_manager.get_repo_config(repo_key)
        if not config:
            raise ValueError(f"Unknown repository: {repo_key}")

        # Resolve version
        resolved_version = self.github_client.resolve_version(
            config["repo"], version, version_override=config.get("version_override")
        )

        # Fetch repository data
        repo_data = self.github_client.fetch_repository_data(
            config["repo"],
            resolved_version,
            config.get("paths", {}),
            config.get("fetch_strategy", "full_content"),
            config.get("parser_type", "default"),
        )

        # Organize modules by category
        modules_by_category = defaultdict(list)
        for category, items in repo_data.items():
            for item in items:
                # Extract module name from filename/path
                module_name = self._extract_module_name(
                    item["name"], config.get("parser_type")
                )
                module_info = ModuleInfo(
                    name=module_name,
                    path=item["path"],
                    category=category,
                    repo=repo_key,
                )
                modules_by_category[category].append(module_info)

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
