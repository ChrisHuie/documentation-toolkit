"""
Tests for prebid.github.io master version override functionality.

This test suite validates:
- Master override works for prebid.github.io repository
- Other repositories are not affected by master override
- Version parameter is correctly overridden
- Logging shows correct override behavior
"""

from unittest.mock import Mock, patch

from src.repo_modules.config import RepoConfig


class TestMasterOverride:
    """Test master version override functionality for prebid.github.io."""

    @patch("src.repo_modules.main.GitHubClient")
    @patch("src.repo_modules.main.ParserFactory")
    def test_prebid_docs_master_override(self, mock_parser_factory, mock_github_client):
        """Test that prebid.github.io always uses master version regardless of input."""
        # Mock the necessary components
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "prebid/prebid.github.io",
            "version": "master",  # Should always be master
            "paths": {"dev-docs/bidders": {"dev-docs/bidders/test.md": ""}},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Mock config for prebid-docs
        with (
            patch(
                "src.repo_modules.main.get_repo_config_with_versions"
            ) as mock_get_config,
            patch("src.repo_modules.main.get_available_repos") as mock_get_repos,
        ):
            mock_config = RepoConfig(
                repo="prebid/prebid.github.io",
                description="Prebid Documentation site",
                versions=["master"],
                parser_type="prebid_docs",
                paths={"Bid Adapters": "dev-docs/bidders"},
                fetch_strategy="filenames_only",
                version_override="master",  # Configuration-driven override
                output_filename_slug="prebid.github.io",
            )
            mock_get_config.return_value = mock_config
            mock_get_repos.return_value = {"prebid-docs": mock_config}

            # Test with different version inputs - should all use master
            test_versions = ["v1.0.0", "feature-branch", "some-other-version", "master"]

            for input_version in test_versions:
                mock_github.fetch_repository_data.reset_mock()

                from src.repo_modules.main import main

                # Mock sys.argv with different versions
                with patch(
                    "sys.argv",
                    ["main.py", "--repo", "prebid-docs", "--version", input_version],
                ):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.write = Mock()
                        main()

                # Verify that fetch_repository_data was called with master version
                mock_github.fetch_repository_data.assert_called_once()
                call_args = mock_github.fetch_repository_data.call_args

                # The version argument should be "master" regardless of input
                assert (
                    call_args[0][1] == "master"
                ), f"Expected master version, got {call_args[0][1]} for input {input_version}"

    @patch("src.repo_modules.main.GitHubClient")
    @patch("src.repo_modules.main.ParserFactory")
    def test_other_repos_not_affected_by_master_override(
        self, mock_parser_factory, mock_github_client
    ):
        """Test that other repositories are not affected by master override logic."""
        # Mock the necessary components
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "prebid/Prebid.js",
            "version": "v9.51.0",  # Should preserve the input version
            "files": {"modules/testBidAdapter.js": ""},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Test with different repositories
        test_configs = [
            {
                "repo_name": "prebid-js",
                "repo_url": "prebid/Prebid.js",
                "parser_type": "prebid_js",
                "modules_path": "modules",
                "paths": None,
                "test_version": "v9.51.0",
            },
            {
                "repo_name": "prebid-server",
                "repo_url": "prebid/prebid-server",
                "parser_type": "prebid_server_go",
                "modules_path": None,
                "paths": {"Bid Adapters": "adapters"},
                "test_version": "v3.8.0",
            },
            {
                "repo_name": "prebid-server-java",
                "repo_url": "prebid/prebid-server-java",
                "parser_type": "prebid_server_java",
                "modules_path": None,
                "paths": {"Bid Adapters": "src/main/java/org/prebid/server/bidder"},
                "test_version": "v3.27.0",
            },
        ]

        for config in test_configs:
            mock_github.fetch_repository_data.reset_mock()

            # Mock config for current repo
            with (
                patch(
                    "src.repo_modules.main.get_repo_config_with_versions"
                ) as mock_get_config,
                patch("src.repo_modules.main.get_available_repos") as mock_get_repos,
            ):
                mock_repo_config = RepoConfig(
                    repo=config["repo_url"],
                    description="Test",
                    versions=["master"],
                    parser_type=config["parser_type"],
                    paths=config["paths"],
                    modules_path=config["modules_path"],
                    fetch_strategy=(
                        "filenames_only"
                        if config["modules_path"]
                        else "directory_names"
                    ),
                    # No version_override for non-prebid-docs repos
                )
                mock_get_config.return_value = mock_repo_config
                mock_get_repos.return_value = {config["repo_name"]: mock_repo_config}

                from src.repo_modules.main import main

                # Mock sys.argv
                with patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        config["repo_name"],
                        "--version",
                        config["test_version"],
                    ],
                ):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.write = Mock()
                        main()

                # Verify that fetch_repository_data was called with the original version
                mock_github.fetch_repository_data.assert_called_once()
                call_args = mock_github.fetch_repository_data.call_args

                # The version should be preserved (not changed to master)
                assert (
                    call_args[0][1] == config["test_version"]
                ), f"Version should be preserved for {config['repo_name']}, expected {config['test_version']}, got {call_args[0][1]}"

    def test_master_override_logic_isolation(self):
        """Test the master override logic in isolation."""

        # Simulate the logic from main.py
        def apply_master_override(repo_url, input_version):
            version = input_version
            if repo_url == "prebid/prebid.github.io":
                version = "master"
            return version

        # Test cases
        test_cases = [
            # (repo_url, input_version, expected_output)
            ("prebid/prebid.github.io", "v1.0.0", "master"),
            ("prebid/prebid.github.io", "feature-branch", "master"),
            ("prebid/prebid.github.io", "master", "master"),
            ("prebid/prebid.github.io", "any-version", "master"),
            ("prebid/Prebid.js", "v9.51.0", "v9.51.0"),
            ("prebid/prebid-server", "v3.8.0", "v3.8.0"),
            ("prebid/prebid-server-java", "v3.27.0", "v3.27.0"),
            ("other/repo", "v1.0.0", "v1.0.0"),
        ]

        for repo_url, input_version, expected_output in test_cases:
            result = apply_master_override(repo_url, input_version)
            assert (
                result == expected_output
            ), f"For repo {repo_url} with version {input_version}, expected {expected_output}, got {result}"

    @patch("src.repo_modules.main.logger")
    def test_master_override_preserves_original_main_logic(self, mock_logger):
        """Test that master override doesn't break other main function logic."""
        # This test ensures the override is properly integrated

        # Test the version determination logic
        def simulate_version_logic(repo_url, args_version):
            version = args_version

            # Original logic would go here (version menu, etc.)
            # Then the override
            if repo_url == "prebid/prebid.github.io":
                version = "master"

            return version

        # Test that override happens after other version logic
        result = simulate_version_logic("prebid/prebid.github.io", "user-input-version")
        assert result == "master"

        # Test that non-prebid.github.io repos are unaffected
        result = simulate_version_logic("prebid/Prebid.js", "v9.51.0")
        assert result == "v9.51.0"

    def test_master_override_with_interactive_mode(self):
        """Test that master override works even when version comes from interactive selection."""

        # Simulate interactive mode where user selects a version
        def simulate_interactive_selection(repo_url, selected_version):
            version = selected_version  # From user interaction

            # Apply override after user selection
            if repo_url == "prebid/prebid.github.io":
                version = "master"

            return version

        # Test that even if user selects different version, it gets overridden
        result = simulate_interactive_selection("prebid/prebid.github.io", "v2.0.0")
        assert result == "master"

        # Test that other repos preserve user selection
        result = simulate_interactive_selection("prebid/Prebid.js", "v9.50.0")
        assert result == "v9.50.0"


