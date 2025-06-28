"""
Tests for module history CLI functionality.
"""

import json
import tempfile
import unittest.mock
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.repo_modules.module_history import ModuleHistoryCache, ModuleHistoryEntry
from src.repo_modules.module_history_cli import (
    format_csv_output,
    format_json_output,
    format_table_output,
    main,
)


class TestOutputFormatting:
    """Test output formatting functions."""

    @pytest.fixture
    def sample_modules(self):
        """Sample module history data for testing."""
        return {
            "appnexus": ModuleHistoryEntry(
                module_name="appnexus",
                module_type="bid_adapters",
                first_version="1.0.0",
                first_major_version=1,
                file_path="modules/appnexusBidAdapter.js",
            ),
            "ga": ModuleHistoryEntry(
                module_name="ga",
                module_type="analytics_adapters",
                first_version="2.0.0",
                first_major_version=2,
                file_path="modules/gaAnalyticsAdapter.js",
            ),
            "rtdModule": ModuleHistoryEntry(
                module_name="rtdModule",
                module_type="other_modules",
                first_version="2.5.0",
                first_major_version=2,
                file_path="modules/rtdModule.js",
            ),
            "unifiedId": ModuleHistoryEntry(
                module_name="unifiedId",
                module_type="identity_modules",
                first_version="3.0.0",
                first_major_version=3,
                file_path="modules/unifiedIdSystem.js",
            ),
        }

    def test_format_table_output(self, sample_modules):
        """Test table output formatting."""
        result = format_table_output(sample_modules)

        # Should contain header
        assert "Prebid.js Module History" in result
        assert "=" * 50 in result

        # Should contain module information
        assert "appnexus" in result
        assert "v1.0.0" in result
        assert "modules/appnexusBidAdapter.js" in result

        # Should group by type
        assert "Bid Adapters" in result
        assert "Analytics Adapters" in result
        assert "Identity Modules" in result
        assert "Other Modules" in result

        # Should contain summary
        assert "Summary:" in result
        assert "4 modules" in result

    def test_format_table_output_with_filter(self, sample_modules):
        """Test table output with module type filter."""
        result = format_table_output(sample_modules, module_type_filter="bid_adapters")

        # Should only contain bid adapters
        assert "appnexus" in result
        assert "ga" not in result
        assert "rtdModule" not in result
        assert "unifiedId" not in result

        # Should show filtered count
        assert "1 modules" in result

    def test_format_table_output_empty(self):
        """Test table output with no modules."""
        result = format_table_output({})
        assert result == "No modules found."

    def test_format_table_output_no_matches(self, sample_modules):
        """Test table output with filter that matches nothing."""
        result = format_table_output(
            sample_modules, module_type_filter="nonexistent_type"
        )
        assert "No modules found for type: nonexistent_type" in result

    def test_format_csv_output(self, sample_modules):
        """Test CSV output formatting."""
        result = format_csv_output(sample_modules)

        lines = result.strip().split("\n")

        # Should have header
        assert (
            lines[0]
            == "module_name,module_type,first_version,first_major_version,file_path"
        )

        # Should have data rows (sorted by module name)
        assert len(lines) == 5  # header + 4 modules

        # Check specific entries
        assert "appnexus,bid_adapters,1.0.0,1,modules/appnexusBidAdapter.js" in lines
        assert "ga,analytics_adapters,2.0.0,2,modules/gaAnalyticsAdapter.js" in lines

    def test_format_csv_output_with_filter(self, sample_modules):
        """Test CSV output with module type filter."""
        result = format_csv_output(
            sample_modules, module_type_filter="analytics_adapters"
        )

        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + 1 module
        assert "ga,analytics_adapters,2.0.0,2,modules/gaAnalyticsAdapter.js" in lines
        assert "appnexus" not in result

    def test_format_csv_output_empty(self):
        """Test CSV output with no modules."""
        result = format_csv_output({})
        assert (
            result
            == "module_name,module_type,first_version,first_major_version,file_path\n"
        )

    def test_format_json_output(self, sample_modules):
        """Test JSON output formatting."""
        result = format_json_output(sample_modules)

        # Should be valid JSON
        data = json.loads(result)

        # Should contain all modules
        assert len(data) == 4
        assert "appnexus" in data
        assert "ga" in data
        assert "rtdModule" in data
        assert "unifiedId" in data

        # Check structure of one entry
        appnexus = data["appnexus"]
        assert appnexus["module_name"] == "appnexus"
        assert appnexus["module_type"] == "bid_adapters"
        assert appnexus["first_version"] == "1.0.0"
        assert appnexus["first_major_version"] == 1
        assert appnexus["file_path"] == "modules/appnexusBidAdapter.js"

    def test_format_json_output_with_filter(self, sample_modules):
        """Test JSON output with module type filter."""
        result = format_json_output(
            sample_modules, module_type_filter="identity_modules"
        )

        data = json.loads(result)
        assert len(data) == 1
        assert "unifiedId" in data
        assert "appnexus" not in data

    def test_format_json_output_empty(self):
        """Test JSON output with no modules."""
        result = format_json_output({})
        data = json.loads(result)
        assert data == {}


