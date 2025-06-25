"""
Repository configuration system
"""

from dataclasses import dataclass


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

    # Example configurations - you can add your specific repos here
    repos = {
        "example-docs": RepoConfig(
            repo="owner/example-docs",
            directory="docs",
            description="Example documentation repository",
            versions=["v1.0.0", "v1.1.0", "main"],
            parser_type="markdown",
        ),
        "api-specs": RepoConfig(
            repo="owner/api-specs",
            directory="openapi",
            description="API specification files",
            versions=["v2.0", "v3.0", "latest"],
            parser_type="openapi",
        ),
    }

    return repos


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