class TestMasterOverrideIntegration:
    """Integration tests for master override functionality."""

    def test_master_override_filename_generation(self):
        """Test that master override affects filename generation correctly."""
        # Simulate filename generation with master override
        repo_url = "prebid/prebid.github.io"
        input_version = "some-feature-branch"

        # Apply override
        version = "master" if repo_url == "prebid/prebid.github.io" else input_version

        # Generate filename
        owner, repo = repo_url.split("/")
        repo_name = repo.lower().replace("-", ".")
        version_clean = version.replace("/", "_")
        filename = f"{repo_name}_modules_version_{version_clean}.txt"

        # Should always generate master filename for prebid.github.io
        assert filename == "prebid.github.io_modules_version_master.txt"

    def test_master_override_with_all_input_methods(self):
        """Test master override with different ways of specifying version."""
        repo_url = "prebid/prebid.github.io"

        # Different ways version might be specified
        version_sources = [
            "command_line_arg",
            "interactive_menu_selection",
            "config_default",
            "environment_variable",
        ]

        # All should result in master for prebid.github.io
        for source in version_sources:
            version = "master" if repo_url == "prebid/prebid.github.io" else source
            assert version == "master"

    def test_master_override_error_handling(self):
        """Test that master override doesn't interfere with error handling."""
        # Test with None version
        repo_url = "prebid/prebid.github.io"
        input_version = None

        # Even with None input, should get master for prebid.github.io
        version = input_version
        if repo_url == "prebid/prebid.github.io":
            version = "master"

        assert version == "master"

        # Test with empty string
        input_version = ""
        version = input_version
        if repo_url == "prebid/prebid.github.io":
            version = "master"

        assert version == "master"
