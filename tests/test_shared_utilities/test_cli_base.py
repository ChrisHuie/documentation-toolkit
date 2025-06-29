"""
Tests for the shared CLI base utilities.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared_utilities.cli_base import (
    AUTH_ARGUMENTS,
    CACHE_ARGUMENTS,
    COMMON_ARGUMENTS,
    DISPLAY_ARGUMENTS,
    FILTER_ARGUMENTS,
    PATH_ARGUMENTS,
    RATE_LIMIT_ARGUMENTS,
    REPOSITORY_ARGUMENTS,
    RESUMABLE_ARGUMENTS,
    ArgumentDefinition,
    BaseArgumentParser,
    ClickCommand,
    create_standard_parser,
)


class TestArgumentDefinition:
    """Test the ArgumentDefinition class."""

    def test_basic_definition(self):
        """Test creating a basic argument definition."""
        arg_def = ArgumentDefinition(
            flags=["--test"],
            help="Test argument",
            type=str,
            default="default",
        )

        assert arg_def.flags == ["--test"]
        assert arg_def.help == "Test argument"
        assert arg_def.type is str
        assert arg_def.default == "default"
        assert arg_def.required is False
        assert arg_def.choices is None
        assert arg_def.action is None

    def test_complete_definition(self):
        """Test creating a complete argument definition."""
        arg_def = ArgumentDefinition(
            flags=["-t", "--test"],
            help="Test argument",
            type=int,
            default=5,
            required=True,
            choices=[1, 2, 3, 4, 5],
            action="store",
            custom_attr="custom_value",
        )

        assert arg_def.flags == ["-t", "--test"]
        assert arg_def.required is True
        assert arg_def.choices == [1, 2, 3, 4, 5]
        assert arg_def.extra_kwargs == {"custom_attr": "custom_value"}


class TestCommonArguments:
    """Test the predefined common arguments."""

    def test_output_argument(self):
        """Test output argument definition."""
        output_arg = COMMON_ARGUMENTS["output"]
        assert "-o" in output_arg.flags
        assert "--output" in output_arg.flags
        assert output_arg.type == "path"
        assert "output file path" in output_arg.help.lower()

    def test_format_argument(self):
        """Test format argument definition."""
        format_arg = COMMON_ARGUMENTS["format"]
        assert "-f" in format_arg.flags
        assert "--format" in format_arg.flags
        assert "table" in format_arg.choices
        assert "json" in format_arg.choices
        assert "csv" in format_arg.choices
        assert format_arg.default == "table"

    def test_quiet_verbose_arguments(self):
        """Test quiet and verbose argument definitions."""
        quiet_arg = COMMON_ARGUMENTS["quiet"]
        verbose_arg = COMMON_ARGUMENTS["verbose"]

        assert "-q" in quiet_arg.flags
        assert "--quiet" in quiet_arg.flags
        assert quiet_arg.action == "store_true"

        # Verbose no longer has short form since -v is for version
        assert "--verbose" in verbose_arg.flags
        assert "-v" not in verbose_arg.flags
        assert verbose_arg.action == "store_true"


class TestRepositoryArguments:
    """Test repository-related arguments."""

    def test_repo_arguments(self):
        """Test repository argument definitions."""
        repo_arg = REPOSITORY_ARGUMENTS["repo"]
        version_arg = REPOSITORY_ARGUMENTS["version"]
        list_arg = REPOSITORY_ARGUMENTS["list_repos"]

        assert "-r" in repo_arg.flags
        assert "--repo" in repo_arg.flags
        assert repo_arg.type is str

        assert "-v" in version_arg.flags
        assert "--version" in version_arg.flags
        assert version_arg.type is str

        assert "--list-repos" in list_arg.flags
        assert list_arg.action == "store_true"


class TestRateLimitArguments:
    """Test rate limiting arguments."""

    def test_rate_limit_defaults(self):
        """Test rate limit argument defaults."""
        delay_arg = RATE_LIMIT_ARGUMENTS["delay"]
        batch_arg = RATE_LIMIT_ARGUMENTS["batch_size"]
        request_arg = RATE_LIMIT_ARGUMENTS["request_delay"]

        assert delay_arg.default == 2.0
        assert delay_arg.type is float

        assert batch_arg.default == 20
        assert batch_arg.type is int

        assert request_arg.default == 0.6
        assert request_arg.type is float


class ConcreteArgumentParser(BaseArgumentParser):
    """Concrete implementation for testing."""

    def get_parser(self) -> argparse.ArgumentParser:
        """Return a basic parser."""
        parser = argparse.ArgumentParser(description=self.description)
        self.add_arguments(parser, [COMMON_ARGUMENTS])
        return parser


class TestBaseArgumentParser:
    """Test the BaseArgumentParser class."""

    def test_initialization(self):
        """Test parser initialization."""
        parser = ConcreteArgumentParser("Test tool", "test-tool")
        assert parser.description == "Test tool"
        assert parser.tool_name == "test-tool"

    def test_add_arguments(self):
        """Test adding arguments to parser."""
        base_parser = ConcreteArgumentParser("Test tool", "test-tool")
        parser = base_parser.get_parser()

        # Check that common arguments were added
        args = parser.parse_args(["--output", "test.txt", "--format", "json"])
        assert args.output == Path("test.txt")
        assert args.format == "json"

    def test_exclude_arguments(self):
        """Test excluding specific arguments."""
        base_parser = ConcreteArgumentParser("Test tool", "test-tool")
        parser = argparse.ArgumentParser()

        base_parser.add_arguments(
            parser, [COMMON_ARGUMENTS], exclude=["format", "verbose"]
        )

        # Output and quiet should be added
        args = parser.parse_args(["--output", "test.txt", "--quiet"])
        assert args.output == Path("test.txt")
        assert args.quiet is True

        # Format should not be available
        with pytest.raises(SystemExit):
            parser.parse_args(["--format", "json"])

    def test_path_type_conversion(self):
        """Test that path type is converted to Path object."""
        base_parser = ConcreteArgumentParser("Test tool", "test-tool")
        parser = base_parser.get_parser()

        args = parser.parse_args(["--output", "/tmp/test.txt"])
        assert isinstance(args.output, Path)
        assert str(args.output) == "/tmp/test.txt"

    @patch("src.shared_utilities.logging_config.configure_logging")
    def test_verbose_mode(self, mock_configure_logging):
        """Test that verbose mode reconfigures logging."""
        base_parser = ConcreteArgumentParser("Test tool", "test-tool")

        # Parse with verbose flag
        base_parser.parse_args(["--verbose"])

        # Should have called configure_logging with DEBUG level
        mock_configure_logging.assert_called_once_with(level="DEBUG")


class TestCreateStandardParser:
    """Test the create_standard_parser convenience function."""

    def test_basic_parser(self):
        """Test creating a basic parser with common arguments."""
        parser = create_standard_parser(
            "Test tool", "test-tool", include_sets=["common"]
        )

        # Should have common arguments
        args = parser.parse_args(["-o", "output.txt", "-f", "csv"])
        assert args.output == Path("output.txt")
        assert args.format == "csv"

    def test_multiple_argument_sets(self):
        """Test including multiple argument sets."""
        parser = create_standard_parser(
            "Test tool", "test-tool", include_sets=["common", "repository", "filter"]
        )

        # Should have arguments from all sets
        args = parser.parse_args(
            [
                "--output",
                "out.txt",
                "--repo",
                "owner/repo",
                "--version",
                "v1.0.0",
                "--limit",
                "10",
            ]
        )

        assert args.output == Path("out.txt")
        assert args.repo == "owner/repo"
        assert args.version == "v1.0.0"
        assert args.limit == 10

    def test_exclude_specific_args(self):
        """Test excluding specific arguments."""
        parser = create_standard_parser(
            "Test tool",
            "test-tool",
            include_sets=["common", "repository"],
            exclude_args=["verbose", "repo"],
        )

        # Should have output but not verbose
        args = parser.parse_args(["--output", "test.txt"])
        assert args.output == Path("test.txt")

        # Should not have verbose or repo
        with pytest.raises(SystemExit):
            parser.parse_args(["--verbose"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--repo", "test/repo"])

    def test_invalid_set_name(self):
        """Test that invalid set names are ignored."""
        parser = create_standard_parser(
            "Test tool", "test-tool", include_sets=["common", "invalid_set"]
        )

        # Should still work with valid set
        args = parser.parse_args(["--output", "test.txt"])
        assert args.output == Path("test.txt")


class TestClickCommand:
    """Test the ClickCommand utilities."""

    def test_common_options_decorator(self):
        """Test adding common options via decorator."""
        import click

        @click.command()
        @ClickCommand.add_common_options()
        def test_command(output_file, output_format, quiet, verbose):
            return {
                "output": output_file,
                "format": output_format,
                "quiet": quiet,
                "verbose": verbose,
            }

        # Test the command has the expected options
        assert any(opt.name == "output_file" for opt in test_command.params)
        assert any(opt.name == "output_format" for opt in test_command.params)
        assert any(opt.name == "quiet" for opt in test_command.params)
        assert any(opt.name == "verbose" for opt in test_command.params)

    def test_repository_options_decorator(self):
        """Test adding repository options via decorator."""
        import click

        @click.command()
        @ClickCommand.add_repository_options()
        def test_command(repo, version, list_repos):
            return {
                "repo": repo,
                "version": version,
                "list_repos": list_repos,
            }

        # Test the command has the expected options
        assert any(opt.name == "repo" for opt in test_command.params)
        assert any(opt.name == "version" for opt in test_command.params)
        assert any(opt.name == "list_repos" for opt in test_command.params)

    def test_exclude_options(self):
        """Test excluding specific options."""
        import click

        @click.command()
        @ClickCommand.add_common_options(exclude=["format", "verbose"])
        def test_command(**kwargs):
            return kwargs

        # Should have output and quiet but not format or verbose
        param_names = [opt.name for opt in test_command.params]
        assert "output_file" in param_names
        assert "quiet" in param_names
        assert "output_format" not in param_names
        assert "verbose" not in param_names


class TestAuthArguments:
    """Test authentication arguments."""

    def test_token_argument(self):
        """Test token argument has short form."""
        token_arg = AUTH_ARGUMENTS["token"]
        assert "-t" in token_arg.flags
        assert "--token" in token_arg.flags
        assert token_arg.type is str


class TestDisplayArguments:
    """Test display enhancement arguments."""

    def test_summary_argument(self):
        """Test summary argument has short form."""
        summary_arg = DISPLAY_ARGUMENTS["summary"]
        assert "-s" in summary_arg.flags
        assert "--summary" in summary_arg.flags
        assert summary_arg.action == "store_true"

    def test_show_json_argument(self):
        """Test show-json argument."""
        show_json_arg = DISPLAY_ARGUMENTS["show_json"]
        assert "--show-json" in show_json_arg.flags
        assert show_json_arg.action == "store_true"


class TestFilterArguments:
    """Test filter arguments."""

    def test_limit_has_short_form(self):
        """Test limit argument now has short form."""
        limit_arg = FILTER_ARGUMENTS["limit"]
        assert "-l" in limit_arg.flags
        assert "--limit" in limit_arg.flags
        assert limit_arg.type is int

    def test_filter_arguments(self):
        """Test various filter arguments."""
        type_arg = FILTER_ARGUMENTS["type"]
        assert "-T" in type_arg.flags
        assert "--type" in type_arg.flags

        adapter_arg = FILTER_ARGUMENTS["adapter"]
        assert "-a" in adapter_arg.flags
        assert "--adapter" in adapter_arg.flags

        mode_arg = FILTER_ARGUMENTS["mode"]
        assert "-m" in mode_arg.flags
        assert "--mode" in mode_arg.flags


class TestPathArguments:
    """Test path-related arguments."""

    def test_directory_argument(self):
        """Test directory argument has short form."""
        dir_arg = PATH_ARGUMENTS["directory"]
        assert "-d" in dir_arg.flags
        assert "--directory" in dir_arg.flags
        assert dir_arg.type is str


class TestArgumentSets:
    """Test that all argument sets are properly defined."""

    def test_all_arguments_have_required_fields(self):
        """Test that all arguments have required fields."""
        all_arg_sets = [
            COMMON_ARGUMENTS,
            REPOSITORY_ARGUMENTS,
            RATE_LIMIT_ARGUMENTS,
            FILTER_ARGUMENTS,
            CACHE_ARGUMENTS,
            AUTH_ARGUMENTS,
            DISPLAY_ARGUMENTS,
            RESUMABLE_ARGUMENTS,
            PATH_ARGUMENTS,
        ]

        for arg_set in all_arg_sets:
            for _name, arg_def in arg_set.items():
                assert isinstance(arg_def, ArgumentDefinition)
                assert len(arg_def.flags) > 0
                assert arg_def.help is not None
                assert len(arg_def.help) > 0
