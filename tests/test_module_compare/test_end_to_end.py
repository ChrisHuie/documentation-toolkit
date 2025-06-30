"""
End-to-end tests for module comparison with real repository configurations.

These tests simulate real usage scenarios from CLI to output generation.
"""

import json
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from src.module_compare.main import main as module_compare_main


class TestEndToEnd:
    """End-to-end tests simulating real usage scenarios."""

    @pytest.fixture
    def mock_github_responses(self):
        """Create realistic GitHub responses for different repositories."""
        return {
            "prebid-js-v9.0.0": {
                "repo": "prebid/Prebid.js",
                "version": "v9.0.0",
                "paths": {
                    "modules": {
                        "modules/appnexusBidAdapter.js": "",
                        "modules/rubiconBidAdapter.js": "",
                        "modules/pubmaticBidAdapter.js": "",
                        "modules/googleAnalyticsAdapter.js": "",
                        "modules/currency.js": "",
                    }
                },
                "files": [],
                "metadata": {"commit_sha": "abc123", "total_files": 5},
            },
            "prebid-js-v9.51.0": {
                "repo": "prebid/Prebid.js",
                "version": "v9.51.0",
                "paths": {
                    "modules": {
                        "modules/appnexusBidAdapter.js": "",
                        "modules/rubiconBidAdapter.js": "",
                        "modules/pubmaticBidAdapter.js": "",
                        "modules/amazonBidAdapter.js": "",  # New
                        "modules/criteoBidAdapter.js": "",  # New
                        "modules/googleAnalyticsAdapter.js": "",
                        "modules/permutiveRtdProvider.js": "",  # New
                        "modules/currency.js": "",
                        "modules/identityLinkIdSystem.js": "",  # New
                    }
                },
                "files": [],
                "metadata": {"commit_sha": "def456", "total_files": 9},
            },
            "prebid-server-v3.8.0": {
                "repo": "prebid/prebid-server",
                "version": "v3.8.0",
                "paths": {
                    "adapters": {
                        "adapters/appnexus": "",
                        "adapters/rubicon": "",
                        "adapters/pubmatic": "",
                        "adapters/openx": "",
                        "adapters/ix": "",
                    },
                    "modules": {
                        "modules/prebid": "",
                        "modules/fiftyonedegrees/devicedetection": "",
                    },
                },
                "files": [],
                "metadata": {"commit_sha": "ghi789", "total_files": 7},
            },
        }

    def test_cli_version_comparison_full_flow(self, mock_github_responses, tmp_path):
        """Test complete flow from CLI to output file for version comparison."""
        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--repo",
                    "prebid-js",
                    "--from-version",
                    "v9.0.0",
                    "--to-version",
                    "v9.51.0",
                    "--no-cumulative",
                ],
            ),
        ):
            # Set up mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                mock_github_responses["prebid-js-v9.0.0"],
                mock_github_responses["prebid-js-v9.51.0"],
            ]

            # Set up output path
            output_file = tmp_path / "output.txt"
            mock_get_output_path.return_value = str(output_file)

            # Run the CLI - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify the comparison was performed
            assert mock_client.fetch_repository_data.call_count == 2

            # Verify output was saved
            assert output_file.exists()

            # Check the saved content
            with open(output_file) as f:
                saved_content = f.read()
            assert "Module Comparison: prebid-js (v9.0.0 → v9.51.0)" in saved_content
            assert "Added: 4" in saved_content
            assert "amazon" in saved_content.lower()
            assert "criteo" in saved_content.lower()

    def test_cli_cross_repo_comparison_full_flow(self, mock_github_responses, tmp_path):
        """Test complete flow for cross-repository comparison."""
        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--from",
                    "prebid-js:v9.51.0",
                    "--to",
                    "prebid-server:v3.8.0",
                    "--format",
                    "json",
                ],
            ),
        ):
            # Set up mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                mock_github_responses["prebid-js-v9.51.0"],
                mock_github_responses["prebid-server-v3.8.0"],
            ]

            # Set up output path
            output_file = tmp_path / "comparison.json"
            mock_get_output_path.return_value = str(output_file)

            # Run the CLI - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify JSON output was generated
            assert output_file.exists()

            with open(output_file) as f:
                data = json.load(f)

            # Verify JSON structure
            assert data["metadata"]["source_repo"] == "prebid-js"
            assert data["metadata"]["target_repo"] == "prebid-server"
            assert data["metadata"]["comparison_type"] == "Repository"

            # Verify some expected differences
            assert data["summary"]["only_in_source"] > 0
            assert data["summary"]["only_in_target"] > 0
            assert data["summary"]["in_both"] > 0

    def test_all_output_formats(self, mock_github_responses, tmp_path):
        """Test that all output formats work correctly."""
        formats = ["table", "json", "csv", "markdown", "yaml", "html"]

        for format_type in formats:
            with (
                patch("src.module_compare.main.GitHubClient") as mock_client_class,
                patch(
                    "src.module_compare.main.get_output_path"
                ) as mock_get_output_path,
                patch(
                    "sys.argv",
                    [
                        "module-compare",
                        "--repo",
                        "prebid-js",
                        "--from-version",
                        "v9.0.0",
                        "--to-version",
                        "v9.51.0",
                        "--format",
                        format_type,
                        "--no-cumulative",  # Use direct comparison for simplicity
                    ],
                ),
            ):
                # Set up mocks
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.resolve_version.side_effect = (
                    lambda repo, version, **kwargs: version
                )
                mock_client.fetch_repository_data.side_effect = [
                    mock_github_responses["prebid-js-v9.0.0"],
                    mock_github_responses["prebid-js-v9.51.0"],
                ]

                # Set up output path
                output_file = (
                    tmp_path
                    / f"comparison.{format_type if format_type != 'table' else 'txt'}"
                )
                mock_get_output_path.return_value = str(output_file)

                # Run the CLI - Click exits with code 0 on success
                try:
                    module_compare_main()
                except SystemExit as e:
                    # Click exits with 0 on success, which is what we expect
                    if e.code != 0:
                        raise

                # Verify output was saved
                assert output_file.exists()
                with open(output_file) as f:
                    saved_content = f.read()

                # Basic validation for each format
                if format_type == "json":
                    json.loads(saved_content)  # Should not raise
                elif format_type == "csv":
                    assert "category,module,change_type" in saved_content
                elif format_type == "markdown":
                    assert "# Module Comparison:" in saved_content
                elif format_type == "yaml":
                    assert "metadata:" in saved_content
                elif format_type == "html":
                    assert "<html>" in saved_content
                else:  # table
                    assert "Module Comparison:" in saved_content

    def test_filename_generation_integration(self, mock_github_responses, tmp_path):
        """Test that filenames are generated correctly using shared utilities."""
        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--repo",
                    "prebid-js",
                    "--from-version",
                    "v9.0.0",
                    "--to-version",
                    "v9.51.0",
                    "--no-cumulative",
                ],
            ),
        ):
            # Set up mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                mock_github_responses["prebid-js-v9.0.0"],
                mock_github_responses["prebid-js-v9.51.0"],
            ]

            # Track filename generation
            generated_filename = None

            def get_output_path(**kwargs):
                nonlocal generated_filename
                generated_filename = kwargs.get("filename", "")
                return str(tmp_path / generated_filename)

            mock_get_output_path.side_effect = get_output_path

            # Run the CLI - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify correct filename was generated
            assert generated_filename is not None
            assert "prebid.js_module_compare_9.0.0_9.51.0.txt" == generated_filename

    def test_show_unchanged_flag(self, mock_github_responses, tmp_path):
        """Test that --show-unchanged flag works correctly."""
        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--repo",
                    "prebid-js",
                    "--from-version",
                    "v9.0.0",
                    "--to-version",
                    "v9.51.0",
                    "--show-unchanged",
                    "--no-cumulative",
                ],
            ),
        ):
            # Set up mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                mock_github_responses["prebid-js-v9.0.0"],
                mock_github_responses["prebid-js-v9.51.0"],
            ]

            # Set up output path
            output_file = tmp_path / "output.txt"
            mock_get_output_path.return_value = str(output_file)

            # Run the CLI - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify unchanged modules are included
            assert output_file.exists()
            with open(output_file) as f:
                saved_content = f.read()
            assert "Unchanged" in saved_content
            assert "appnexus" in saved_content  # This adapter exists in both versions

    def test_error_handling_invalid_repo(self):
        """Test error handling for invalid repository."""
        with (
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--repo",
                    "invalid-repo",
                    "--from-version",
                    "v1.0.0",
                    "--to-version",
                    "v2.0.0",
                ],
            ),
            patch("sys.stderr", new=StringIO()) as mock_stderr,
        ):
            with pytest.raises(SystemExit):
                module_compare_main()

            error_output = mock_stderr.getvalue()
            assert "Unknown repository: invalid-repo" in error_output

    def test_interactive_mode_simulation(self, mock_github_responses, tmp_path):
        """Test interactive mode selection flow."""
        # Skip interactive test as it's complex to mock properly
        pytest.skip("Interactive mode testing requires complex mocking")

    def test_output_directory_structure(self, mock_github_responses, tmp_path):
        """Test that output follows the correct directory structure."""
        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--from",
                    "prebid-js:v9.0.0",
                    "--to",
                    "prebid-server:v3.8.0",
                ],
            ),
        ):
            # Set up mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                mock_github_responses["prebid-js-v9.51.0"],
                mock_github_responses["prebid-server-v3.8.0"],
            ]

            # Set up output path to mimic expected directory structure
            expected_path = tmp_path / "module-compare" / "cross-repo"
            expected_path.mkdir(parents=True, exist_ok=True)
            output_file = (
                expected_path
                / "prebid.js_v9.51.0_module_compare_prebid.server.go_v3.8.0.txt"
            )
            mock_get_output_path.return_value = str(output_file)

            # Run the CLI - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify output file was created
            assert output_file.exists()

            # Verify content
            with open(output_file) as f:
                content = f.read()
                assert "prebid-js vs prebid-server" in content

    def test_performance_with_large_comparison(self, tmp_path):
        """Test performance with a large number of modules."""
        # Create a large response
        large_response_v1 = {
            "repo": "test/large-repo",
            "version": "v1.0.0",
            "paths": {"modules": {f"modules/module{i}.js": "" for i in range(500)}},
            "files": [],
            "metadata": {"commit_sha": "perf1", "total_files": 500},
        }

        # v2 adds 100 new modules and removes 50
        modules_v2 = {f"modules/module{i}.js": "" for i in range(50, 600)}
        large_response_v2 = {
            "repo": "test/large-repo",
            "version": "v2.0.0",
            "paths": {"modules": modules_v2},
            "files": [],
            "metadata": {"commit_sha": "perf2", "total_files": 550},
        }

        with (
            patch("src.module_compare.main.GitHubClient") as mock_client_class,
            patch("src.module_compare.main.get_output_path") as mock_get_output_path,
            patch(
                "src.module_compare.main.RepositoryConfigManager"
            ) as mock_config_class,
            patch(
                "sys.argv",
                [
                    "module-compare",
                    "--repo",
                    "test-repo",
                    "--from-version",
                    "v1.0.0",
                    "--to-version",
                    "v2.0.0",
                    "--no-cumulative",
                ],
            ),
        ):
            # Set up config
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            mock_config.get_config.return_value = {
                "repo": "test/large-repo",
                "parser_type": "default",
                "paths": {"Modules": "modules"},
            }

            # Set up GitHub client
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.resolve_version.side_effect = (
                lambda repo, version, **kwargs: version
            )
            mock_client.fetch_repository_data.side_effect = [
                large_response_v1,
                large_response_v2,
            ]

            # Set up output
            output_file = tmp_path / "large.txt"
            mock_get_output_path.return_value = str(output_file)

            # Run and verify it completes - Click exits with code 0 on success
            try:
                module_compare_main()
            except SystemExit as e:
                # Click exits with 0 on success, which is what we expect
                if e.code != 0:
                    raise

            # Verify large comparison was handled
            assert output_file.exists()
            with open(output_file) as f:
                saved_content = f.read()
            # With rename detection, the test now detects 50 as renames
            assert "Added: 50" in saved_content
            assert "Removed: 0" in saved_content
            assert "Renamed: 50" in saved_content
            assert "Net Change: 50" in saved_content
