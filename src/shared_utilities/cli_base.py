"""
Shared CLI utilities for consistent command-line interfaces across all tools.

This module provides base classes and common argument definitions to ensure
consistency in CLI behavior, naming, and functionality across the toolkit.
"""

import argparse
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click

from . import get_logger

logger = get_logger(__name__)


class ArgumentDefinition:
    """Definition for a CLI argument with all its properties."""

    def __init__(
        self,
        flags: list[str],
        help: str,
        type: type | str | None = None,
        default: Any = None,
        required: bool = False,
        choices: list[str] | None = None,
        action: str | None = None,
        **kwargs: Any,
    ):
        """Initialize argument definition."""
        self.flags = flags
        self.help = help
        self.type = type
        self.default = default
        self.required = required
        self.choices = choices
        self.action = action
        self.extra_kwargs = kwargs


# Common arguments that should be available to all tools
COMMON_ARGUMENTS = {
    "output": ArgumentDefinition(
        flags=["-o", "--output"],
        help="Output file path (default: stdout for human-readable formats)",
        type="path",
    ),
    "format": ArgumentDefinition(
        flags=["-f", "--format"],
        choices=["table", "json", "csv", "markdown", "yaml", "html"],
        default="table",
        help="Output format",
    ),
    "quiet": ArgumentDefinition(
        flags=["-q", "--quiet"],
        action="store_true",
        help="Suppress progress output",
    ),
    "verbose": ArgumentDefinition(
        flags=["--verbose"],  # No short form to give -v to version
        action="store_true",
        help="Enable verbose logging",
    ),
}

# Repository-related arguments for tools that work with GitHub repos
REPOSITORY_ARGUMENTS = {
    "repo": ArgumentDefinition(
        flags=["-r", "--repo"],
        help="Repository (format: owner/repo or predefined key)",
        type=str,
    ),
    "version": ArgumentDefinition(
        flags=["-v", "--version"],
        help="Version/tag/branch to analyze",
        type=str,
    ),
    "list_repos": ArgumentDefinition(
        flags=["--list-repos"],
        action="store_true",
        help="List available repositories and exit",
    ),
}

# Rate limiting arguments for tools making API calls
RATE_LIMIT_ARGUMENTS = {
    "delay": ArgumentDefinition(
        flags=["--delay"],
        type=float,
        default=2.0,
        help="Delay between batches (seconds)",
    ),
    "batch_size": ArgumentDefinition(
        flags=["--batch-size"],
        type=int,
        default=20,
        help="Number of items per batch",
    ),
    "request_delay": ArgumentDefinition(
        flags=["--request-delay"],
        type=float,
        default=0.6,
        help="Delay between individual requests (seconds)",
    ),
}

# NOTE: FILTER_ARGUMENTS has been moved below with more comprehensive definitions

# Cache-related arguments
CACHE_ARGUMENTS = {
    "force_refresh": ArgumentDefinition(
        flags=["--force-refresh"],
        action="store_true",
        help="Force refresh even if cache exists",
    ),
    "clear_cache": ArgumentDefinition(
        flags=["--clear-cache"],
        action="store_true",
        help="Clear cache and exit",
    ),
    "cache_info": ArgumentDefinition(
        flags=["--cache-info"],
        action="store_true",
        help="Show cache information and exit",
    ),
}

# Authentication arguments
AUTH_ARGUMENTS = {
    "token": ArgumentDefinition(
        flags=["-t", "--token"],
        help="GitHub Personal Access Token (overrides GITHUB_TOKEN env var)",
        type=str,
    ),
}

# Display enhancement arguments
DISPLAY_ARGUMENTS = {
    "summary": ArgumentDefinition(
        flags=["-s", "--summary"],
        action="store_true",
        help="Show summary statistics",
    ),
    "show_json": ArgumentDefinition(
        flags=["--show-json"],
        action="store_true",
        help="Include JSON representation in output",
    ),
}

