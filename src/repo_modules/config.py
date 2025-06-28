"""
Repository configuration system
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .github_client import GitHubClient

CONFIG_FILE = Path(__file__).parent / "repos.json"


@dataclass
class RepoConfig:
    """Configuration for a repository parser."""

    repo: str  # GitHub repo in format "owner/repo"
    description: str  # Human-readable description
    versions: list[str]  # Available versions/tags/branches
    parser_type: str = "default"  # Parser type identifier
    directory: str | None = (
        None  # Directory within repo to parse (for backward compatibility)
    )
    modules_path: str | None = None  # Optional path to modules directory for parsing
    paths: dict[str, str] | None = None  # Multiple paths for multi-directory parsing
    fetch_strategy: str = (
        "full_content"  # How to fetch data: "full_content", "filenames_only", "directory_names"
    )
    version_override: str | None = None  # Force specific version (e.g., "master")
    output_filename_slug: str | None = None  # Custom slug for auto-generated filenames


def _load_repos() -> dict[str, dict]:
    """Load repository configurations from JSON file."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_available_repos() -> dict[str, RepoConfig]:
    """Get dictionary of available preconfigured repositories."""
    repos_data = _load_repos()
    return {name: RepoConfig(**data) for name, data in repos_data.items()}


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
            description=config.description,
            versions=dynamic_versions,
            parser_type=config.parser_type,
            directory=config.directory,
            modules_path=config.modules_path,
            paths=config.paths,
            fetch_strategy=config.fetch_strategy,
            version_override=config.version_override,
            output_filename_slug=config.output_filename_slug,
        )
    except Exception:
        # Return original config with fallback versions if discovery fails
        return config


def add_repo_config(name: str, config: RepoConfig) -> None:
    """Add a new repository configuration and save to file."""
    repos = _load_repos()
    repos[name] = asdict(config)
    with open(CONFIG_FILE, "w") as f:
        json.dump(repos, f, indent=4)


def get_repo_config(name: str) -> RepoConfig:
    """Get configuration for a specific repository."""
    repos = get_available_repos()
    if name not in repos:
        raise ValueError(f"Repository '{name}' not found in available configurations")
    return repos[name]
