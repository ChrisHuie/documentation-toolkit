"""
Repository configuration system
"""

from dataclasses import dataclass

from .github_client import GitHubClient


@dataclass
class RepoConfig:
    """Configuration for a repository parser."""

    repo: str  # GitHub repo in format "owner/repo"
    directory: str  # Directory within repo to parse
    description: str  # Human-readable description
    versions: list[str]  # Available versions/tags/branches
    parser_type: str = "default"  # Parser type identifier


def get_available_repos() -> dict[str, RepoConfig]:
    """Get dictionary of available preconfigured repositories."""

    # Use static versions to avoid rate limiting during repo listing
    # Versions will be dynamically fetched when a specific repo is selected
    repos = {
        "prebid-js": RepoConfig(
            repo="prebid/Prebid.js",
            directory="modules",
            description="Prebid.js - Header bidding wrapper for publishers",
            versions=["master"],  # Will be dynamically updated when selected
            parser_type="default",
        ),
        "prebid-server-java": RepoConfig(
            repo="prebid/prebid-server-java",
            directory="src/main/java/org/prebid/server",
            description="Prebid Server Java implementation",
            versions=["master"],  # Will be dynamically updated when selected
            parser_type="default",
        ),
        "prebid-server": RepoConfig(
            repo="prebid/prebid-server",
            directory="adapters",
            description="Prebid Server Go implementation",
            versions=["master"],  # Will be dynamically updated when selected
            parser_type="default",
        ),
        "prebid-docs": RepoConfig(
            repo="prebid/prebid.github.io",
            directory="dev-docs",
            description="Prebid documentation site",
            versions=["master"],  # Special case - no semantic versioning
            parser_type="markdown",
        ),
    }

    return repos


def get_repo_config_with_versions(name: str) -> RepoConfig:
    """Get repository configuration with dynamically fetched versions."""
    repos = get_available_repos()
    if name not in repos:
        raise ValueError(f"Repository '{name}' not found in available configurations")

    config = repos[name]

    # Skip version discovery for docs repo
    if name == "prebid-docs":
        return config

    # Fetch dynamic versions for other repos
    try:
        client = GitHubClient()
        dynamic_versions = client.get_semantic_versions(config.repo)
        # Create new config with dynamic versions
        return RepoConfig(
            repo=config.repo,
            directory=config.directory,
            description=config.description,
            versions=dynamic_versions,
            parser_type=config.parser_type,
        )
    except Exception:
        # Return original config with fallback versions if discovery fails
        return config


def add_repo_config(name: str, config: RepoConfig) -> None:
    """Add a new repository configuration (runtime only)."""
    # This could be extended to persist configurations
    pass


def get_repo_config(name: str) -> RepoConfig:
    """Get configuration for a specific repository."""
    repos = get_available_repos()
    if name not in repos:
        raise ValueError(f"Repository '{name}' not found in available configurations")
    return repos[name]
