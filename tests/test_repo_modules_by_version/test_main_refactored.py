"""
Tests for refactored main.py with configuration-driven functionality.

This test suite validates:
- Version override functionality through configuration
- generate_output_filename helper function
- Configuration-driven behavior in main function
- Integration with new RepoConfig fields
"""

import pytest
from unittest.mock import Mock, patch

from src.repo_modules_by_version.config import RepoConfig
from src.repo_modules_by_version.main import generate_output_filename


class TestGenerateOutputFilename:
    """Test the generate_output_filename helper function."""

    def test_generate_filename_with_custom_slug(self):
        """Test filename generation with custom output_filename_slug."""
        config = RepoConfig(
            repo="test/repository",
            description="Test",
            versions=["v1.0.0"],
            output_filename_slug="custom.name",
        )

        result = generate_output_filename(config, "v1.2.3")
        assert result == "custom.name_modules_version_v1.2.3.txt"

    def test_generate_filename_without_custom_slug(self):
        """Test filename generation without custom slug (fallback to repo name)."""
        config = RepoConfig(
            repo="owner/test-repository",
            description="Test",
            versions=["v1.0.0"],
            # No output_filename_slug specified
        )

        result = generate_output_filename(config, "v1.2.3")
        # Should convert dashes to dots and use lowercase
        assert result == "test.repository_modules_version_v1.2.3.txt"

    def test_generate_filename_version_cleaning(self):
        """Test that version strings are properly cleaned."""
        config = RepoConfig(
            repo="test/repo",
            description="Test",
            versions=["v1.0.0"],
            output_filename_slug="test.repo",
        )

        # Test various version formats
        test_cases = [
            ("v1.0.0", "test.repo_modules_version_v1.0.0.txt"),
            ("feature/branch", "test.repo_modules_version_feature_branch.txt"),
            ("release/v2.1.0", "test.repo_modules_version_release_v2.1.0.txt"),
            ("master", "test.repo_modules_version_master.txt"),
        ]

        for version, expected in test_cases:
            result = generate_output_filename(config, version)
            assert result == expected

    def test_generate_filename_real_repositories(self):
        """Test filename generation for real repository configurations."""
        test_cases = [
            # (repo, slug, version, expected)
            (
                "prebid/Prebid.js",
                "prebid.js",
                "v9.51.0",
                "prebid.js_modules_version_v9.51.0.txt",
            ),
            (
                "prebid/prebid-server",
                "prebid.server.go",
                "v3.8.0",
                "prebid.server.go_modules_version_v3.8.0.txt",
            ),
            (
                "prebid/prebid-server-java",
                "prebid.server.java",
                "v3.27.0",
                "prebid.server.java_modules_version_v3.27.0.txt",
            ),
            (
                "prebid/prebid.github.io",
                "prebid.github.io",
                "master",
                "prebid.github.io_modules_version_master.txt",
            ),
        ]

        for repo, slug, version, expected in test_cases:
            config = RepoConfig(
                repo=repo,
                description="Test",
                versions=["master"],
                output_filename_slug=slug,
            )

            result = generate_output_filename(config, version)
            assert result == expected

    def test_generate_filename_fallback_logic(self):
        """Test filename generation fallback when no slug is provided."""
        test_cases = [
            # (repo, version, expected)
            ("owner/simple-repo", "v1.0.0", "simple.repo_modules_version_v1.0.0.txt"),
            (
                "company/complex-name-here",
                "v2.1.0",
                "complex.name.here_modules_version_v2.1.0.txt",
            ),
            ("user/CamelCase", "v1.0.0", "camelcase_modules_version_v1.0.0.txt"),
        ]

        for repo, version, expected in test_cases:
            config = RepoConfig(
                repo=repo,
                description="Test",
                versions=["master"],
                # No output_filename_slug provided
            )

            result = generate_output_filename(config, version)
            assert result == expected