# Resumable operation arguments
RESUMABLE_ARGUMENTS = {
    "resume": ArgumentDefinition(
        flags=["--resume"],
        action="store_true",
        help="Resume from previous checkpoint if available",
    ),
    "start_from": ArgumentDefinition(
        flags=["--start-from"],
        type=int,
        default=0,
        help="Start processing from specific index",
    ),
}

# Directory/path arguments
PATH_ARGUMENTS = {
    "directory": ArgumentDefinition(
        flags=["-d", "--directory"],
        type=str,
        help="Directory path to process",
    ),
}

# Common filter arguments
FILTER_ARGUMENTS = {
    "limit": ArgumentDefinition(
        flags=["-l", "--limit"],
        type=int,
        help="Limit number of items to process",
    ),
    "type": ArgumentDefinition(
        flags=["-T", "--type"],
        type=str,
        help="Filter by type",
    ),
    "adapter": ArgumentDefinition(
        flags=["-a", "--adapter"],
        type=str,
        help="Filter by specific adapter",
    ),
    "mode": ArgumentDefinition(
        flags=["-m", "--mode"],
        type=str,
        help="Processing mode",
    ),
}


class BaseArgumentParser(ABC):
    """
    Abstract base class for creating consistent argument parsers.

    Subclasses should implement get_parser() and can use the add_arguments()
    helper to add common argument sets.
    """

    def __init__(self, description: str, tool_name: str):
        """Initialize base parser."""
        self.description = description
        self.tool_name = tool_name
        self._parser: argparse.ArgumentParser | None = None

    @abstractmethod
    def get_parser(self) -> argparse.ArgumentParser:
        """Return configured argument parser. Must be implemented by subclasses."""
        pass

    def add_arguments(
        self,
        parser: argparse.ArgumentParser,
        argument_sets: list[dict[str, ArgumentDefinition]],
        exclude: list[str] | None = None,
    ) -> None:
        """
        Add multiple argument sets to a parser.

        Args:
            parser: ArgumentParser instance
            argument_sets: List of argument dictionaries to add
            exclude: List of argument names to exclude
        """
        exclude = exclude or []

        for arg_set in argument_sets:
            for name, arg_def in arg_set.items():
                if name not in exclude:
                    self._add_argument(parser, arg_def)

    def _add_argument(
        self, parser: argparse.ArgumentParser, arg_def: ArgumentDefinition
    ) -> None:
        """Add a single argument to the parser."""
        kwargs: dict[str, Any] = {
            "help": arg_def.help,
        }

        if arg_def.type:
            if arg_def.type == "path":
                kwargs["type"] = Path
            else:
                kwargs["type"] = arg_def.type

        if arg_def.default is not None:
            kwargs["default"] = arg_def.default

        if arg_def.required:
            kwargs["required"] = arg_def.required

        if arg_def.choices:
            kwargs["choices"] = arg_def.choices

        if arg_def.action:
            kwargs["action"] = arg_def.action

        # Add any extra kwargs
        kwargs.update(arg_def.extra_kwargs)

        parser.add_argument(*arg_def.flags, **kwargs)

    def parse_args(self, args: list[str] | None = None) -> argparse.Namespace:
        """Parse command line arguments."""
        parser = self.get_parser()
        parsed_args = parser.parse_args(args)

        # Handle common behaviors
        if hasattr(parsed_args, "verbose") and parsed_args.verbose:
            # Reconfigure logging for verbose mode
            from .logging_config import configure_logging

            configure_logging(level="DEBUG")

        return parsed_args


