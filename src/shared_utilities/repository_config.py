"""Repository configuration management for shared use across tools."""

import json
from pathlib import Path
from typing import TypedDict

from .logging_config import get_logger

logger = get_logger(__name__)


class RepositoryConfig(TypedDict, total=False):
    """Type definition for repository configuration."""

    repo: str
    description: str
    versions: list[str]
    parser_type: str
    fetch_strategy: str
    version_override: str | None
    output_filename_slug: str | None
    paths: dict[str, str]


class RepositoryConfigManager:
    """Manages repository configurations for all tools."""

    def __init__(self, config_file: Path | None = None):
        """Initialize the repository configuration manager.

        Args:
            config_file: Path to the repository configuration file.
                        If None, looks for repos.json in standard locations.
        """
        self.config_file = config_file or self._find_config_file()
        self.configs: dict[str, RepositoryConfig] = {}
        self._load_configs()

    def _find_config_file(self) -> Path:
        """Find the repository configuration file in standard locations.

        Returns:
            Path to the configuration file.

        Raises:
            FileNotFoundError: If no configuration file is found.
        """
        # Try to find repos.json in multiple locations
        search_paths = [
            Path(__file__).parent.parent / "repo_modules" / "repos.json",
            # Legacy path no longer used
            Path.cwd() / "repos.json",
        ]

        for path in search_paths:
            if path.exists():
                logger.debug(f"Found repository config at: {path}")
                return path

        raise FileNotFoundError(
            "Could not find repos.json in any expected location. "
            f"Searched: {[str(p) for p in search_paths]}"
        )

    def _load_configs(self) -> None:
        """Load repository configurations from file."""
        try:
            with open(self.config_file) as f:
                self.configs = json.load(f)
            logger.info(f"Loaded {len(self.configs)} repository configurations")
        except Exception as e:
            logger.error(f"Failed to load repository configs: {e}")
            raise

    def get_config(self, repo_key: str) -> RepositoryConfig:
        """Get configuration for a specific repository.

        Args:
            repo_key: The repository key or full repo name (owner/repo).

        Returns:
            Repository configuration dictionary.

        Raises:
            KeyError: If the repository is not found.
        """
        # First try direct key lookup
        if repo_key in self.configs:
            return self.configs[repo_key]

        # Then try matching by repo field
        for _, config in self.configs.items():
            if config.get("repo") == repo_key:
                return config

        raise KeyError(f"Repository '{repo_key}' not found in configuration")

    def list_repositories(self) -> list[str]:
        """Get list of all configured repository keys.

        Returns:
            List of repository keys.
        """
        return list(self.configs.keys())

    def get_all_configs(self) -> dict[str, RepositoryConfig]:
        """Get all repository configurations.

        Returns:
            Dictionary of all repository configurations.
        """
        return self.configs.copy()

    def is_configured(self, repo_key: str) -> bool:
        """Check if a repository is configured.

        Args:
            repo_key: The repository key or full repo name.

        Returns:
            True if the repository is configured, False otherwise.
        """
        try:
            self.get_config(repo_key)
            return True
        except KeyError:
            return False

    def get_repo_full_name(self, repo_key: str) -> str:
        """Get the full repository name (owner/repo) for a key.

        Args:
            repo_key: The repository key.

        Returns:
            Full repository name in owner/repo format.

        Raises:
            KeyError: If the repository is not found.
        """
        config = self.get_config(repo_key)
        return config["repo"]

    def get_fetch_strategy(self, repo_key: str) -> str:
        """Get the fetch strategy for a repository.

        Args:
            repo_key: The repository key.

        Returns:
            Fetch strategy (e.g., 'full_content', 'filenames_only', 'directory_names').
        """
        config = self.get_config(repo_key)
        return config.get("fetch_strategy", "full_content")

    def get_parser_type(self, repo_key: str) -> str:
        """Get the parser type for a repository.

        Args:
            repo_key: The repository key.

        Returns:
            Parser type name.
        """
        config = self.get_config(repo_key)
        return config.get("parser_type", "default")

    def get_version_override(self, repo_key: str) -> str | None:
        """Get version override for a repository.

        Args:
            repo_key: The repository key.

        Returns:
            Version override if specified, None otherwise.
        """
        config = self.get_config(repo_key)
        return config.get("version_override")

    def get_output_slug(self, repo_key: str) -> str | None:
        """Get output filename slug for a repository.

        Args:
            repo_key: The repository key.

        Returns:
            Output filename slug if specified, None otherwise.
        """
        config = self.get_config(repo_key)
        return config.get("output_filename_slug")

    def get_paths(self, repo_key: str) -> dict[str, str]:
        """Get configured paths for a repository.

        Args:
            repo_key: The repository key.

        Returns:
            Dictionary of category names to paths.
        """
        config = self.get_config(repo_key)
        return config.get("paths", {})
