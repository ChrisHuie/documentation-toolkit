"""
Tests for the main CLI module.
"""

from unittest.mock import Mock, patch

import pytest

from src.repo_modules_by_version.config import RepoConfig
from src.repo_modules_by_version.main import (
    create_parser,
    main,
    show_repo_menu,
    show_version_menu,
)


class TestCreateParser:
    """Test argument parser creation."""

    def test_create_parser_returns_parser(self):
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert parser is not None
        assert hasattr(parser, "parse_args")

    def test_parser_accepts_repo_argument(self):
        """Test parser accepts --repo argument."""
        parser = create_parser()
        args = parser.parse_args(["--repo", "owner/repo"])
        assert args.repo == "owner/repo"

    def test_parser_accepts_version_argument(self):
        """Test parser accepts --version argument."""
        parser = create_parser()
        args = parser.parse_args(["--version", "v1.0.0"])
        assert args.version == "v1.0.0"

    def test_parser_accepts_list_repos_flag(self):
        """Test parser accepts --list-repos flag."""
        parser = create_parser()
        args = parser.parse_args(["--list-repos"])
        assert args.list_repos is True

    def test_parser_accepts_output_argument(self):
        """Test parser accepts --output argument."""
        parser = create_parser()
        args = parser.parse_args(["--output", "output.txt"])
        assert args.output == "output.txt"

    def test_parser_defaults(self):
        """Test parser defaults when no arguments provided."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.repo is None
        assert args.version is None
        assert args.list_repos is False
        assert args.output is None


class TestShowRepoMenu:
    """Test repository menu functionality."""

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("builtins.input")
    def test_show_repo_menu_valid_selection(self, mock_input, mock_get_repos):
        """Test valid repository selection."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
            )
        }
        mock_input.return_value = "1"

        result = show_repo_menu()
        assert result == "test-repo"

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("builtins.input")
    def test_show_repo_menu_quit(self, mock_input, mock_get_repos):
        """Test quitting from repository menu."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
            )
        }
        mock_input.return_value = "q"

        result = show_repo_menu()
        assert result is None

    @patch("src.repo_modules_by_version.main.get_available_repos")
    def test_show_repo_menu_no_repos(self, mock_get_repos):
        """Test menu when no repositories are available."""
        mock_get_repos.return_value = {}

        result = show_repo_menu()
        assert result is None

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("builtins.input")
    def test_show_repo_menu_invalid_then_valid(self, mock_input, mock_get_repos):
        """Test invalid selection followed by valid selection."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
            )
        }
        # Mock more realistic invalid attempts before success
        mock_input.side_effect = ["0", "2", "1"]

        result = show_repo_menu()
        assert result == "test-repo"

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("builtins.input")
    def test_show_repo_menu_keyboard_interrupt(self, mock_input, mock_get_repos):
        """Test handling of keyboard interrupt."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
            )
        }
        mock_input.side_effect = KeyboardInterrupt()

        result = show_repo_menu()
        assert result is None


class TestShowVersionMenu:
    """Test version menu functionality."""

    @patch("builtins.input")
    def test_show_version_menu_valid_selection(self, mock_input):
        """Test valid version selection."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=["v1.0.0", "v2.0.0", "main"],
        )
        mock_input.return_value = "2"

        result = show_version_menu(config)
        assert result == "v2.0.0"

    @patch("builtins.input")
    def test_show_version_menu_quit(self, mock_input):
        """Test quitting from version menu."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=["v1.0.0"],
        )
        mock_input.return_value = "q"

        result = show_version_menu(config)
        assert result is None

    def test_show_version_menu_no_versions(self):
        """Test menu when no versions are available."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=[],
        )

        result = show_version_menu(config)
        assert result is None

    @patch("builtins.input")
    def test_show_version_menu_invalid_then_valid(self, mock_input):
        """Test invalid selection followed by valid selection."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=["v1.0.0"],
        )
        # Mock more realistic invalid attempts before success
        mock_input.side_effect = ["0", "2", "1"]

        result = show_version_menu(config)
        assert result == "v1.0.0"


class TestMainFunction:
    """Test main CLI function."""

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("sys.argv", ["main.py", "--list-repos"])
    def test_main_list_repos_with_repos(self, mock_get_repos):
        """Test main function with --list-repos when repos exist."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
            )
        }

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("sys.argv", ["main.py", "--list-repos"])
    def test_main_list_repos_no_repos(self, mock_get_repos):
        """Test main function with --list-repos when no repos exist."""
        mock_get_repos.return_value = {}

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("sys.argv", ["main.py", "--repo", "test-repo", "--version", "v1.0.0"])
    def test_main_with_preconfigured_repo(self, mock_get_repos, mock_github_client):
        """Test main function with preconfigured repository."""
        mock_get_repos.return_value = {
            "test-repo": RepoConfig(
                repo="test/repo",
                directory="docs",
                description="Test repository",
                versions=["v1.0.0"],
                parser_type="default",
            )
        }

        mock_client_instance = Mock()
        mock_client_instance.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {"README.md": "# Test"},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }
        mock_github_client.return_value = mock_client_instance

        # Mock parser
        with patch(
            "src.repo_modules_by_version.main.ParserFactory"
        ) as mock_parser_factory:
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = "Parsed output"
            mock_factory_instance = Mock()
            mock_factory_instance.get_parser.return_value = mock_parser_instance
            mock_parser_factory.return_value = mock_factory_instance

            main()

            mock_client_instance.fetch_repository_data.assert_called_once_with(
                "test/repo", "v1.0.0", "docs"
            )

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("src.repo_modules_by_version.main.get_available_repos")
    @patch("sys.argv", ["main.py", "--repo", "custom/repo", "--version", "v1.0.0"])
    def test_main_with_custom_repo(self, mock_get_repos, mock_github_client):
        """Test main function with custom repository not in config."""
        mock_get_repos.return_value = {}

        mock_client_instance = Mock()
        mock_client_instance.fetch_repository_data.return_value = {
            "repo": "custom/repo",
            "version": "v1.0.0",
            "directory": "",
            "files": {"README.md": "# Custom"},
            "metadata": {"commit_sha": "xyz789", "total_files": 1},
        }
        mock_github_client.return_value = mock_client_instance

        with patch(
            "src.repo_modules_by_version.main.ParserFactory"
        ) as mock_parser_factory:
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = "Custom parsed output"
            mock_factory_instance = Mock()
            mock_factory_instance.get_parser.return_value = mock_parser_instance
            mock_parser_factory.return_value = mock_factory_instance

            main()

            mock_client_instance.fetch_repository_data.assert_called_once_with(
                "custom/repo", "v1.0.0", ""
            )

    @patch("src.repo_modules_by_version.main.show_repo_menu")
    @patch("sys.argv", ["main.py"])
    def test_main_interactive_repo_selection_quit(self, mock_show_repo_menu):
        """Test main function when user quits repo selection."""
        mock_show_repo_menu.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("sys.argv", ["main.py", "--repo", "test/repo"])
    def test_main_missing_version_no_preconfigured(self, mock_github_client):
        """Test main function when version is missing and no preconfigured versions."""
        with patch(
            "src.repo_modules_by_version.main.get_available_repos"
        ) as mock_get_repos:
            mock_get_repos.return_value = {}

            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("builtins.open", create=True)
    @patch(
        "sys.argv",
        [
            "main.py",
            "--repo",
            "test/repo",
            "--version",
            "v1.0.0",
            "--output",
            "output.txt",
        ],
    )
    def test_main_with_output_file(self, mock_open, mock_github_client):
        """Test main function with output file."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_client_instance = Mock()
        mock_client_instance.fetch_repository_data.return_value = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "",
            "files": {"README.md": "# Test"},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }
        mock_github_client.return_value = mock_client_instance

        with patch(
            "src.repo_modules_by_version.main.ParserFactory"
        ) as mock_parser_factory:
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = "Output content"
            mock_factory_instance = Mock()
            mock_factory_instance.get_parser.return_value = mock_parser_instance
            mock_parser_factory.return_value = mock_factory_instance

            with patch(
                "src.repo_modules_by_version.main.get_available_repos"
            ) as mock_get_repos:
                mock_get_repos.return_value = {}

                main()

                mock_file.write.assert_called_once_with("Output content")

    @patch("src.repo_modules_by_version.main.GitHubClient")
    @patch("sys.argv", ["main.py", "--repo", "test/repo", "--version", "v1.0.0"])
    def test_main_handles_exceptions(self, mock_github_client):
        """Test main function handles exceptions gracefully."""
        mock_github_client.side_effect = Exception("Test error")

        with patch(
            "src.repo_modules_by_version.main.get_available_repos"
        ) as mock_get_repos:
            mock_get_repos.return_value = {}

            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