class TestCLIInterface:
    """Test CLI command interface."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_tracker(self):
        """Create mock module history tracker."""
        tracker = MagicMock()

        # Sample data for testing
        sample_modules = {
            "appnexus": ModuleHistoryEntry(
                module_name="appnexus",
                module_type="bid_adapters",
                first_version="1.0.0",
                first_major_version=1,
                file_path="modules/appnexusBidAdapter.js",
            ),
            "ga": ModuleHistoryEntry(
                module_name="ga",
                module_type="analytics_adapters",
                first_version="2.0.0",
                first_major_version=2,
                file_path="modules/gaAnalyticsAdapter.js",
            ),
        }

        cache = ModuleHistoryCache(
            repo_name="prebid/Prebid.js",
            last_analyzed_version="9.52.0",
            modules=sample_modules,
            metadata={"analysis_date": "2023-01-01"},
        )

        tracker.analyze_module_history.return_value = cache
        tracker.get_modules_by_version.return_value = sample_modules
        tracker.get_cache_info.return_value = {
            "repo_name": "prebid/Prebid.js",
            "last_analyzed_version": "9.52.0",
            "module_count": 2,
            "cache_file": "/path/to/cache.json",
            "metadata": {"analysis_date": "2023-01-01"},
        }

        return tracker

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_default_command(self, mock_tracker_class, runner, mock_tracker):
        """Test running command with default parameters."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Prebid.js Module History" in result.output
        assert "appnexus" in result.output
        assert "ga" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_csv_format(self, mock_tracker_class, runner, mock_tracker):
        """Test CSV output format."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--format", "csv"])

        assert result.exit_code == 0
        assert "module_name,module_type,first_version" in result.output
        assert "appnexus,bid_adapters,1.0.0" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_json_format(self, mock_tracker_class, runner, mock_tracker):
        """Test JSON output format."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--format", "json"])

        assert result.exit_code == 0
        # Should be valid JSON
        json.loads(result.output)

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_module_type_filter(self, mock_tracker_class, runner, mock_tracker):
        """Test filtering by module type."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--type", "bid_adapters"])

        assert result.exit_code == 0
        assert "appnexus" in result.output
        # Should not contain analytics adapters in filtered output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_major_version_filter(self, mock_tracker_class, runner, mock_tracker):
        """Test filtering by major version."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--major-version", "1"])

        assert result.exit_code == 0
        mock_tracker.get_modules_by_version.assert_called_with("prebid/Prebid.js", 1)

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_output_file(self, mock_tracker_class, runner, mock_tracker):
        """Test writing output to file."""
        mock_tracker_class.return_value = mock_tracker

        with runner.isolated_filesystem():
            result = runner.invoke(main, ["--format", "json", "-o", "output.json"])

            assert result.exit_code == 0
            assert "Output written to output.json" in result.output

            # Check file was created and contains valid JSON
            with open("output.json") as f:
                data = json.load(f)
                assert "appnexus" in data

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_force_refresh(self, mock_tracker_class, runner, mock_tracker):
        """Test force refresh option."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--force-refresh"])

        assert result.exit_code == 0
        mock_tracker.analyze_module_history.assert_called_with(
            "prebid/Prebid.js", force_refresh=True, progress_callback=unittest.mock.ANY
        )

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_clear_cache(self, mock_tracker_class, runner, mock_tracker):
        """Test clearing cache."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--clear-cache"])

        assert result.exit_code == 0
        assert "Clearing module history cache" in result.output
        assert "Cache cleared successfully" in result.output
        mock_tracker.clear_cache.assert_called_with("prebid/Prebid.js")

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_cache_info(self, mock_tracker_class, runner, mock_tracker):
        """Test displaying cache information."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--cache-info"])

        assert result.exit_code == 0
        assert "Cache Information:" in result.output
        assert "prebid/Prebid.js" in result.output
        assert "9.52.0" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_cache_info_no_cache(self, mock_tracker_class, runner, mock_tracker):
        """Test cache info when no cache exists."""
        mock_tracker_class.return_value = mock_tracker
        mock_tracker.get_cache_info.return_value = None

        result = runner.invoke(main, ["--cache-info"])

        assert result.exit_code == 0
        assert "No cache found for repository" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_custom_repo(self, mock_tracker_class, runner, mock_tracker):
        """Test custom repository option."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--repo", "custom/repo"])

        assert result.exit_code == 0
        mock_tracker.analyze_module_history.assert_called_with(
            "custom/repo", force_refresh=False, progress_callback=unittest.mock.ANY
        )

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_quiet_mode(self, mock_tracker_class, runner, mock_tracker):
        """Test quiet mode (no progress indicators)."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--quiet"])

        assert result.exit_code == 0
        # Should not contain progress indicators in quiet mode
        assert "📊" not in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_github_token(self, mock_tracker_class, runner, mock_tracker):
        """Test GitHub token passing."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--token", "test_token"])

        assert result.exit_code == 0
        mock_tracker_class.assert_called_with(token="test_token")

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_error_handling(self, mock_tracker_class, runner):
        """Test error handling in CLI."""
        mock_tracker = MagicMock()
        mock_tracker.analyze_module_history.side_effect = Exception("Test error")
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Unexpected error: Test error" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_module_history_error(self, mock_tracker_class, runner):
        """Test ModuleHistoryError handling."""
        from src.repo_modules.module_history import ModuleHistoryError

        mock_tracker = MagicMock()
        mock_tracker.analyze_module_history.side_effect = ModuleHistoryError(
            "Module error"
        )
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "Error: Module error" in result.output

    def test_keyboard_interrupt(self, runner):
        """Test keyboard interrupt handling."""
        with patch(
            "src.repo_modules.module_history_cli.ModuleHistoryTracker"
        ) as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker.analyze_module_history.side_effect = KeyboardInterrupt()
            mock_tracker_class.return_value = mock_tracker

            result = runner.invoke(main, [])

            assert result.exit_code == 1
            assert "Operation cancelled by user" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_invalid_format_option(self, mock_tracker_class, runner, mock_tracker):
        """Test invalid format option."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--format", "invalid"])

        # Click should handle this and show error
        assert result.exit_code != 0
        assert "Invalid value for '--format'" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_invalid_type_option(self, mock_tracker_class, runner, mock_tracker):
        """Test invalid module type option."""
        mock_tracker_class.return_value = mock_tracker

        result = runner.invoke(main, ["--type", "invalid_type"])

        # Click should handle this and show error
        assert result.exit_code != 0
        assert "Invalid value for '--type'" in result.output

    @patch("src.repo_modules.module_history_cli.ModuleHistoryTracker")
    def test_help_text(self, mock_tracker_class, runner):
        """Test help text display."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Generate historical reports for Prebid.js modules" in result.output
        assert "Examples:" in result.output
        assert "--format" in result.output
        assert "--type" in result.output
