"""
Tests for filename_generator.py - Shared filename generation utilities
"""

import os
import tempfile
from pathlib import Path

from src.shared_utilities.filename_generator import (
    clean_version_for_filename,
    ensure_output_directory,
    generate_output_filename,
    generate_timestamped_filename,
    generate_unique_filename,
    get_safe_filename,
)


class TestGenerateOutputFilename:
    """Tests for generate_output_filename function"""

    def test_known_repository_mapping(self):
        """Test that known repositories are mapped to predefined slugs"""
        result = generate_output_filename(
            "prebid/Prebid.js", "v9.0.0", "alias_mappings"
        )
        assert result == "prebid.js_alias_mappings_9.0.0.txt"

    def test_custom_slug_override(self):
        """Test that custom slug overrides default mapping"""
        result = generate_output_filename(
            "prebid/Prebid.js", "v9.0.0", "alias_mappings", custom_slug="custom.slug"
        )
        assert result == "custom.slug_alias_mappings_9.0.0.txt"

    def test_unknown_repository_generation(self):
        """Test filename generation for unknown repositories"""
        result = generate_output_filename("owner/test-repo", "v1.0.0", "modules")
        assert result == "test.repo_modules_1.0.0.txt"

    def test_custom_extension(self):
        """Test custom file extension"""
        result = generate_output_filename(
            "prebid/Prebid.js", "v9.0.0", "alias_mappings", extension="json"
        )
        assert result == "prebid.js_alias_mappings_9.0.0.json"

    def test_version_cleaning(self):
        """Test that version strings are properly cleaned"""
        result = generate_output_filename("prebid/Prebid.js", "feature/test", "modules")
        assert result == "prebid.js_modules_feature_test.txt"


class TestCleanVersionForFilename:
    """Tests for clean_version_for_filename function"""

    def test_remove_leading_v(self):
        """Test removal of leading 'v' from version"""
        assert clean_version_for_filename("v3.19.0") == "3.19.0"
        assert clean_version_for_filename("3.19.0") == "3.19.0"

    def test_replace_slashes(self):
        """Test replacement of slashes with underscores"""
        assert clean_version_for_filename("feature/branch") == "feature_branch"

    def test_replace_problematic_characters(self):
        """Test replacement of problematic filename characters"""
        assert clean_version_for_filename("v1.0:test") == "1.0_test"
        assert clean_version_for_filename('v1.0"test') == "1.0_test"
        assert clean_version_for_filename("v1.0*test") == "1.0_test"

    def test_complex_version_string(self):
        """Test cleaning of complex version strings"""
        assert (
            clean_version_for_filename('v1.0.0-beta:test"branch')
            == "1.0.0-beta_test_branch"
        )


class TestGenerateTimestampedFilename:
    """Tests for generate_timestamped_filename function"""

    def test_date_only_timestamp(self):
        """Test filename with date-only timestamp"""
        result = generate_timestamped_filename(
            "test", include_date=True, include_time=False
        )
        # Should match pattern: test_YYYYMMDD.txt
        assert result.startswith("test_")
        assert result.endswith(".txt")
        assert len(result.split("_")[1].split(".")[0]) == 8  # YYYYMMDD

    def test_date_and_time_timestamp(self):
        """Test filename with date and time timestamp"""
        result = generate_timestamped_filename(
            "test", include_date=True, include_time=True
        )
        # Should match pattern: test_YYYYMMDD_HHMMSS.txt
        assert result.startswith("test_")
        assert result.endswith(".txt")
        timestamp_parts = result.split("_")[1:]
        assert len(timestamp_parts) == 2
        assert len(timestamp_parts[0]) == 8  # YYYYMMDD
        assert len(timestamp_parts[1].split(".")[0]) == 6  # HHMMSS

    def test_no_timestamp(self):
        """Test filename without timestamp"""
        result = generate_timestamped_filename(
            "test", include_date=False, include_time=False
        )
        assert result == "test.txt"

    def test_custom_extension_timestamped(self):
        """Test timestamped filename with custom extension"""
        result = generate_timestamped_filename(
            "test", extension="json", include_date=True
        )
        assert result.endswith(".json")