class ClickCommand:
    """
    Base class for creating consistent Click commands.

    Provides helper methods to add common option sets to Click commands.
    """

    @staticmethod
    def add_common_options(exclude: list[str] | None = None):
        """Decorator that adds common options to a Click command."""
        exclude = exclude or []

        def decorator(func):
            # Add options in reverse order since decorators are applied bottom-up
            if "verbose" not in exclude:
                func = click.option(
                    "-v", "--verbose", is_flag=True, help="Enable verbose logging"
                )(func)

            if "quiet" not in exclude:
                func = click.option(
                    "-q", "--quiet", is_flag=True, help="Suppress progress output"
                )(func)

            if "format" not in exclude:
                func = click.option(
                    "-f",
                    "--format",
                    "output_format",
                    type=click.Choice(
                        ["table", "json", "csv", "markdown", "yaml", "html"]
                    ),
                    default="table",
                    help="Output format",
                    show_default=True,
                )(func)

            if "output" not in exclude:
                func = click.option(
                    "-o",
                    "--output",
                    "output_file",
                    type=click.Path(),
                    help="Output file path (default: stdout)",
                )(func)

            return func

        return decorator

    @staticmethod
    def add_repository_options(exclude: list[str] | None = None):
        """Decorator that adds repository-related options."""
        exclude = exclude or []

        def decorator(func):
            if "list_repos" not in exclude:
                func = click.option(
                    "--list-repos",
                    is_flag=True,
                    help="List available repositories and exit",
                )(func)

            if "version" not in exclude:
                func = click.option(
                    "--version",
                    help="Version/tag/branch to analyze",
                )(func)

            if "repo" not in exclude:
                func = click.option(
                    "--repo",
                    help="Repository (format: owner/repo or predefined key)",
                )(func)

            return func

        return decorator

    @staticmethod
    def add_rate_limit_options(exclude: list[str] | None = None):
        """Decorator that adds rate limiting options."""
        exclude = exclude or []

        def decorator(func):
            if "request_delay" not in exclude:
                func = click.option(
                    "--request-delay",
                    type=float,
                    default=0.6,
                    help="Delay between individual requests (seconds)",
                    show_default=True,
                )(func)

            if "batch_size" not in exclude:
                func = click.option(
                    "--batch-size",
                    type=int,
                    default=20,
                    help="Number of items per batch",
                    show_default=True,
                )(func)

            if "delay" not in exclude:
                func = click.option(
                    "--delay",
                    type=float,
                    default=2.0,
                    help="Delay between batches (seconds)",
                    show_default=True,
                )(func)

            return func

        return decorator


def create_standard_parser(
    description: str,
    tool_name: str,
    include_sets: list[str] | None = None,
    exclude_args: list[str] | None = None,
) -> argparse.ArgumentParser:
    """
    Convenience function to create a standard argument parser with common options.

    Args:
        description: Tool description
        tool_name: Name of the tool
        include_sets: List of argument set names to include
                     ("common", "repository", "rate_limit", "filter", "cache",
                      "auth", "display", "resumable", "path")
        exclude_args: List of specific argument names to exclude

    Returns:
        Configured ArgumentParser
    """
    include_sets = include_sets or ["common"]
    exclude_args = exclude_args or []

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Map set names to argument dictionaries
    available_sets = {
        "common": COMMON_ARGUMENTS,
        "repository": REPOSITORY_ARGUMENTS,
        "rate_limit": RATE_LIMIT_ARGUMENTS,
        "filter": FILTER_ARGUMENTS,
        "cache": CACHE_ARGUMENTS,
        "auth": AUTH_ARGUMENTS,
        "display": DISPLAY_ARGUMENTS,
        "resumable": RESUMABLE_ARGUMENTS,
        "path": PATH_ARGUMENTS,
    }

    # Add requested argument sets
    for set_name in include_sets:
        if set_name in available_sets:
            arg_set = available_sets[set_name]
            for name, arg_def in arg_set.items():
                if name not in exclude_args:
                    _add_argument_to_parser(parser, arg_def)

    return parser


def _add_argument_to_parser(
    parser: argparse.ArgumentParser, arg_def: ArgumentDefinition
) -> None:
    """Helper to add argument definition to parser."""
    kwargs: dict[str, Any] = {"help": arg_def.help}

    if arg_def.type:
        if arg_def.type == "path":
            kwargs["type"] = Path
        else:
            kwargs["type"] = arg_def.type

    if arg_def.default is not None:
        kwargs["default"] = arg_def.default

    if arg_def.required:
        kwargs["required"] = arg_def.required

    if arg_def.choices:
        kwargs["choices"] = arg_def.choices

    if arg_def.action:
        kwargs["action"] = arg_def.action

    kwargs.update(arg_def.extra_kwargs)

    parser.add_argument(*arg_def.flags, **kwargs)
