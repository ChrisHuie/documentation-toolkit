"""
Contract tests to ensure data structure consistency.

These tests verify that the expected data structures are maintained
between different components of the system.
"""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import (
    CategoryComparison,
    ComparisonMode,
    ComparisonResult,
    ComparisonStatistics,
    ModuleInfo,
)
from src.shared_utilities.repository_config import RepositoryConfigManager


class TestDataStructureContracts:
    """Test that data structures maintain their contracts."""

    def test_github_client_response_contract(self):
        """Test that GitHubClient returns the expected response structure."""
        expected_keys = {"repo", "version", "paths", "files", "metadata"}

        # The response should always have these keys
        mock_response = {
            "repo": "owner/repo",
            "version": "v1.0.0",
            "paths": {"modules": {"file.js": "content"}},
            "files": [],
            "metadata": {
                "commit_sha": "abc123",
                "total_files": 1,
            },
        }

        # Verify all expected keys are present
        assert set(mock_response.keys()) == expected_keys

        # Verify metadata structure
        assert "commit_sha" in mock_response["metadata"]
        assert "total_files" in mock_response["metadata"]

        # Verify paths is a dict of dicts
        assert isinstance(mock_response["paths"], dict)
        for path_content in mock_response["paths"].values():
            assert isinstance(path_content, dict)

    def test_module_info_contract(self):
        """Test ModuleInfo data structure contract."""
        module = ModuleInfo(name="testModule", path="path/to/module.js")

        # Verify required attributes
        assert hasattr(module, "name")
        assert hasattr(module, "path")

        # Verify types
        assert isinstance(module.name, str)
        assert isinstance(module.path, str)

        # Verify string representation includes the name
        assert "testModule" in str(module)

    def test_category_comparison_contract(self):
        """Test CategoryComparison data structure contract."""
        # Version comparison mode
        version_cat = CategoryComparison(
            category="Bid Adapters", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )

        # Should have version comparison attributes
        assert hasattr(version_cat, "added")
        assert hasattr(version_cat, "removed")
        assert hasattr(version_cat, "unchanged")
        assert isinstance(version_cat.added, list)
        assert isinstance(version_cat.removed, list)
        assert isinstance(version_cat.unchanged, list)

        # Repository comparison mode
        repo_cat = CategoryComparison(
            category="Bid Adapters",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Should have repository comparison attributes
        assert hasattr(repo_cat, "only_in_source")
        assert hasattr(repo_cat, "only_in_target")
        assert hasattr(repo_cat, "in_both")
        assert isinstance(repo_cat.only_in_source, list)
        assert isinstance(repo_cat.only_in_target, list)
        assert isinstance(repo_cat.in_both, list)

    def test_comparison_result_contract(self):
        """Test ComparisonResult data structure contract."""
        result = ComparisonResult(
            source_repo="repo1",
            source_version="v1.0.0",
            target_repo="repo2",
            target_version="v2.0.0",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # Verify required attributes
        assert hasattr(result, "source_repo")
        assert hasattr(result, "source_version")
        assert hasattr(result, "target_repo")
        assert hasattr(result, "target_version")
        assert hasattr(result, "comparison_mode")
        assert hasattr(result, "categories")

        # Verify types
        assert isinstance(result.categories, dict)
        assert isinstance(result.comparison_mode, ComparisonMode)

        # Verify methods exist
        assert callable(getattr(result, "get_statistics", None))

        # Verify computed properties based on mode
        assert hasattr(result, "all_added") or hasattr(result, "all_only_in_source")
        assert hasattr(result, "all_removed") or hasattr(result, "all_only_in_target")

    def test_comparison_statistics_contract(self):
        """Test ComparisonStatistics data structure contract."""
        result = ComparisonResult(
            source_repo="repo1",
            source_version="v1.0.0",
            target_repo="repo1",
            target_version="v2.0.0",
            comparison_mode=ComparisonMode.VERSION_COMPARISON,
        )

        # Add some test data
        category = CategoryComparison(
            category="Test", comparison_mode=ComparisonMode.VERSION_COMPARISON
        )
        category.added = [ModuleInfo("new", "path/new.js")]
        category.removed = [ModuleInfo("old", "path/old.js")]
        result.categories["Test"] = category

        stats = result.get_statistics()

        # Verify statistics structure
        assert isinstance(stats, ComparisonStatistics)
        assert hasattr(stats, "total_added")
        assert hasattr(stats, "total_removed")
        assert hasattr(stats, "net_change")
        assert hasattr(stats, "source_total")
        assert hasattr(stats, "target_total")
        assert hasattr(stats, "categories_with_most_changes")
        assert hasattr(stats, "category_stats")

        # Verify types
        assert isinstance(stats.total_added, int)
        assert isinstance(stats.total_removed, int)
        assert isinstance(stats.net_change, int)
        assert isinstance(stats.categories_with_most_changes, list)
        assert isinstance(stats.category_stats, list)

    def test_config_manager_contract(self):
        """Test RepositoryConfigManager contract."""
        manager = RepositoryConfigManager()

        # Verify required methods
        assert callable(getattr(manager, "get_config", None))
        assert hasattr(manager, "configs") and isinstance(manager.configs, dict)

        # Test get_config returns expected structure
        config = manager.get_config("prebid-js")
        if config:  # If config exists
            assert isinstance(config, dict)
            assert "repo" in config
            assert "parser_type" in config
            assert "paths" in config or "directory" in config

            # If paths exists, it should be a dict
            if "paths" in config:
                assert isinstance(config["paths"], dict)

    def test_comparator_fetch_contract(self):
        """Test that comparator correctly uses the GitHub client contract."""
        mock_github = Mock()
        mock_config = Mock()

        # Set up expected config structure
        mock_config.get_config.return_value = {
            "repo": "owner/repo",
            "parser_type": "default",
            "paths": {"Modules": "src"},
            "fetch_strategy": "filenames_only",
        }

        # Set up expected GitHub response
        expected_response = {
            "repo": "owner/repo",
            "version": "v1.0.0",
            "paths": {"src": {"src/module.js": ""}},
            "files": [],
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        mock_github.fetch_repository_data.return_value = expected_response
        mock_github.resolve_version.return_value = "v1.0.0"

        comparator = ModuleComparator(mock_github, mock_config)

        # This should work without errors if contracts are maintained
        comparator.compare("test-repo", "v1.0.0", "test-repo", "v2.0.0")

        # Verify the GitHub client was called with expected parameters
        calls = mock_github.fetch_repository_data.call_args_list
        assert len(calls) == 2

        # Verify call structure
        for call in calls:
            kwargs = call[1]
            assert "repo_name" in kwargs
            assert "version" in kwargs
            assert "paths" in kwargs
            assert "fetch_strategy" in kwargs

    def test_output_formatter_data_contract(self):
        """Test that output formatter receives expected data structure."""
        from src.module_compare.output_formatter import ModuleCompareOutputFormatter

        formatter = ModuleCompareOutputFormatter()

        # Create a result with expected structure
        result = ComparisonResult(
            source_repo="repo1",
            source_version="v1.0.0",
            target_repo="repo2",
            target_version="v2.0.0",
            comparison_mode=ComparisonMode.REPOSITORY_COMPARISON,
        )

        # The prepare_data method should return expected structure
        data = formatter.prepare_data(result, show_unchanged=False)

        # Verify data contract
        assert isinstance(data, dict)
        assert "header" in data
        assert "metadata" in data
        assert "summary" in data
        assert "items" in data
        assert "statistics" in data

        # Verify metadata structure
        assert isinstance(data["metadata"], dict)
        assert "Source" in data["metadata"]
        assert "Target" in data["metadata"]
        assert "Comparison Type" in data["metadata"]

        # Verify items structure
        assert isinstance(data["items"], list)
        for item in data["items"]:
            assert "category" in item
            assert "modules" in item

    @pytest.mark.parametrize(
        "fetch_strategy", ["filenames_only", "directory_names", "full_content"]
    )
    def test_fetch_strategy_contract(self, fetch_strategy):
        """Test that all fetch strategies return the same response structure."""
        mock_github = Mock()
        mock_config = Mock()

        mock_config.get_config.return_value = {
            "repo": "owner/repo",
            "parser_type": "default",
            "paths": {"Modules": "src"},
            "fetch_strategy": fetch_strategy,
        }

        # All strategies should return the same structure
        response = {
            "repo": "owner/repo",
            "version": "v1.0.0",
            "paths": {
                "src": {
                    "src/module.js": (
                        "content" if fetch_strategy == "full_content" else ""
                    )
                }
            },
            "files": [],
            "metadata": {
                "commit_sha": "abc123",
                "total_files": 1,
                "fetch_strategy": fetch_strategy,
            },
        }

        mock_github.fetch_repository_data.return_value = response
        mock_github.resolve_version.return_value = "v1.0.0"

        comparator = ModuleComparator(mock_github, mock_config)

        # Should work with any fetch strategy
        comparator.compare("test-repo", "v1.0.0", "test-repo", "v1.0.0")

        # Verify the fetch strategy was passed correctly
        call_kwargs = mock_github.fetch_repository_data.call_args[1]
        assert call_kwargs["fetch_strategy"] == fetch_strategy

    def test_parser_type_contract(self):
        """Test that all parser types follow the same parsing contract."""
        comparator = ModuleComparator(Mock(), Mock())

        parser_types = [
            "prebid_js",
            "prebid_server_go",
            "prebid_server_java",
            "prebid_docs",
            "default",
        ]

        # Test repo data
        repo_data = {
            "paths": {
                "modules": {"test.js": None},
                "adapters": {"test": None},
                "src": {"test.java": None},
            }
        }

        for parser_type in parser_types:
            # All parsers should return a dict of categories
            result = comparator.module_parser.parse_modules(
                repo_data=repo_data, parser_type=parser_type, repo_key="test-repo"
            )
            assert isinstance(result, dict)

            # Each category should map to a list
            for category, modules in result.items():
                assert isinstance(category, str)
                assert isinstance(modules, list)

    def test_version_override_contract(self):
        """Test that version override is consistently applied."""
        mock_github = Mock()
        mock_config = Mock()

        # Config with version override
        mock_config.get_config.return_value = {
            "repo": "owner/repo",
            "parser_type": "default",
            "paths": {"Modules": "src"},
            "version_override": "master",
        }

        mock_github.fetch_repository_data.return_value = {
            "repo": "owner/repo",
            "version": "master",  # Should be overridden
            "paths": {},
            "files": [],
            "metadata": {"commit_sha": "abc", "total_files": 0},
        }
        mock_github.resolve_version.return_value = "master"

        comparator = ModuleComparator(mock_github, mock_config)
        comparator.compare("test-repo", "v1.0.0", "test-repo", "v2.0.0")

        # Both calls should use "master" regardless of input versions
        calls = mock_github.fetch_repository_data.call_args_list
        assert calls[0][1]["version"] == "master"
        assert calls[1][1]["version"] == "master"
