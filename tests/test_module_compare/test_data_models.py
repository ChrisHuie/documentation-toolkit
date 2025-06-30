"""Tests for module comparison data models."""

from src.module_compare.data_models import (
    CategoryComparison,
    ChangeType,
    ComparisonMode,
    ComparisonResult,
    ModuleInfo,
)


class TestModuleInfo:
    """Test ModuleInfo dataclass."""

    def test_module_info_creation(self):
        """Test creating a ModuleInfo instance."""
        module = ModuleInfo(
            name="testModule",
            path="modules/testModule.js",
            category="Bid Adapters",
            repo="prebid-js",
        )

        assert module.name == "testModule"
        assert module.path == "modules/testModule.js"
        assert module.category == "Bid Adapters"
        assert module.repo == "prebid-js"

    def test_module_info_equality(self):
        """Test ModuleInfo equality comparison."""
        module1 = ModuleInfo(name="test", path="path1", category="cat1")
        module2 = ModuleInfo(name="test", path="path2", category="cat1")
        module3 = ModuleInfo(name="test", path="path1", category="cat2")
        module4 = ModuleInfo(name="other", path="path1", category="cat1")

        # Same name and category = equal (path doesn't matter for cross-repo)
        assert module1 == module2
        # Different category = not equal
        assert module1 != module3
        # Different name = not equal
        assert module1 != module4

    def test_module_info_hash(self):
        """Test ModuleInfo hashing for set operations."""
        module1 = ModuleInfo(name="test", path="path1", category="cat1")
        module2 = ModuleInfo(name="test", path="path2", category="cat1")

        # Should have same hash if equal
        assert hash(module1) == hash(module2)

        # Should work in sets
        module_set = {module1, module2}
        assert len(module_set) == 1


class TestCategoryComparison:
    """Test CategoryComparison dataclass."""

    def test_version_comparison_stats(self):
        """Test statistics for version comparison."""
        category = CategoryComparison(
            category="Bid Adapters", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )

        # Add some modules
        category.added = [
            ModuleInfo(name="new1", path="p1"),
            ModuleInfo(name="new2", path="p2"),
        ]
        category.removed = [ModuleInfo(name="old1", path="p3")]
        category.unchanged = [
            ModuleInfo(name="same1", path="p4"),
            ModuleInfo(name="same2", path="p5"),
            ModuleInfo(name="same3", path="p6"),
        ]

        # Test counts
        assert category.total_source == 4  # removed + unchanged
        assert category.total_target == 5  # added + unchanged
        assert category.has_changes is True
        assert category.net_change == 1  # 2 added - 1 removed
        assert category.change_percentage == 25.0  # (5-4)/4 * 100

    def test_repository_comparison_stats(self):
        """Test statistics for repository comparison."""
        category = CategoryComparison(
            category="Bid Adapters",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Add some modules
        category.only_in_source = [
            ModuleInfo(name="source1", path="p1"),
            ModuleInfo(name="source2", path="p2"),
        ]
        category.only_in_target = [ModuleInfo(name="target1", path="p3")]
        category.in_both = [
            ModuleInfo(name="common1", path="p4"),
            ModuleInfo(name="common2", path="p5"),
        ]

        # Test counts
        assert category.total_source == 4  # only_in_source + in_both
        assert category.total_target == 3  # only_in_target + in_both
        assert category.has_changes is True
        assert category.overlap_percentage == 40.0  # 2/(2+1+2) * 100

    def test_empty_category(self):
        """Test empty category statistics."""
        category = CategoryComparison(
            category="Empty", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )

        assert category.total_source == 0
        assert category.total_target == 0
        assert category.has_changes is False
        assert category.net_change == 0
        assert category.change_percentage == 0.0


class TestComparisonResult:
    """Test ComparisonResult dataclass."""

    def test_version_comparison_result(self):
        """Test version comparison result."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.51.0",
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        # Add categories
        cat1 = CategoryComparison(
            category="Bid Adapters", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )
        cat1.added = [ModuleInfo(name="new1", path="p1")]
        cat1.removed = [ModuleInfo(name="old1", path="p2")]
        cat1.unchanged = [ModuleInfo(name="same1", path="p3")]

        result.categories["Bid Adapters"] = cat1

        # Test properties
        assert result.is_same_repo is True
        assert len(result.all_added) == 1
        assert len(result.all_removed) == 1
        assert len(result.all_unchanged) == 1
        assert result.total_source_modules == 2
        assert result.total_target_modules == 2

    def test_repository_comparison_result(self):
        """Test repository comparison result."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.51.0",
            target_repo="prebid-server",
            target_version="v3.8.0",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Add categories
        cat1 = CategoryComparison(
            category="Bid Adapters",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )
        cat1.only_in_source = [ModuleInfo(name="js1", path="p1")]
        cat1.only_in_target = [ModuleInfo(name="server1", path="p2")]
        cat1.in_both = [ModuleInfo(name="common1", path="p3")]

        result.categories["Bid Adapters"] = cat1

        # Test properties
        assert result.is_same_repo is False
        assert len(result.all_only_in_source) == 1
        assert len(result.all_only_in_target) == 1
        assert len(result.all_in_both) == 1
        assert result.total_source_modules == 2
        assert result.total_target_modules == 2

    def test_get_statistics(self):
        """Test comprehensive statistics generation."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.51.0",
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        # Add multiple categories
        for i, cat_name in enumerate(["Bid Adapters", "Analytics", "RTD"]):
            cat = CategoryComparison(
                category=cat_name, comparison_mode=ComparisonMode.VERSION_COMPARISON
            )
            # Add different numbers to each category
            cat.added = [ModuleInfo(name=f"new{j}", path=f"p{j}") for j in range(i + 1)]
            cat.removed = [ModuleInfo(name=f"old{j}", path=f"p{j}") for j in range(i)]
            cat.unchanged = [
                ModuleInfo(name=f"same{j}", path=f"p{j}") for j in range(5)
            ]

            result.categories[cat_name] = cat

        stats = result.get_statistics()

        assert stats.comparison_mode == ComparisonMode.VERSION_COMPARISON
        assert stats.categories_count == 3
        assert stats.total_added == 6  # 1 + 2 + 3
        assert stats.total_removed == 3  # 0 + 1 + 2
        assert stats.net_change == 3
        assert len(stats.category_stats) == 3
        assert len(stats.categories_with_most_changes) == 3
        assert stats.categories_with_most_changes[0][0] == "RTD"  # Most changes

    def test_get_differences(self):
        """Test getting module differences."""
        result = ComparisonResult(
            source_repo="prebid-js",
            source_version="v9.0.0",
            target_repo="prebid-js",
            target_version="v9.51.0",
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        cat = CategoryComparison(
            category="Bid Adapters", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )
        cat.added = [ModuleInfo(name="new1", path="p1")]
        cat.removed = [ModuleInfo(name="old1", path="p2")]
        cat.unchanged = [ModuleInfo(name="same1", path="p3")]

        result.categories["Bid Adapters"] = cat

        # Without unchanged
        diffs = result.get_differences(include_unchanged=False)
        assert len(diffs) == 2
        assert any(d.change_type == ChangeType.ADDED for d in diffs)
        assert any(d.change_type == ChangeType.REMOVED for d in diffs)

        # With unchanged
        diffs = result.get_differences(include_unchanged=True)
        assert len(diffs) == 3
        assert any(d.change_type == ChangeType.UNCHANGED for d in diffs)