class TestVersionOverrideFunctionality:
    """Test version override functionality through configuration."""

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.ParserFactory")
    def test_version_override_applied(self, mock_parser_factory, mock_github_client):
        """Test that version_override from config is applied."""
        # Setup mocks
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "master",  # Should be overridden version
            "files": {},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Create config with version override
        config = RepoConfig(
            repo="test/repo",
            description="Test",
            versions=["v1.0.0", "v2.0.0"],
            parser_type="test",
            modules_path="modules",
            fetch_strategy="filenames_only",
            version_override="master",  # This should override user input
        )

        with (
            patch(
                "src.repo_modules_by_version.main.get_repo_config_with_versions",
                return_value=config,
            ),
            patch(
                "src.repo_modules_by_version.main.get_available_repos",
                return_value={"test-repo": config},
            ),
            patch(
                "sys.argv", ["main.py", "--repo", "test-repo", "--version", "v1.0.0"]
            ),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.write = Mock()

            from src.repo_modules_by_version.main import main

            main()

            # Verify that GitHub client was called with overridden version "master", not "v1.0.0"
            mock_github.fetch_repository_data.assert_called_once()
            call_args = mock_github.fetch_repository_data.call_args
            called_version = call_args[0][1]  # Second argument is version
            assert called_version == "master", f"Expected master, got {called_version}"

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.ParserFactory")
    def test_no_version_override_preserves_user_input(
        self, mock_parser_factory, mock_github_client
    ):
        """Test that without version_override, user input is preserved."""
        # Setup mocks
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "v1.0.0",  # Should be user input
            "files": {},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Create config without version override
        config = RepoConfig(
            repo="test/repo",
            description="Test",
            versions=["v1.0.0", "v2.0.0"],
            parser_type="test",
            modules_path="modules",
            fetch_strategy="filenames_only",
            # No version_override specified
        )

        with (
            patch(
                "src.repo_modules_by_version.main.get_repo_config_with_versions",
                return_value=config,
            ),
            patch(
                "src.repo_modules_by_version.main.get_available_repos",
                return_value={"test-repo": config},
            ),
            patch(
                "sys.argv", ["main.py", "--repo", "test-repo", "--version", "v1.0.0"]
            ),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.write = Mock()

            from src.repo_modules_by_version.main import main

            main()

            # Verify that GitHub client was called with user input version "v1.0.0"
            mock_github.fetch_repository_data.assert_called_once()
            call_args = mock_github.fetch_repository_data.call_args
            called_version = call_args[0][1]  # Second argument is version
            assert called_version == "v1.0.0", f"Expected v1.0.0, got {called_version}"


class TestConfigurationDrivenBehavior:
    """Test that main function behavior is driven by configuration."""

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.ParserFactory")
    def test_fetch_strategy_passed_to_github_client(
        self, mock_parser_factory, mock_github_client
    ):
        """Test that fetch_strategy from config is passed to GitHubClient."""
        # Setup mocks
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "files": {},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Test different fetch strategies
        test_strategies = ["full_content", "filenames_only", "directory_names"]

        for strategy in test_strategies:
            mock_github.fetch_repository_data.reset_mock()

            config = RepoConfig(
                repo="test/repo",
                description="Test",
                versions=["v1.0.0"],
                parser_type="test",
                modules_path="modules",
                fetch_strategy=strategy,
            )

            with (
                patch(
                    "src.repo_modules_by_version.main.get_repo_config_with_versions",
                    return_value=config,
                ),
                patch(
                    "src.repo_modules_by_version.main.get_available_repos",
                    return_value={"test-repo": config},
                ),
                patch(
                    "sys.argv",
                    ["main.py", "--repo", "test-repo", "--version", "v1.0.0"],
                ),
                patch("builtins.open", create=True) as mock_open,
            ):
                mock_open.return_value.__enter__.return_value.write = Mock()

                from src.repo_modules_by_version.main import main

                main()

                # Verify that fetch_strategy was passed to GitHubClient
                mock_github.fetch_repository_data.assert_called_once()
                call_args = mock_github.fetch_repository_data.call_args
                called_strategy = call_args[0][5]  # Sixth argument is fetch_strategy
                assert (
                    called_strategy == strategy
                ), f"Expected {strategy}, got {called_strategy}"

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.ParserFactory")
    def test_output_filename_uses_generate_helper(
        self, mock_parser_factory, mock_github_client
    ):
        """Test that output filename uses the generate_output_filename helper."""
        # Setup mocks
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "files": {},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        config = RepoConfig(
            repo="test/custom-repo",
            description="Test",
            versions=["v1.0.0"],
            parser_type="test",
            modules_path="modules",
            fetch_strategy="filenames_only",
            output_filename_slug="custom.output.name",
        )

        with (
            patch(
                "src.repo_modules_by_version.main.get_repo_config_with_versions",
                return_value=config,
            ),
            patch(
                "src.repo_modules_by_version.main.get_available_repos",
                return_value={"test-repo": config},
            ),
            patch(
                "sys.argv", ["main.py", "--repo", "test-repo", "--version", "v2.1.0"]
            ),
            patch("builtins.open", create=True) as mock_open,
            patch("os.path.exists", return_value=False),
        ):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            from src.repo_modules_by_version.main import main

            main()

            # Verify that the file was opened with the expected filename
            expected_filename = "custom.output.name_modules_version_v2.1.0.txt"
            mock_open.assert_called_with(expected_filename, "w")

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.ParserFactory")
    def test_integration_all_new_config_fields(
        self, mock_parser_factory, mock_github_client
    ):
        """Test integration with all new configuration fields."""
        # Setup mocks
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "forced-version",
            "files": {},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Configuration using all new fields
        config = RepoConfig(
            repo="test/integration-repo",
            description="Integration test",
            versions=["v1.0.0"],
            parser_type="test",
            paths={"Category": "path"},
            fetch_strategy="directory_names",
            version_override="forced-version",
            output_filename_slug="integration.test",
        )

        with (
            patch(
                "src.repo_modules_by_version.main.get_repo_config_with_versions",
                return_value=config,
            ),
            patch(
                "src.repo_modules_by_version.main.get_available_repos",
                return_value={"test-repo": config},
            ),
            patch(
                "sys.argv",
                ["main.py", "--repo", "test-repo", "--version", "user-input"],
            ),
            patch("builtins.open", create=True) as mock_open,
            patch("os.path.exists", return_value=False),
        ):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            from src.repo_modules_by_version.main import main

            main()

            # Verify all configuration fields were used correctly
            github_call = mock_github.fetch_repository_data.call_args

            # Check version override was applied
            assert github_call[0][1] == "forced-version"  # version parameter

            # Check fetch strategy was passed
            assert github_call[0][5] == "directory_names"  # fetch_strategy parameter

            # Check filename used custom slug
            expected_filename = "integration.test_modules_version_forced-version.txt"
            mock_open.assert_called_with(expected_filename, "w")
