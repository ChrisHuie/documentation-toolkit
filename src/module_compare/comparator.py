"""Core comparison logic for module comparison tool."""

from collections import defaultdict
from collections.abc import Callable

from src.shared_utilities import ModuleParser, get_logger
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
    ModuleRename,
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
        self.module_parser = ModuleParser()

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

        # Use the shared module parser
        parser_type = config.get("parser_type", "default")
        paths_config = config.get("paths", {})

        # Parse modules using the shared parser
        parsed_modules = self.module_parser.parse_modules(
            repo_data=repo_data,
            parser_type=parser_type,
            repo_key=repo_key,
            paths_config=paths_config,
        )

        # Convert from shared ModuleInfo to local ModuleInfo
        # This is needed because the data models still use a local ModuleInfo class
        modules_by_category = {}
        for category, modules in parsed_modules.items():
            local_modules = []
            for mod in modules:
                local_module = ModuleInfo(
                    name=mod.name,
                    path=mod.path,
                    category=mod.category,
                    repo=mod.repo,
                )
                local_modules.append(local_module)
            modules_by_category[category] = local_modules

        return modules_by_category

    def _detect_renames(
        self, removed_modules: list[ModuleInfo], added_modules: list[ModuleInfo]
    ) -> tuple[list[ModuleRename], list[ModuleInfo], list[ModuleInfo]]:
        """Detect potential module renames based on similarity.

        Args:
            removed_modules: Modules that were removed
            added_modules: Modules that were added

        Returns:
            Tuple of (renames, remaining_removed, remaining_added)
        """
        renames = []
        matched_removed = set()
        matched_added = set()

        # Known renames from git history/PRs
        known_renames = {
            # Based on PR history and commits
            "imds": "advertising",  # PR #12878 - ownership change from IMDS to Advertising.com
            "gothamads": "intenze",  # PR #6010 - rebranding to Intenze
            # Note: BT -> blockthrough is not a rename, BT is the file name but bidder code is blockthrough
            # Note: growadvertising exists as growadvertisingBidAdapter with bidder code 'growads'
        }

        # Common rename patterns
        def normalize_name(name: str) -> str:
            """Normalize name for comparison."""
            # Convert to lowercase and remove common separators
            normalized = name.lower()
            # Replace common separators with consistent one
            for sep in ["_", "-", "."]:
                normalized = normalized.replace(sep, "")
            return normalized

        def calculate_similarity(name1: str, name2: str) -> float:
            """Calculate similarity score between two names."""
            # Exact match after normalization
            if normalize_name(name1) == normalize_name(name2):
                return 1.0

            # Check if one is contained in the other (common for abbreviations)
            norm1, norm2 = normalize_name(name1), normalize_name(name2)
            if norm1 in norm2 or norm2 in norm1:
                return 0.8

            # Check if shorter name is abbreviation of longer name
            shorter, longer = (
                (name1.lower(), name2.lower())
                if len(name1) < len(name2)
                else (name2.lower(), name1.lower())
            )
            if self._is_abbreviation(shorter, longer):
                return 0.85

            # Levenshtein-like simple character comparison
            # Count common characters in same positions
            common = sum(
                1 for a, b in zip(name1.lower(), name2.lower(), strict=False) if a == b
            )
            max_len = max(len(name1), len(name2))
            if max_len == 0:
                return 0.0
            return common / max_len

        # First, check known renames
        for removed in removed_modules:
            if removed.name in known_renames:
                # Look for the known rename target
                for added in added_modules:
                    if (
                        added.name == known_renames[removed.name]
                        and added not in matched_added
                    ):
                        renames.append(
                            ModuleRename(
                                old_module=removed,
                                new_module=added,
                                similarity_score=1.0,  # Known rename, perfect score
                                detection_method="git_history",
                            )
                        )
                        matched_removed.add(removed)
                        matched_added.add(added)
                        break

        # Then try to match remaining modules based on similarity
        for removed in removed_modules:
            if removed in matched_removed:
                continue

            best_match = None
            best_score = 0.0
            best_method = "similarity"

            for added in added_modules:
                if added in matched_added:
                    continue

                # Skip if different categories
                if removed.category != added.category:
                    continue

                # Special cases for known patterns
                # camelCase to snake_case conversion
                camel_to_snake = self._camel_to_snake(removed.name)
                if camel_to_snake == added.name:
                    score = 0.95
                    detection_method = "case_change"
                # snake_case to camelCase conversion
                elif self._snake_to_camel(added.name) == removed.name:
                    score = 0.95
                    detection_method = "case_change"
                # Check for substring match first (more specific)
                elif normalize_name(removed.name) in normalize_name(
                    added.name
                ) or normalize_name(added.name) in normalize_name(removed.name):
                    score = 0.85
                    detection_method = "substring"
                # Check if it's an abbreviation match
                elif self._is_abbreviation(
                    removed.name.lower(), added.name.lower()
                ) or self._is_abbreviation(added.name.lower(), removed.name.lower()):
                    score = 0.9
                    detection_method = "abbreviation"
                else:
                    # Calculate similarity score as fallback
                    score = calculate_similarity(removed.name, added.name)
                    detection_method = "similarity"

                if score > best_score and score >= 0.7:  # Minimum threshold
                    best_match = added
                    best_score = score
                    best_method = detection_method

            if best_match:
                renames.append(
                    ModuleRename(
                        old_module=removed,
                        new_module=best_match,
                        similarity_score=best_score,
                        detection_method=best_method,
                    )
                )
                matched_removed.add(removed)
                matched_added.add(best_match)

        # Return remaining modules that weren't matched
        remaining_removed = list(set(removed_modules) - matched_removed)
        remaining_added = list(set(added_modules) - matched_added)

        return renames, remaining_removed, remaining_added

    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re

        # Insert underscore before uppercase letters
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        # Insert underscore before uppercase letters that follow lowercase
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _snake_to_camel(self, name: str) -> str:
        """Convert snake_case to camelCase."""
        components = name.split("_")
        if not components:
            return name
        # First component stays lowercase, rest are capitalized
        return components[0] + "".join(x.capitalize() for x in components[1:])

    def _is_abbreviation(self, shorter: str, longer: str) -> bool:
        """Check if shorter string is an abbreviation of longer string.

        For example: 'incrx' could be abbreviation of 'incrementx'
        """
        # All characters in shorter must appear in longer in order
        j = 0  # pointer for longer string
        for char in shorter:
            found = False
            while j < len(longer):
                if longer[j] == char:
                    found = True
                    j += 1
                    break
                j += 1
            if not found:
                return False
        return True

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

            # Calculate initial differences
            added = target_mods - source_mods
            removed = source_mods - target_mods
            unchanged = source_mods & target_mods

            # Detect renames among added/removed modules
            renames, remaining_removed, remaining_added = self._detect_renames(
                list(removed), list(added)
            )

            category_comparison = CategoryComparison(
                category=category,
                comparison_mode=ComparisonMode.VERSION_COMPARISON,
                added=sorted(remaining_added, key=lambda x: x.name),
                removed=sorted(remaining_removed, key=lambda x: x.name),
                unchanged=sorted(unchanged, key=lambda x: x.name),
                renamed=sorted(renames, key=lambda x: x.old_module.name),
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
