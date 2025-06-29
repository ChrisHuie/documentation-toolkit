"""
Configuration system for module history analysis.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from ..shared_utilities import get_logger


@dataclass
class HistoryConfig:
    """Configuration for module history analysis."""

    repo_name: str
    parser_type: str = "default"
    fetch_strategy: str = "filenames_only"
    module_patterns: dict[str, str] | None = None
    version_override: str | None = None
    description: str = ""

    def __post_init__(self):
        """Set default module patterns if not provided."""
        if self.module_patterns is None:
            self.module_patterns = {
                "bid_adapters": "*BidAdapter.js",
                "analytics_adapters": "*AnalyticsAdapter.js",
                "rtd_modules": "*RtdProvider.js",
                "identity_modules": "*IdSystem.js",
                "other_modules": "*.js",
            }


class HistoryConfigManager:
    """Manages history configurations for repositories."""

    def __init__(self, config_file: str | None = None):
        """Initialize config manager.

        Args:
            config_file: Path to configuration file, defaults to built-in repos.json
        """
        self.logger = get_logger(__name__)

        if config_file is None:
            # Use the existing repos.json from repo_modules
            repo_modules_dir = Path(__file__).parent.parent / "repo_modules"
            self.config_file = repo_modules_dir / "repos.json"
        else:
            self.config_file = Path(config_file)
        self._configs: dict[str, HistoryConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load configurations from file."""
        try:
            if not self.config_file.exists():
                self.logger.warning(f"Config file not found: {self.config_file}")
                return

            with open(self.config_file) as f:
                data = json.load(f)

            for repo_id, repo_data in data.items():
                # Convert repo_modules config to history config
                config = HistoryConfig(
                    repo_name=repo_data["repo"],
                    description=repo_data.get("description", ""),
                    parser_type=repo_data.get("parser_type", "default"),
                    fetch_strategy=repo_data.get("fetch_strategy", "filenames_only"),
                    version_override=repo_data.get("version_override"),
                )

                # Set specific module patterns based on parser type
                if config.parser_type == "prebid_js":
                    config.module_patterns = {
                        "bid_adapters": "*BidAdapter.js",
                        "analytics_adapters": "*AnalyticsAdapter.js",
                        "rtd_modules": "*RtdProvider.js",
                        "identity_modules": "*IdSystem.js",
                        "other_modules": "*.js",
                    }
                elif config.parser_type in ["prebid_server_go", "prebid_server_java"]:
                    config.module_patterns = {
                        "bid_adapters": "*",  # Directory-based
                        "analytics_adapters": "*",
                        "privacy_modules": "*",
                        "other_modules": "*",
                    }

                self._configs[repo_id] = config

            self.logger.info(f"Loaded {len(self._configs)} repository configurations")

        except Exception as e:
            self.logger.error(f"Failed to load configs: {e}")
            self._configs = {}

    def get_config(self, repo_id: str) -> HistoryConfig | None:
        """Get configuration for a repository."""
        return self._configs.get(repo_id)

    def get_available_repos(self) -> list[str]:
        """Get list of available repository IDs."""
        return list(self._configs.keys())

    def get_config_by_repo_name(self, repo_name: str) -> HistoryConfig | None:
        """Get configuration by repository name (owner/repo format)."""
        for config in self._configs.values():
            if config.repo_name == repo_name:
                return config
        return None