class TestEnsureOutputDirectory:
    """Tests for ensure_output_directory function"""

    def test_create_directory_structure(self):
        """Test creation of directory structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "nested", "dir", "file.txt")
            result_path = ensure_output_directory(test_path)

            assert result_path == Path(test_path)
            assert result_path.parent.exists()
            assert result_path.parent.is_dir()

    def test_existing_directory(self):
        """Test with existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "file.txt")
            result_path = ensure_output_directory(test_path)

            assert result_path == Path(test_path)
            assert result_path.parent.exists()


class TestGetSafeFilename:
    """Tests for get_safe_filename function"""

    def test_replace_spaces(self):
        """Test replacement of spaces with underscores"""
        assert get_safe_filename("test file name") == "test_file_name"

    def test_remove_problematic_characters(self):
        """Test removal of problematic characters"""
        unsafe_name = 'file/name\\with:bad*chars?"<>|'
        safe_name = get_safe_filename(unsafe_name)
        assert safe_name == "file_name_with_bad_chars"

    def test_remove_multiple_underscores(self):
        """Test removal of multiple consecutive underscores"""
        assert (
            get_safe_filename("test__multiple___underscores")
            == "test_multiple_underscores"
        )

    def test_strip_leading_trailing_underscores(self):
        """Test removal of leading and trailing underscores"""
        assert get_safe_filename("_test_filename_") == "test_filename"

    def test_newlines_and_tabs(self):
        """Test replacement of newlines and tabs"""
        assert get_safe_filename("test\nfile\tname\r") == "test_file_name"


class TestGenerateUniqueFilename:
    """Tests for generate_unique_filename function"""

    def test_unique_filename_no_conflict(self):
        """Test unique filename when no conflict exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = generate_unique_filename(temp_dir, "test", "txt")
            assert result == "test.txt"

    def test_unique_filename_with_conflict(self):
        """Test unique filename when conflicts exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create conflicting files
            Path(temp_dir, "test.txt").touch()
            Path(temp_dir, "test_1.txt").touch()

            result = generate_unique_filename(temp_dir, "test", "txt")
            assert result == "test_2.txt"

    def test_unique_filename_multiple_conflicts(self):
        """Test unique filename with multiple conflicts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple conflicting files
            for i in range(5):
                if i == 0:
                    Path(temp_dir, "test.txt").touch()
                else:
                    Path(temp_dir, f"test_{i}.txt").touch()

            result = generate_unique_filename(temp_dir, "test", "txt")
            assert result == "test_5.txt"


class TestIntegration:
    """Integration tests combining multiple functions"""

    def test_complete_filename_workflow(self):
        """Test complete workflow from generation to ensuring directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate filename
            filename = generate_output_filename("test/repo", "v1.0.0", "modules")
            assert filename == "repo_modules_1.0.0.txt"

            # Create full path
            full_path = os.path.join(temp_dir, "output", filename)

            # Ensure directory exists
            path_obj = ensure_output_directory(full_path)
            assert path_obj.parent.exists()

            # Test unique filename generation
            Path(full_path).touch()  # Create the file
            unique_filename = generate_unique_filename(
                path_obj.parent, "repo_modules_1.0.0", "txt"
            )
            assert unique_filename == "repo_modules_1.0.0_1.txt"

    def test_safe_filename_with_timestamp(self):
        """Test safe filename generation with timestamp"""
        unsafe_base = "test file:with/bad*chars"
        safe_base = get_safe_filename(unsafe_base)
        assert safe_base == "test_file_with_bad_chars"

        timestamped = generate_timestamped_filename(safe_base, include_date=True)
        assert timestamped.startswith("test_file_with_bad_chars_")
        assert timestamped.endswith(".txt")
