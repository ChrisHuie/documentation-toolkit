"""
Tests for configuration refactoring - new fields and functionality.

This test suite validates:
- New RepoConfig fields (fetch_strategy, version_override, output_filename_slug)
- Backward compatibility with existing configurations
- Configuration validation and defaults
"""

from src.repo_modules_by_version.config import RepoConfig, get_available_repos


class TestRepoConfigNewFields:
    """Test new fields added to RepoConfig for configuration-driven architecture."""

    def test_repo_config_with_all_new_fields(self):
        """Test RepoConfig creation with all new fields."""
        config = RepoConfig(
            repo="test/repo",
            description="Test repository",
            versions=["v1.0.0"],
            parser_type="test",
            fetch_strategy="filenames_only",
            version_override="master",
            output_filename_slug="custom.name",
        )

        assert config.fetch_strategy == "filenames_only"
        assert config.version_override == "master"
        assert config.output_filename_slug == "custom.name"

    def test_repo_config_with_partial_new_fields(self):
        """Test RepoConfig with only some new fields specified."""
        config = RepoConfig(
            repo="test/repo",
            description="Test repository",
            versions=["v1.0.0"],
            fetch_strategy="directory_names",
            version_override="v2.0.0",
            # output_filename_slug not specified
        )

        assert config.fetch_strategy == "directory_names"
        assert config.version_override == "v2.0.0"
        assert config.output_filename_slug is None

    def test_repo_config_default_values(self):
        """Test that new fields have appropriate default values."""
        config = RepoConfig(
            repo="test/repo", description="Test repository", versions=["v1.0.0"]
        )

        assert config.fetch_strategy == "full_content"  # Default value
        assert config.version_override is None  # Default value
        assert config.output_filename_slug is None  # Default value

    def test_fetch_strategy_values(self):
        """Test different fetch strategy values."""
        strategies = ["full_content", "filenames_only", "directory_names"]

        for strategy in strategies:
            config = RepoConfig(
                repo="test/repo",
                description="Test repository",
                versions=["v1.0.0"],
                fetch_strategy=strategy,
            )
            assert config.fetch_strategy == strategy


class TestRepositoryConfigurations:
    """Test that all repository configurations include the new fields."""

    def test_all_repos_have_fetch_strategy(self):
        """Test that all configured repositories have fetch_strategy set."""
        repos = get_available_repos()

        for repo_name, config in repos.items():
            assert hasattr(
                config, "fetch_strategy"
            ), f"{repo_name} missing fetch_strategy"
            assert config.fetch_strategy in [
                "full_content",
                "filenames_only",
                "directory_names",
            ], f"{repo_name} has invalid fetch_strategy: {config.fetch_strategy}"

    def test_prebid_docs_has_version_override(self):
        """Test that prebid-docs has version_override set to master."""
        repos = get_available_repos()
        prebid_docs_config = repos.get("prebid-docs")

        assert prebid_docs_config is not None
        assert prebid_docs_config.version_override == "master"

    def test_repos_have_output_filename_slugs(self):
        """Test that repositories have appropriate output_filename_slug values."""
        repos = get_available_repos()

        expected_slugs = {
            "prebid-js": "prebid.js",
            "prebid-server": "prebid.server.go",
            "prebid-server-java": "prebid.server.java",
            "prebid-docs": "prebid.github.io",
        }

        for repo_name, expected_slug in expected_slugs.items():
            config = repos.get(repo_name)
            assert config is not None, f"Repository {repo_name} not found"
            assert (
                config.output_filename_slug == expected_slug
            ), f"{repo_name} has wrong slug: {config.output_filename_slug}"

    def test_fetch_strategies_are_appropriate(self):
        """Test that repositories have appropriate fetch strategies for their use case."""
        repos = get_available_repos()

        expected_strategies = {
            "prebid-js": "filenames_only",  # For modules parsing
            "prebid-server": "directory_names",  # For directory structure
            "prebid-server-java": "directory_names",  # For directory structure
            "prebid-docs": "filenames_only",  # For documentation files
        }

        for repo_name, expected_strategy in expected_strategies.items():
            config = repos.get(repo_name)
            assert config is not None, f"Repository {repo_name} not found"
            assert (
                config.fetch_strategy == expected_strategy
            ), f"{repo_name} has wrong strategy: {config.fetch_strategy}"


class TestBackwardCompatibility:
    """Test that existing functionality still works with new fields."""

    def test_existing_fields_unchanged(self):
        """Test that existing RepoConfig fields are unchanged."""
        config = RepoConfig(
            repo="test/repo",
            description="Test repository",
            versions=["v1.0.0"],
            parser_type="test",
            directory="test-dir",
            modules_path="modules",
            paths={"Category": "path"},
        )

        # Verify existing fields still work
        assert config.repo == "test/repo"
        assert config.description == "Test repository"
        assert config.versions == ["v1.0.0"]
        assert config.parser_type == "test"
        assert config.directory == "test-dir"
        assert config.modules_path == "modules"
        assert config.paths == {"Category": "path"}

    def test_json_loading_with_missing_new_fields(self):
        """Test that configurations load correctly even without new fields."""
        # This simulates loading old configuration files
        old_config_data = {
            "repo": "test/old-repo",
            "description": "Old repository",
            "versions": ["v1.0.0"],
            "parser_type": "default",
            # Missing new fields: fetch_strategy, version_override, output_filename_slug
        }

        config = RepoConfig(**old_config_data)

        # Should have default values for new fields
        assert config.fetch_strategy == "full_content"
        assert config.version_override is None
        assert config.output_filename_slug is None

        # Existing fields should work
        assert config.repo == "test/old-repo"
        assert config.description == "Old repository"

    def test_configuration_loading_doesnt_break(self):
        """Test that the actual repository configuration loading doesn't break."""
        # This tests the real configuration loading from repos.json
        repos = get_available_repos()

        # Should load without errors
        assert len(repos) > 0

        # All configs should be valid RepoConfig instances
        for config in repos.values():
            assert isinstance(config, RepoConfig)
            assert hasattr(config, "fetch_strategy")
            assert hasattr(config, "version_override")
            assert hasattr(config, "output_filename_slug")
