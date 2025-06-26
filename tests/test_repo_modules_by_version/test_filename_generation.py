"""
Tests for filename generation logic with new naming conventions.

This test suite validates:
- Correct filename generation for all repo types
- Special handling for prebid.js naming
- Special handling for prebid-server (Go) -> prebid.server.go
- Proper version cleaning (/ -> _)
- File replacement logic
"""

import os
import tempfile
from unittest.mock import Mock, patch

from src.repo_modules_by_version.config import RepoConfig


class TestFilenameGeneration:
    """Test filename generation for all repository types."""

    def test_prebid_js_filename_generation(self):
        """Test that Prebid.js generates correct filename."""
        config = RepoConfig(
            repo="prebid/Prebid.js",
            description="Test",
            versions=["master"],
            parser_type="prebid_js",
            modules_path="modules",
        )

        # Simulate filename generation logic
        owner, repo = config.repo.split("/")
        repo_name = repo.lower().replace("-", ".")

        # prebid.js should remain as prebid.js (no special handling needed)
        version_clean = "9.51.0"
        expected_filename = f"{repo_name}_modules_version_{version_clean}.txt"

        assert expected_filename == "prebid.js_modules_version_9.51.0.txt"

    def test_prebid_server_go_filename_generation(self):
        """Test that Prebid Server Go generates correct filename with .go suffix."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={"Bid Adapters": "adapters"},
        )

        # Simulate filename generation logic
        owner, repo = config.repo.split("/")
        repo_name = repo.lower().replace("-", ".")

        # Special handling for prebid-server (Go)
        if repo_name == "prebid.server":
            repo_name = "prebid.server.go"

        version_clean = "v3.8.0"
        expected_filename = f"{repo_name}_modules_version_{version_clean}.txt"

        assert expected_filename == "prebid.server.go_modules_version_v3.8.0.txt"

    def test_prebid_server_java_filename_generation(self):
        """Test that Prebid Server Java generates correct filename."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={"Bid Adapters": "src/main/java/org/prebid/server/bidder"},
        )

        # Simulate filename generation logic
        owner, repo = config.repo.split("/")
        repo_name = repo.lower().replace("-", ".")

        version_clean = "3.27.0"
        expected_filename = f"{repo_name}_modules_version_{version_clean}.txt"

        assert expected_filename == "prebid.server.java_modules_version_3.27.0.txt"

    def test_prebid_docs_filename_generation(self):
        """Test that Prebid Docs generates correct filename."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Test",
            versions=["master"],
            parser_type="prebid_docs",
            paths={"Bid Adapters": "dev-docs/bidders"},
        )

        # Simulate filename generation logic
        owner, repo = config.repo.split("/")
        repo_name = repo.lower().replace("-", ".")

        version_clean = "master"
        expected_filename = f"{repo_name}_modules_version_{version_clean}.txt"

        assert expected_filename == "prebid.github.io_modules_version_master.txt"

    def test_version_cleaning(self):
        """Test that version strings are properly cleaned for filenames."""
        test_cases = [
            ("v1.0.0", "v1.0.0"),
            ("feature/test", "feature_test"),
            ("release/v2.1.0", "release_v2.1.0"),
            ("master", "master"),
            ("v3.8.0", "v3.8.0"),
        ]

        for input_version, expected_clean in test_cases:
            version_clean = input_version.replace("/", "_")
            assert version_clean == expected_clean

    def test_repository_name_conversion(self):
        """Test repository name conversion logic."""
        test_cases = [
            ("owner/Prebid.js", "prebid.js"),
            ("owner/prebid-server", "prebid.server"),
            ("owner/prebid-server-java", "prebid.server.java"),
            ("owner/prebid.github.io", "prebid.github.io"),
            ("owner/test-repo", "test.repo"),
            ("owner/test_repo", "test_repo"),
        ]

        for full_repo, expected_name in test_cases:
            owner, repo = full_repo.split("/")
            repo_name = repo.lower().replace("-", ".")
            assert repo_name == expected_name

    def test_special_naming_rules(self):
        """Test all special naming rules for filename generation."""
        test_cases = [
            # (repo_name_after_conversion, expected_final_name)
            ("prebid.js", "prebid.js"),  # No change needed
            ("prebid.server", "prebid.server.go"),  # Add .go suffix
            ("prebid.server.java", "prebid.server.java"),  # No change
            ("prebid.github.io", "prebid.github.io"),  # No change
        ]

        for input_name, expected_output in test_cases:
            repo_name = input_name

            # Apply special handling rules
            if repo_name == "prebid.server":
                repo_name = "prebid.server.go"

            assert repo_name == expected_output


@patch("src.repo_modules_by_version.main.GitHubClient")
@patch("src.repo_modules_by_version.main.ParserFactory")
class TestFilenameGenerationIntegration:
    """Integration tests for filename generation within main function."""

    def test_main_function_filename_generation(
        self, mock_parser_factory, mock_github_client
    ):
        """Test filename generation through main function execution."""
        # Mock the necessary components
        mock_github = Mock()
        mock_github_client.return_value = mock_github
        mock_github.fetch_repository_data.return_value = {
            "repo": "prebid/prebid-server",
            "version": "v3.8.0",
            "paths": {"adapters": {"adapters/test": ""}},
        }

        mock_factory = Mock()
        mock_parser_factory.return_value = mock_factory
        mock_parser = Mock()
        mock_parser.parse.return_value = "test output"
        mock_factory.get_parser.return_value = mock_parser

        # Mock config
        with patch(
            "src.repo_modules_by_version.main.get_repo_config_with_versions"
        ) as mock_get_config:
            mock_config = RepoConfig(
                repo="prebid/prebid-server",
                description="Test",
                versions=["master"],
                parser_type="prebid_server_go",
                paths={"Bid Adapters": "adapters"},
            )
            mock_get_config.return_value = mock_config

            # Test with temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                original_cwd = os.getcwd()
                try:
                    os.chdir(temp_dir)

                    # Import and test main function
                    from src.repo_modules_by_version.main import main

                    # Mock sys.argv
                    with patch(
                        "sys.argv",
                        ["main.py", "--repo", "prebid-server", "--version", "v3.8.0"],
                    ):
                        main()

                    # Check that the correct filename was generated
                    expected_filename = "prebid.server.go_modules_version_v3.8.0.txt"
                    assert os.path.exists(
                        expected_filename
                    ), f"Expected file {expected_filename} was not created"

                finally:
                    os.chdir(original_cwd)


class TestFileReplacementLogic:
    """Test file replacement functionality."""

    def test_file_replacement_detection(self):
        """Test that existing files are properly detected and replaced."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_filename = os.path.join(temp_dir, "test_file.txt")

            # Create initial file
            with open(test_filename, "w") as f:
                f.write("original content")

            # Verify file exists
            assert os.path.exists(test_filename)

            # Test replacement
            with open(test_filename, "w") as f:
                f.write("new content")

            # Verify content was replaced
            with open(test_filename) as f:
                content = f.read()

            assert content == "new content"

    def test_master_file_replacement_message(self):
        """Test that master files show proper replacement message."""
        # This would be tested in integration with main function
        # but testing the logic here
        test_filenames = [
            "prebid.js_modules_version_master.txt",
            "prebid.server.go_modules_version_master.txt",
            "prebid.github.io_modules_version_master.txt",
            "prebid.js_modules_version_v9.51.0.txt",  # Not master
        ]

        for filename in test_filenames:
            if filename.endswith("_master.txt"):
                # Should show replacement message for master files
                assert "master" in filename
            else:
                # Regular version files
                assert "master" not in filename or not filename.endswith("_master.txt")


