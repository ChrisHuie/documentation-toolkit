"""
Integration tests for supported-mediatypes CLI
"""

from unittest.mock import Mock, patch

import pytest

from src.supported_mediatypes.main import create_parser, main


class TestSupportedMediaTypesCLI:
    """Test cases for the supported-mediatypes CLI."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with (
            patch(
                "src.supported_mediatypes.main.RepositoryConfigManager"
            ) as mock_config_mgr,
            patch("src.supported_mediatypes.main.GitHubClient") as mock_github_client,
            patch("src.supported_mediatypes.main.MediaTypeExtractor") as mock_extractor,
            patch("src.supported_mediatypes.main.get_logger") as mock_logger,
        ):
            # Configure mocks
            mock_config_instance = Mock()
            mock_config_instance.get_config.return_value = {"repo": "prebid/Prebid.js"}
            mock_config_mgr.return_value = mock_config_instance

            mock_github_instance = Mock()
            mock_github_instance.get_semantic_versions.return_value = [
                "master",
                "v9.0.0 (current latest)",
            ]
            mock_github_client.return_value = mock_github_instance

            mock_extractor_instance = Mock()
            mock_extractor.return_value = mock_extractor_instance

            yield {
                "config_manager": mock_config_mgr,
                "github_client": mock_github_client,
                "extractor": mock_extractor_instance,
                "logger": mock_logger(),
            }

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()

        # Test with valid arguments
        args = parser.parse_args(["--version", "v9.0.0", "--format", "json"])
        assert args.version == "v9.0.0"
        assert args.format == "json"

        # Test defaults
        args = parser.parse_args([])
        assert args.version is None
        assert args.format == "table"
        assert args.summary is False
        assert args.show_json is False

    def test_main_success_table_output(self, mock_dependencies, capsys):
        """Test successful execution with table output to stdout."""
        # Configure mock extractor
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 1,
            "adapters_with_media_types": 1,
            "adapters": {
                "appnexus": {
                    "mediaTypes": ["banner", "video"],
                    "file": "modules/appnexusBidAdapter.js",
                }
            },
            "summary": {
                "total_adapters": 1,
                "by_media_type": {"banner": 1, "video": 1, "native": 0},
                "by_combination": {"banner, video": 1},
            },
        }

        # Run with no arguments (default table output)
        with patch("sys.argv", ["supported-mediatypes"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Prebid.js Supported Media Types Report" in captured.out
        assert "appnexus" in captured.out
        assert "banner, video" in captured.out

    def test_main_success_json_output_to_file(self, mock_dependencies):
        """Test successful execution with JSON output (mocked, no file creation)."""
        # Configure mock extractor
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 1,
            "adapters_with_media_types": 1,
            "adapters": {
                "appnexus": {
                    "mediaTypes": ["banner"],
                    "file": "modules/appnexusBidAdapter.js",
                }
            },
        }

        # Mock the formatter to prevent file creation
        with patch(
            "src.supported_mediatypes.main.MediaTypeOutputFormatter"
        ) as mock_formatter:
            mock_instance = Mock()
            mock_formatter.return_value = mock_instance

            # Run with JSON output
            with patch(
                "sys.argv",
                ["supported-mediatypes", "--format", "json", "--output", "test.json"],
            ):
                result = main()

        assert result == 0
        # Verify save was called with correct arguments
        mock_instance.save.assert_called_once()
        call_args = mock_instance.save.call_args
        assert call_args[0][1] == "test.json"  # output path
        assert call_args[0][2] == "json"  # format

    def test_main_with_specific_version(self, mock_dependencies):
        """Test execution with specific version."""
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v8.0.0",
            "total_adapters": 0,
            "adapters_with_media_types": 0,
            "adapters": {},
        }

        with patch("sys.argv", ["supported-mediatypes", "--version", "v8.0.0"]):
            main()

        # Verify version was passed correctly
        mock_dependencies["extractor"].extract_media_types.assert_called_with(
            "prebid/Prebid.js", "v8.0.0", specific_adapter=None
        )

    def test_main_with_specific_adapter(self, mock_dependencies):
        """Test execution for specific adapter."""
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 1,
            "adapters_with_media_types": 1,
            "adapters": {
                "rubicon": {
                    "mediaTypes": ["banner", "video", "native"],
                    "file": "modules/rubiconBidAdapter.js",
                }
            },
        }

        with patch("sys.argv", ["supported-mediatypes", "--adapter", "rubicon"]):
            result = main()

        assert result == 0
        mock_dependencies["extractor"].extract_media_types.assert_called_with(
            "prebid/Prebid.js", "v9.0.0", specific_adapter="rubicon"
        )

    def test_main_with_summary(self, mock_dependencies, capsys):
        """Test execution with summary flag."""
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 2,
            "adapters_with_media_types": 2,
            "adapters": {
                "adapter1": {
                    "mediaTypes": ["banner"],
                    "file": "modules/adapter1BidAdapter.js",
                },
                "adapter2": {
                    "mediaTypes": ["video"],
                    "file": "modules/adapter2BidAdapter.js",
                },
            },
            "summary": {
                "total_adapters": 2,
                "by_media_type": {"banner": 1, "video": 1, "native": 0},
                "by_combination": {"banner": 1, "video": 1},
            },
        }

        with patch("sys.argv", ["supported-mediatypes", "--summary"]):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Summary Statistics:" in captured.out
        assert "Media Type Usage:" in captured.out

    def test_main_no_adapters_found(self, mock_dependencies):
        """Test execution when no adapters are found."""
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 0,
            "adapters_with_media_types": 0,
            "adapters": {},
        }

        with patch("sys.argv", ["supported-mediatypes"]):
            result = main()

        assert result == 1  # Should return error code

    def test_main_keyboard_interrupt(self, mock_dependencies):
        """Test handling of keyboard interrupt."""
        mock_dependencies["extractor"].extract_media_types.side_effect = (
            KeyboardInterrupt()
        )

        with patch("sys.argv", ["supported-mediatypes"]):
            result = main()

        assert result == 130  # Standard exit code for Ctrl+C

    def test_main_exception_handling(self, mock_dependencies):
        """Test handling of general exceptions."""
        mock_dependencies["extractor"].extract_media_types.side_effect = Exception(
            "Test error"
        )

        with patch("sys.argv", ["supported-mediatypes"]):
            result = main()

        assert result == 1
        # Verify error was logged (logger might be from get_logger, not the mock)

    def test_main_csv_output_default_path(self, mock_dependencies):
        """Test CSV output with default path generation (mocked, no file creation)."""
        mock_dependencies["extractor"].extract_media_types.return_value = {
            "version": "v9.0.0",
            "total_adapters": 1,
            "adapters_with_media_types": 1,
            "adapters": {
                "test": {"mediaTypes": ["banner"], "file": "modules/testBidAdapter.js"}
            },
        }

        # Mock the formatter to prevent file creation
        with patch(
            "src.supported_mediatypes.main.MediaTypeOutputFormatter"
        ) as mock_formatter:
            mock_instance = Mock()
            mock_formatter.return_value = mock_instance

            with patch("sys.argv", ["supported-mediatypes", "--format", "csv"]):
                result = main()

            assert result == 0
            # Verify save was called with correct format
            mock_instance.save.assert_called_once()
            call_args = mock_instance.save.call_args
            assert call_args[0][2] == "csv"  # format
            # Path should contain expected pattern
            assert "prebid.js_supported_mediatypes" in str(call_args[0][1])
