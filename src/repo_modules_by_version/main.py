#!/usr/bin/env python3
"""
Documentation tools CLI - Extract data from GitHub repositories
"""

import argparse
import sys

from dotenv import load_dotenv
from loguru import logger

from .config import RepoConfig, get_available_repos, get_repo_config_with_versions
from .github_client import GitHubClient
from .parser_factory import ParserFactory

# Initialize environment and logging
load_dotenv()
logger.remove()  # Remove default handler
logger.add(
    sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} [{level}] {message}", level="INFO"
)


def generate_output_filename(config: RepoConfig, version: str) -> str:
    """
    Generate output filename based on repository configuration.

    Args:
        config: Repository configuration containing output_filename_slug
        version: Version string to include in filename

    Returns:
        Generated filename string
    """
    # Use custom slug if provided, otherwise generate from repo name
    if config.output_filename_slug:
        repo_name = config.output_filename_slug
    else:
        # Extract repo name and convert dashes to dots
        owner, repo = config.repo.split("/")
        repo_name = repo.lower().replace("-", ".")

    # Clean version string for filename
    version_clean = version.replace("/", "_")

    return f"{repo_name}_modules_version_{version_clean}.txt"


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract data from GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--repo",
        type=str,
        help="GitHub repository (format: owner/repo). If not specified, shows available repos menu.",
    )

    parser.add_argument(
        "--version",
        type=str,
        help="Repository version/tag/branch to analyze. If not specified, shows available versions.",
    )

    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="List all available preconfigured repositories",
    )

    parser.add_argument(
        "--output", type=str, help="Output file path (optional, defaults to stdout)"
    )

    return parser


def show_repo_menu() -> str | None:
    """Display available repositories and get user selection."""
    repos = get_available_repos()

    if not repos:
        print("No preconfigured repositories available.")
        return None

    print("\nAvailable repositories:")
    print("-" * 40)

    for i, (repo_name, config) in enumerate(repos.items(), 1):
        print(f"{i}. {repo_name}")
        print(f"   Repository: {config.repo}")
        print(f"   Description: {config.description}")
        print(f"   Available versions: {', '.join(config.versions)}")
        print()

    while True:
        try:
            choice = input("Select a repository (number) or 'q' to quit: ").strip()
            if choice.lower() == "q":
                return None

            choice_num = int(choice)
            if 1 <= choice_num <= len(repos):
                repo_names = list(repos.keys())
                return repo_names[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(repos)}")
        except (ValueError, KeyboardInterrupt):
            print("\nExiting...")
            return None


def show_version_menu(repo_config: RepoConfig) -> str | None:
    """Display available versions for a repository and get user selection."""
    if not repo_config.versions:
        print("No versions configured for this repository.")
        return None

    print(f"\nAvailable versions for {repo_config.repo}:")
    print("-" * 40)

    for i, version in enumerate(repo_config.versions, 1):
        print(f"{i}. {version}")

    while True:
        try:
            choice = input("Select a version (number) or 'q' to quit: ").strip()
            if choice.lower() == "q":
                return None

            choice_num = int(choice)
            if 1 <= choice_num <= len(repo_config.versions):
                return repo_config.versions[choice_num - 1]
            else:
                print(
                    f"Please enter a number between 1 and {len(repo_config.versions)}"
                )
        except (ValueError, KeyboardInterrupt):
            print("\nExiting...")
            return None


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle list repos command
    if args.list_repos:
        repos = get_available_repos()
        if repos:
            logger.info("Available repositories:")
            for name, config in repos.items():
                logger.info(f"- {name}: {config.repo}")
        else:
            logger.error("No preconfigured repositories available.")
        sys.exit(0)

    # Determine repository
    repo_name = None
    repo_config = None

    if args.repo:
        # Check if it's a preconfigured repo
        repos = get_available_repos()
        if args.repo in repos:
            repo_name = args.repo
            repo_config = get_repo_config_with_versions(args.repo)
        else:
            # Treat as custom GitHub repo
            repo_config = RepoConfig(
                repo=args.repo,
                directory="",  # Will need to be specified later
                description="Custom repository",
                versions=[],
            )
    else:
        # Show menu for preconfigured repos
        repo_name = show_repo_menu()
        if not repo_name:
            sys.exit(0)

        # Get repo config with dynamic versions
        repo_config = get_repo_config_with_versions(repo_name)

    # Determine version
    version = args.version
    if not version:
        if repo_config.versions:
            version = show_version_menu(repo_config)
            if not version:
                sys.exit(0)
        else:
            logger.error(
                "No version specified and no preconfigured versions available."
            )
            logger.error("Please specify a version using --version")
            sys.exit(1)

    # Apply version override if configured
    if repo_config.version_override:
        version = repo_config.version_override

    # Initialize GitHub client and parser
    try:
        github_client = GitHubClient()
        parser_factory = ParserFactory()

        logger.info("Analyzing %s at version %s...", repo_config.repo, version)

        # Get parser for this repository
        parser_instance = parser_factory.get_parser(repo_config)

        # Fetch and parse repository data
        data = github_client.fetch_repository_data(
            repo_config.repo,
            version,
            repo_config.directory,
            repo_config.modules_path,
            repo_config.paths,
            repo_config.fetch_strategy,
        )
        result = parser_instance.parse(data)

        # Output result
        if args.output:
            output_file = args.output
        elif repo_config.modules_path or repo_config.paths:
            # Auto-generate filename using configuration-driven helper
            output_file = generate_output_filename(repo_config, version)
        else:
            output_file = None

        if output_file:
            # Check if file already exists and replace it
            import os

            if os.path.exists(output_file):
                logger.info("Replacing existing file: %s", output_file)

            with open(output_file, "w") as f:
                f.write(result)
            logger.info("Results written to %s", output_file)
        else:
            logger.info("Results:")
            logger.info("%s", "-" * 40)
            logger.info("%s", result)

    except Exception as e:
        logger.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