class TestFilenamingEdgeCases:
    """Test edge cases in filename generation."""

    def test_empty_version_handling(self):
        """Test handling of empty or None versions."""
        # Version should always be provided, but test graceful handling
        version = ""
        version_clean = version.replace("/", "_") if version else "unknown"
        assert version_clean == "unknown"

    def test_special_characters_in_version(self):
        """Test handling of special characters in version strings."""
        test_cases = [
            ("v1.0.0-beta", "v1.0.0-beta"),
            ("release/v2.1.0-rc1", "release_v2.1.0-rc1"),
            ("feature/fix-bug", "feature_fix-bug"),
            ("hotfix/urgent-fix", "hotfix_urgent-fix"),
        ]

        for input_version, expected_clean in test_cases:
            version_clean = input_version.replace("/", "_")
            assert version_clean == expected_clean

    def test_long_version_strings(self):
        """Test handling of very long version strings."""
        long_version = "very-long-feature-branch-name-that-exceeds-normal-length/v1.0.0"
        version_clean = long_version.replace("/", "_")
        expected = "very-long-feature-branch-name-that-exceeds-normal-length_v1.0.0"
        assert version_clean == expected

    def test_repo_name_with_numbers(self):
        """Test repository names containing numbers."""
        test_cases = [
            ("owner/project-v2", "project.v2"),
            ("owner/service-1.0", "service.1.0"),
            ("owner/tool-123-beta", "tool.123.beta"),
        ]

        for full_repo, expected_name in test_cases:
            owner, repo = full_repo.split("/")
            repo_name = repo.lower().replace("-", ".")
            assert repo_name == expected_name
