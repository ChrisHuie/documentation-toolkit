"""Tests for module history configuration system."""

import json
import tempfile
from pathlib import Path

from src.module_history.config import HistoryConfig, HistoryConfigManager


class TestHistoryConfig:
    """Test HistoryConfig dataclass."""

    def test_default_initialization(self):
        """Test default configuration initialization."""
        config = HistoryConfig(repo_name="test/repo")

        assert config.repo_name == "test/repo"
        assert config.parser_type == "default"
        assert config.fetch_strategy == "filenames_only"
        assert config.version_override is None
        assert config.description == ""

        # Test default module patterns are set
        assert config.module_patterns is not None
        assert "bid_adapters" in config.module_patterns
        assert config.module_patterns["bid_adapters"] == "*BidAdapter.js"

    def test_custom_initialization(self):
        """Test configuration with custom values."""
        custom_patterns = {"custom_modules": "*.js"}
        config = HistoryConfig(
            repo_name="custom/repo",
            parser_type="custom",
            fetch_strategy="full_content",
            module_patterns=custom_patterns,
            version_override="master",
            description="Custom repo",
        )

        assert config.repo_name == "custom/repo"
        assert config.parser_type == "custom"
        assert config.fetch_strategy == "full_content"
        assert config.module_patterns == custom_patterns
        assert config.version_override == "master"
        assert config.description == "Custom repo"


class TestHistoryConfigManager:
    """Test HistoryConfigManager."""

    def test_load_configs_from_file(self):
        """Test loading configurations from a JSON file."""
        # Create temporary config file
        config_data = {
            "test-repo": {
                "repo": "test/repository",
                "description": "Test repository",
                "parser_type": "prebid_js",
                "fetch_strategy": "filenames_only",
                "version_override": "master",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager = HistoryConfigManager(temp_file)

            # Test that config was loaded
            available_repos = manager.get_available_repos()
            assert "test-repo" in available_repos

            # Test getting specific config
            config = manager.get_config("test-repo")
            assert config is not None
            assert config.repo_name == "test/repository"
            assert config.description == "Test repository"
            assert config.parser_type == "prebid_js"
            assert config.fetch_strategy == "filenames_only"
            assert config.version_override == "master"

            # Test module patterns for prebid_js
            assert config.module_patterns["bid_adapters"] == "*BidAdapter.js"

        finally:
            Path(temp_file).unlink()

    def test_get_config_by_repo_name(self):
        """Test getting configuration by repository name."""
        config_data = {
            "test-repo": {"repo": "test/repository", "description": "Test repository"}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager = HistoryConfigManager(temp_file)

            # Test finding by repo name
            config = manager.get_config_by_repo_name("test/repository")
            assert config is not None
            assert config.repo_name == "test/repository"

            # Test not found
            config = manager.get_config_by_repo_name("nonexistent/repo")
            assert config is None

        finally:
            Path(temp_file).unlink()

    def test_nonexistent_config_file(self):
        """Test handling of nonexistent config file."""
        manager = HistoryConfigManager("/nonexistent/path/config.json")

        # Should not raise exception
        available_repos = manager.get_available_repos()
        assert available_repos == []

        config = manager.get_config("any-repo")
        assert config is None

    def test_prebid_server_patterns(self):
        """Test module patterns for Prebid Server repositories."""
        config_data = {
            "prebid-server": {
                "repo": "prebid/prebid-server",
                "parser_type": "prebid_server_go",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager = HistoryConfigManager(temp_file)
            config = manager.get_config("prebid-server")

            assert config is not None
            assert config.module_patterns["bid_adapters"] == "*"
            assert config.module_patterns["analytics_adapters"] == "*"
            assert config.module_patterns["privacy_modules"] == "*"

        finally:
            Path(temp_file).unlink()
