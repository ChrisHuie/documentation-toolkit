"""
Tests for output_formatter.py - Shared output formatting utilities
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.shared_utilities.output_formatter import (
    AliasMapping,
    OutputFormatter,
    OutputMetadata,
    create_output_metadata_from_result,
    extract_aliases_from_result_data,
)


class TestAliasMapping:
    """Tests for AliasMapping dataclass"""

    def test_alias_mapping_creation(self):
        """Test creation of AliasMapping"""
        mapping = AliasMapping(name="alias1", alias_of="bidder1")
        assert mapping.name == "alias1"
        assert mapping.alias_of == "bidder1"

    def test_alias_mapping_equality(self):
        """Test equality comparison of AliasMapping objects"""
        mapping1 = AliasMapping(name="alias1", alias_of="bidder1")
        mapping2 = AliasMapping(name="alias1", alias_of="bidder1")
        mapping3 = AliasMapping(name="alias2", alias_of="bidder1")

        assert mapping1 == mapping2
        assert mapping1 != mapping3


class TestOutputMetadata:
    """Tests for OutputMetadata dataclass"""

    def test_output_metadata_creation(self):
        """Test creation of OutputMetadata with required fields"""
        metadata = OutputMetadata(
            repository="test/repo",
            version="v1.0.0",
            commit_sha="abc123",
            total_files=10,
            files_with_aliases=5,
        )

        assert metadata.repository == "test/repo"
        assert metadata.version == "v1.0.0"
        assert metadata.commit_sha == "abc123"
        assert metadata.total_files == 10
        assert metadata.files_with_aliases == 5
        assert metadata.files_with_commented_aliases == 0  # Default value

    def test_output_metadata_with_all_fields(self):
        """Test creation of OutputMetadata with all fields"""
        metadata = OutputMetadata(
            repository="test/repo",
            version="v1.0.0",
            commit_sha="abc123",
            total_files=10,
            files_with_aliases=5,
            files_with_commented_aliases=2,
            files_not_in_version=1,
            files_with_empty_aliases=2,
            total_aliases=15,
        )

        assert metadata.files_with_commented_aliases == 2
        assert metadata.files_not_in_version == 1
        assert metadata.files_with_empty_aliases == 2
        assert metadata.total_aliases == 15


class TestOutputFormatter:
    """Tests for OutputFormatter class"""

    @pytest.fixture
    def formatter(self):
        """Create OutputFormatter instance"""
        return OutputFormatter()

    @pytest.fixture
    def sample_aliases(self):
        """Sample alias mappings for testing"""
        return [
            AliasMapping(name="alias1", alias_of="bidder1"),
            AliasMapping(name="alias2", alias_of="bidder1"),
            AliasMapping(name="alias3", alias_of="bidder2"),
        ]

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing"""
        return OutputMetadata(
            repository="test/repo",
            version="v1.0.0",
            commit_sha="abc123def",
            total_files=10,
            files_with_aliases=3,
            files_with_commented_aliases=1,
            files_not_in_version=2,
            files_with_empty_aliases=4,
            total_aliases=3,
        )

    def test_generate_alias_output_file_js_mode(
        self, formatter, sample_aliases, sample_metadata
    ):
        """Test alias output file generation for JS mode"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_path = temp_file.name

        try:
            formatter.generate_alias_output_file(
                temp_path, sample_aliases, sample_metadata, "js"
            )

            # Read and verify content
            with open(temp_path) as f:
                content = f.read()

            # Check headers
            assert "# Prebid.js Alias Mappings" in content
            assert "# Repository: test/repo" in content
            assert "# Version: v1.0.0" in content
            assert "# Generated: abc123def" in content
            assert "# Total Files: 10" in content
            assert "# Files with Aliases: 3" in content
            assert "# Files with Commented Aliases: 1" in content
            assert "# Total Aliases: 3" in content

            # Check alias list
            assert "alias1" in content
            assert "alias2" in content
            assert "alias3" in content

            # Check JSON structure
            assert '"name": "alias1"' in content
            assert '"aliasOf": "bidder1"' in content

        finally:
            Path(temp_path).unlink()

    def test_generate_alias_output_file_server_mode(
        self, formatter, sample_aliases, sample_metadata
    ):
        """Test alias output file generation for server mode"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_path = temp_file.name

        try:
            formatter.generate_alias_output_file(
                temp_path, sample_aliases, sample_metadata, "server"
            )

            with open(temp_path) as f:
                content = f.read()

            # Check title is correct for server mode
            assert "# Prebid Server Alias Mappings" in content
            # Should not have commented aliases line for server mode
            assert "Files with Commented Aliases" not in content

        finally:
            Path(temp_path).unlink()

    def test_generate_alias_output_file_java_server_mode(
        self, formatter, sample_aliases, sample_metadata
    ):
        """Test alias output file generation for Java server mode"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_path = temp_file.name

        try:
            formatter.generate_alias_output_file(
                temp_path, sample_aliases, sample_metadata, "java-server"
            )

            with open(temp_path) as f:
                content = f.read()

            # Check title is correct for Java server mode
            assert "# Prebid Server Java Alias Mappings" in content

        finally:
            Path(temp_path).unlink()

    def test_generate_modules_output_file(self, formatter, sample_metadata):
        """Test modules output file generation"""
        modules_data = {
            "Adapters": ["adapter1", "adapter2", "adapter3"],
            "Analytics": {"analytics1": "description1", "analytics2": "description2"},
            "Core": ["module1", "module2"],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_path = temp_file.name

        try:
            formatter.generate_modules_output_file(
                temp_path, modules_data, sample_metadata
            )

            with open(temp_path) as f:
                content = f.read()

            # Check headers
            assert "# Repository Modules" in content
            assert "# Repository: test/repo" in content
            assert "# Version: v1.0.0" in content

            # Check module categories
            assert "## Adapters" in content
            assert "## Analytics" in content
            assert "## Core" in content

            # Check module items
            assert "- adapter1" in content
            assert "- analytics1: description1" in content
            assert "- module1" in content

            # Check JSON structure
            assert "```json" in content
            assert '"Adapters"' in content

        finally:
            Path(temp_path).unlink()

    def test_format_console_output(self, formatter):
        """Test console output formatting"""
        data = {
            "metadata": {
                "files_with_aliases": 5,
                "files_with_commented_aliases": 2,
                "files_not_in_version": 1,
                "files_with_empty_aliases": 3,
                "total_files": 11,
            }
        }

        result = formatter.format_console_output(data, "js")

        assert "Results:" in result
        assert "Files with aliases: 5" in result
        assert "Files with commented aliases only: 2" in result
        assert "Files not in version: 1" in result
        assert "Files with empty aliases: 3" in result
        assert "Total files: 11" in result
        assert "=" * 60 in result

    def test_format_console_output_non_js_mode(self, formatter):
        """Test console output formatting for non-JS mode"""
        data = {
            "metadata": {
                "files_with_aliases": 3,
                "files_not_in_version": 1,
                "files_with_empty_aliases": 2,
                "total_files": 6,
            }
        }

        result = formatter.format_console_output(data, "server")

        assert "Results:" in result
        assert "Files with aliases: 3" in result
        # Should not have commented aliases for non-JS mode
        assert "commented aliases" not in result


class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_extract_aliases_from_result_data_js_mode(self):
        """Test alias extraction from result data for JS mode"""
        result_data = {
            "file_aliases": {
                "modules/bidder1BidAdapter.js": {"aliases": ["alias1", "alias2"]},
                "modules/bidder2BidAdapter.js": {"aliases": ["alias3"]},
                "modules/bidder3BidAdapter.js": {"aliases": []},  # No aliases
            }
        }

        aliases = extract_aliases_from_result_data(result_data, "js")

        assert len(aliases) == 3
        assert AliasMapping(name="alias1", alias_of="bidder1") in aliases
        assert AliasMapping(name="alias2", alias_of="bidder1") in aliases
        assert AliasMapping(name="alias3", alias_of="bidder2") in aliases

    def test_extract_aliases_from_result_data_server_mode(self):
        """Test alias extraction from result data for server mode"""
        result_data = {
            "file_aliases": {
                "static/bidder-info/alias1.yaml": {
                    "alias_name": "alias1",
                    "alias_of": "bidder1",
                },
                "static/bidder-info/alias2.yaml": {
                    "alias_name": "alias2",
                    "alias_of": "bidder2",
                },
                "static/bidder-info/nobidder.yaml": {
                    "alias_name": None,
                    "alias_of": None,
                },
            }
        }

        aliases = extract_aliases_from_result_data(result_data, "server")

        assert len(aliases) == 2
        assert AliasMapping(name="alias1", alias_of="bidder1") in aliases
        assert AliasMapping(name="alias2", alias_of="bidder2") in aliases

    def test_extract_aliases_from_result_data_java_server_mode(self):
        """Test alias extraction from result data for Java server mode"""
        result_data = {
            "file_aliases": {
                "src/main/resources/bidder-config/bidder1.yaml": {
                    "aliases": ["alias1", "alias2"],
                    "bidder_name": "bidder1",
                },
                "src/main/resources/bidder-config/bidder2.yaml": {
                    "aliases": ["alias3"],
                    "bidder_name": "bidder2",
                },
                "src/main/resources/bidder-config/bidder3.yaml": {
                    "aliases": [],
                    "bidder_name": "bidder3",
                },
            }
        }

        aliases = extract_aliases_from_result_data(result_data, "java-server")

        assert len(aliases) == 3
        assert AliasMapping(name="alias1", alias_of="bidder1") in aliases
        assert AliasMapping(name="alias2", alias_of="bidder1") in aliases
        assert AliasMapping(name="alias3", alias_of="bidder2") in aliases

    def test_create_output_metadata_from_result(self):
        """Test output metadata creation from result data"""
        result_data = {
            "repo": "test/repository",
            "version": "v2.0.0",
            "metadata": {
                "commit_sha": "def456abc",
                "total_files": 15,
                "files_with_aliases": 8,
                "files_with_commented_aliases": 3,
                "files_not_in_version": 2,
                "files_with_empty_aliases": 2,
            },
        }

        metadata = create_output_metadata_from_result(result_data)

        assert metadata.repository == "test/repository"
        assert metadata.version == "v2.0.0"
        assert metadata.commit_sha == "def456abc"
        assert metadata.total_files == 15
        assert metadata.files_with_aliases == 8
        assert metadata.files_with_commented_aliases == 3
        assert metadata.files_not_in_version == 2
        assert metadata.files_with_empty_aliases == 2

    def test_create_output_metadata_from_result_minimal(self):
        """Test output metadata creation with minimal result data"""
        result_data = {"repo": "test/repo", "version": "v1.0.0"}

        metadata = create_output_metadata_from_result(result_data)

        assert metadata.repository == "test/repo"
        assert metadata.version == "v1.0.0"
        assert metadata.commit_sha == ""
        assert metadata.total_files == 0
        assert metadata.files_with_aliases == 0


class TestIntegration:
    """Integration tests for output formatting"""

    def test_end_to_end_alias_file_generation(self):
        """Test complete workflow from result data to file"""
        # Simulate result data from alias finder
        result_data = {
            "repo": "prebid/Prebid.js",
            "version": "v9.0.0",
            "file_aliases": {
                "modules/exampleBidAdapter.js": {
                    "aliases": ["example", "exampleAlias"]
                },
                "modules/testBidAdapter.js": {"aliases": ["test"]},
            },
            "metadata": {
                "commit_sha": "abc123def456",
                "total_files": 2,
                "files_with_aliases": 2,
                "files_with_commented_aliases": 0,
                "files_not_in_version": 0,
                "files_with_empty_aliases": 0,
            },
        }

        # Extract aliases and metadata
        aliases = extract_aliases_from_result_data(result_data, "js")
        metadata = create_output_metadata_from_result(result_data)

        # Generate output file
        formatter = OutputFormatter()

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_path = temp_file.name

        try:
            formatter.generate_alias_output_file(temp_path, aliases, metadata, "js")

            # Verify file contents
            with open(temp_path) as f:
                content = f.read()

            # Verify structure and content
            assert "# Prebid.js Alias Mappings" in content
            assert "# Repository: prebid/Prebid.js" in content
            assert "example" in content
            assert "exampleAlias" in content
            assert "test" in content

            # Verify JSON is valid
            json_start = content.find("```json\n") + 8
            json_end = content.find("\n```", json_start)
            json_content = content[json_start:json_end]

            parsed_json = json.loads(json_content)
            assert len(parsed_json) == 3
            assert all(isinstance(item, dict) for item in parsed_json)
            assert all("name" in item and "aliasOf" in item for item in parsed_json)

        finally:
            Path(temp_path).unlink()
