"""Data models for module comparison results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComparisonMode(Enum):
    """Type of comparison being performed."""

    VERSION_COMPARISON = "version"  # Same repo, different versions
    REPOSITORY_COMPARISON = "repository"  # Different repos


class ChangeType(Enum):
    """Types of changes in module comparison."""

    # For version comparison (same repo)
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"

    # For repository comparison (cross-repo)
    ONLY_IN_SOURCE = "only_in_source"
    ONLY_IN_TARGET = "only_in_target"
    IN_BOTH = "in_both"


@dataclass
class ModuleInfo:
    """Information about a module."""

    name: str
    path: str
    category: str | None = None
    repo: str | None = None  # Repository this module belongs to

    def __hash__(self):
        return hash((self.name, self.category))

    def __eq__(self, other):
        if not isinstance(other, ModuleInfo):
            return False
        # For cross-repo comparison, match by name and category only
        return self.name == other.name and self.category == other.category


@dataclass
class ModuleDifference:
    """Represents a difference in modules between two sources."""

    module: ModuleInfo
    change_type: ChangeType
    source_version: str
    target_version: str


@dataclass
class CategoryComparison:
    """Comparison results for a specific category."""

    category: str
    comparison_mode: ComparisonMode

    # For version comparison (same repo)
    added: list[ModuleInfo] = field(default_factory=list)
    removed: list[ModuleInfo] = field(default_factory=list)
    unchanged: list[ModuleInfo] = field(default_factory=list)

    # For repository comparison (cross-repo)
    only_in_source: list[ModuleInfo] = field(default_factory=list)
    only_in_target: list[ModuleInfo] = field(default_factory=list)
    in_both: list[ModuleInfo] = field(default_factory=list)

    @property
    def total_source(self) -> int:
        """Total modules in source."""
        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            return len(self.removed) + len(self.unchanged)
        else:
            return len(self.only_in_source) + len(self.in_both)

    @property
    def total_target(self) -> int:
        """Total modules in target."""
        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            return len(self.added) + len(self.unchanged)
        else:
            return len(self.only_in_target) + len(self.in_both)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            return bool(self.added or self.removed)
        else:
            return bool(self.only_in_source or self.only_in_target)

    @property
    def net_change(self) -> int:
        """Net change in modules (version comparison only)."""
        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            return len(self.added) - len(self.removed)
        return 0

    @property
    def change_percentage(self) -> float:
        """Percentage change from source to target."""
        if self.total_source == 0:
            return 100.0 if self.total_target > 0 else 0.0
        return ((self.total_target - self.total_source) / self.total_source) * 100

    @property
    def overlap_percentage(self) -> float:
        """Percentage of overlap (repository comparison only)."""
        if self.comparison_mode != ComparisonMode.REPOSITORY_COMPARISON:
            return 0.0
        total = len(self.only_in_source) + len(self.only_in_target) + len(self.in_both)
        if total == 0:
            return 0.0
        return (len(self.in_both) / total) * 100

    def get_statistics(self) -> dict[str, Any]:
        """Get category-specific statistics."""
        stats = {
            "category": self.category,
            "source_total": self.total_source,
            "target_total": self.total_target,
        }

        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            stats.update(
                {
                    "added": len(self.added),
                    "removed": len(self.removed),
                    "unchanged": len(self.unchanged),
                    "net_change": self.net_change,
                    "change_percentage": round(self.change_percentage, 1),
                }
            )
        else:
            stats.update(
                {
                    "only_in_source": len(self.only_in_source),
                    "only_in_target": len(self.only_in_target),
                    "in_both": len(self.in_both),
                    "overlap_percentage": round(self.overlap_percentage, 1),
                }
            )

        return stats


@dataclass
class ComparisonStatistics:
    """Detailed statistics for the comparison."""

    comparison_mode: ComparisonMode

    # Overall stats
    source_total: int = 0
    target_total: int = 0
    categories_count: int = 0

    # Version comparison stats
    total_added: int = 0
    total_removed: int = 0
    total_unchanged: int = 0
    net_change: int = 0
    overall_change_percentage: float = 0.0

    # Repository comparison stats
    total_only_in_source: int = 0
    total_only_in_target: int = 0
    total_in_both: int = 0
    overall_overlap_percentage: float = 0.0

    # Category breakdowns
    category_stats: list[dict[str, Any]] = field(default_factory=list)
    categories_with_most_changes: list[tuple[str, int]] = field(default_factory=list)
    categories_by_growth_rate: list[tuple[str, float]] = field(default_factory=list)

    # Repository comparison specific
    unique_categories_source: list[str] = field(default_factory=list)
    unique_categories_target: list[str] = field(default_factory=list)
    common_categories: list[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Complete comparison result between two module sources."""

    source_repo: str
    source_version: str
    target_repo: str
    target_version: str
    comparison_mode: ComparisonMode
    categories: dict[str, CategoryComparison] = field(default_factory=dict)

    @property
    def is_same_repo(self) -> bool:
        """Check if comparing versions of the same repository."""
        return self.source_repo == self.target_repo

    @property
    def all_added(self) -> list[ModuleInfo]:
        """Get all added modules (version comparison only)."""
        if self.comparison_mode != ComparisonMode.VERSION_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.added)
        return modules

    @property
    def all_removed(self) -> list[ModuleInfo]:
        """Get all removed modules (version comparison only)."""
        if self.comparison_mode != ComparisonMode.VERSION_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.removed)
        return modules

    @property
    def all_unchanged(self) -> list[ModuleInfo]:
        """Get all unchanged modules (version comparison only)."""
        if self.comparison_mode != ComparisonMode.VERSION_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.unchanged)
        return modules

    @property
    def all_only_in_source(self) -> list[ModuleInfo]:
        """Get modules only in source (repository comparison only)."""
        if self.comparison_mode != ComparisonMode.REPOSITORY_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.only_in_source)
        return modules

    @property
    def all_only_in_target(self) -> list[ModuleInfo]:
        """Get modules only in target (repository comparison only)."""
        if self.comparison_mode != ComparisonMode.REPOSITORY_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.only_in_target)
        return modules

    @property
    def all_in_both(self) -> list[ModuleInfo]:
        """Get modules in both (repository comparison only)."""
        if self.comparison_mode != ComparisonMode.REPOSITORY_COMPARISON:
            return []
        modules = []
        for category in self.categories.values():
            modules.extend(category.in_both)
        return modules

    @property
    def total_source_modules(self) -> int:
        """Total modules in source."""
        return sum(cat.total_source for cat in self.categories.values())

    @property
    def total_target_modules(self) -> int:
        """Total modules in target."""
        return sum(cat.total_target for cat in self.categories.values())

    def get_statistics(self) -> ComparisonStatistics:
        """Calculate comprehensive statistics for the comparison."""
        stats = ComparisonStatistics(comparison_mode=self.comparison_mode)

        # Basic counts
        stats.source_total = self.total_source_modules
        stats.target_total = self.total_target_modules
        stats.categories_count = len(self.categories)

        # Category statistics
        stats.category_stats = [
            cat.get_statistics() for cat in self.categories.values()
        ]

        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            # Version comparison statistics
            stats.total_added = len(self.all_added)
            stats.total_removed = len(self.all_removed)
            stats.total_unchanged = len(self.all_unchanged)
            stats.net_change = stats.total_added - stats.total_removed

            if stats.source_total > 0:
                stats.overall_change_percentage = (
                    (stats.target_total - stats.source_total) / stats.source_total
                ) * 100

            # Categories with most changes
            changes_by_category = [
                (cat.category, len(cat.added) + len(cat.removed))
                for cat in self.categories.values()
            ]
            stats.categories_with_most_changes = sorted(
                changes_by_category, key=lambda x: x[1], reverse=True
            )

            # Categories by growth rate
            growth_by_category = [
                (cat.category, cat.change_percentage)
                for cat in self.categories.values()
                if cat.total_source > 0  # Avoid division by zero
            ]
            stats.categories_by_growth_rate = sorted(
                growth_by_category, key=lambda x: x[1], reverse=True
            )

        else:
            # Repository comparison statistics
            stats.total_only_in_source = len(self.all_only_in_source)
            stats.total_only_in_target = len(self.all_only_in_target)
            stats.total_in_both = len(self.all_in_both)

            total_unique = (
                stats.total_only_in_source
                + stats.total_only_in_target
                + stats.total_in_both
            )
            if total_unique > 0:
                stats.overall_overlap_percentage = (
                    stats.total_in_both / total_unique
                ) * 100

            # Category analysis
            source_categories = {
                cat for cat, comp in self.categories.items() if comp.total_source > 0
            }
            target_categories = {
                cat for cat, comp in self.categories.items() if comp.total_target > 0
            }

            stats.unique_categories_source = sorted(
                source_categories - target_categories
            )
            stats.unique_categories_target = sorted(
                target_categories - source_categories
            )
            stats.common_categories = sorted(source_categories & target_categories)

        return stats

    @property
    def summary_stats(self) -> dict[str, Any]:
        """Get summary statistics (backward compatibility)."""
        stats = self.get_statistics()

        summary = {
            "source_repo": self.source_repo,
            "source_version": self.source_version,
            "target_repo": self.target_repo,
            "target_version": self.target_version,
            "comparison_mode": self.comparison_mode.value,
            "source_total": stats.source_total,
            "target_total": stats.target_total,
            "categories": stats.categories_count,
        }

        if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
            summary.update(
                {
                    "added": stats.total_added,
                    "removed": stats.total_removed,
                    "unchanged": stats.total_unchanged,
                    "net_change": stats.net_change,
                    "change_percentage": round(stats.overall_change_percentage, 1),
                }
            )
        else:
            summary.update(
                {
                    "only_in_source": stats.total_only_in_source,
                    "only_in_target": stats.total_only_in_target,
                    "in_both": stats.total_in_both,
                    "overlap_percentage": round(stats.overall_overlap_percentage, 1),
                }
            )

        return summary

    def get_differences(
        self, include_unchanged: bool = False
    ) -> list[ModuleDifference]:
        """Get module differences, optionally including unchanged/common modules."""
        differences = []

        for category in self.categories.values():
            if self.comparison_mode == ComparisonMode.VERSION_COMPARISON:
                for module in category.added:
                    differences.append(
                        ModuleDifference(
                            module=module,
                            change_type=ChangeType.ADDED,
                            source_version=self.source_version,
                            target_version=self.target_version,
                        )
                    )

                for module in category.removed:
                    differences.append(
                        ModuleDifference(
                            module=module,
                            change_type=ChangeType.REMOVED,
                            source_version=self.source_version,
                            target_version=self.target_version,
                        )
                    )

                if include_unchanged:
                    for module in category.unchanged:
                        differences.append(
                            ModuleDifference(
                                module=module,
                                change_type=ChangeType.UNCHANGED,
                                source_version=self.source_version,
                                target_version=self.target_version,
                            )
                        )
            else:
                for module in category.only_in_source:
                    differences.append(
                        ModuleDifference(
                            module=module,
                            change_type=ChangeType.ONLY_IN_SOURCE,
                            source_version=self.source_version,
                            target_version=self.target_version,
                        )
                    )

                for module in category.only_in_target:
                    differences.append(
                        ModuleDifference(
                            module=module,
                            change_type=ChangeType.ONLY_IN_TARGET,
                            source_version=self.source_version,
                            target_version=self.target_version,
                        )
                    )

                if include_unchanged:
                    for module in category.in_both:
                        differences.append(
                            ModuleDifference(
                                module=module,
                                change_type=ChangeType.IN_BOTH,
                                source_version=self.source_version,
                                target_version=self.target_version,
                            )
                        )

        return differences

    def get_categories_with_changes(self) -> list[str]:
        """Get list of categories that have changes."""
        return [cat for cat, comp in self.categories.items() if comp.has_changes]
