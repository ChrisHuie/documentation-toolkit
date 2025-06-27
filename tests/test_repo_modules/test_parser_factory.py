"""
Tests for the parser_factory module.
"""

import pytest

from src.repo_modules_by_version.config import RepoConfig
from src.repo_modules_by_version.parser_factory import (
    BaseParser,
    DefaultParser,
    MarkdownParser,
    OpenAPIParser,
    ParserFactory,
)


class TestBaseParser:
    """Test BaseParser abstract class."""

    def test_base_parser_is_abstract(self):
        """Test that BaseParser cannot be instantiated directly."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test",
            versions=["v1.0.0"],
        )

        with pytest.raises(TypeError):
            BaseParser(config)  # type: ignore[abstract]

    def test_base_parser_subclass_implementation(self):
        """Test that subclasses must implement parse method."""

        class IncompleteParser(BaseParser):
            pass

        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test",
            versions=["v1.0.0"],
        )

        with pytest.raises(TypeError):
            IncompleteParser(config)  # type: ignore[abstract]


class TestDefaultParser:
    """Test DefaultParser implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=["v1.0.0"],
            parser_type="default",
        )
        self.parser = DefaultParser(self.config)

    def test_default_parser_initialization(self):
        """Test DefaultParser can be initialized."""
        assert isinstance(self.parser, DefaultParser)
        assert self.parser.config == self.config

    def test_default_parser_parse_output_format(self, sample_github_data):
        """Test DefaultParser produces correctly formatted output."""
        result = self.parser.parse(sample_github_data)

        assert "Repository: test/repo" in result
        assert "Version: v1.0.0" in result
        assert "Directory: docs" in result
        assert "Total files: 2" in result
        assert "📄 docs/README.md" in result
        assert "📄 docs/api.md" in result

    def test_default_parser_handles_long_files(self):
        """Test DefaultParser truncates long files appropriately."""
        long_content = "\n".join([f"Line {i}" for i in range(20)])
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {"docs/long.md": long_content},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)
        assert "... (10 more lines)" in result

    def test_default_parser_handles_short_files(self):
        """Test DefaultParser shows all content for short files."""
        short_content = "\n".join([f"Line {i}" for i in range(5)])
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {"docs/short.md": short_content},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)
        assert "... (0 more lines)" not in result
        assert "Line 4" in result


class TestMarkdownParser:
    """Test MarkdownParser implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test repository",
            versions=["v1.0.0"],
            parser_type="markdown",
        )
        self.parser = MarkdownParser(self.config)

    def test_markdown_parser_initialization(self):
        """Test MarkdownParser can be initialized."""
        assert isinstance(self.parser, MarkdownParser)
        assert self.parser.config == self.config

    def test_markdown_parser_filters_markdown_files(self, sample_github_data):
        """Test MarkdownParser only processes .md files."""
        data = sample_github_data.copy()
        data["files"]["docs/config.yaml"] = "key: value"

        result = self.parser.parse(data)

        assert "docs/README.md" in result
        assert "docs/api.md" in result
        assert "docs/config.yaml" not in result

    def test_markdown_parser_extracts_headers(self):
        """Test MarkdownParser correctly extracts headers."""
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {
                "docs/test.md": "# Main Title\n## Subtitle\n### Sub-subtitle\nContent here\n## Another Section"
            },
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)

        assert "- Main Title" in result
        assert "  - Subtitle" in result
        assert "    - Sub-subtitle" in result
        assert "  - Another Section" in result

    def test_markdown_parser_handles_no_markdown_files(self):
        """Test MarkdownParser handles repositories without markdown files."""
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {"docs/config.yaml": "key: value"},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)
        assert "No markdown files found." in result

    def test_extract_headers_with_various_formats(self):
        """Test header extraction with different markdown formats."""
        content = """
# Header 1
## Header 2
###Header 3 No Space
#### Header 4
#####
######  Header 6 Multiple Spaces
####### Invalid Header 7
Not a header
        """

        headers = self.parser._extract_headers(content)

        expected = [
            (1, "Header 1"),
            (2, "Header 2"),
            (3, "Header 3 No Space"),
            (4, "Header 4"),
            (6, "Header 6 Multiple Spaces"),
            (7, "Invalid Header 7"),
        ]

        assert headers == expected


class TestOpenAPIParser:
    """Test OpenAPIParser implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RepoConfig(
            repo="test/repo",
            directory="openapi",
            description="API repository",
            versions=["v1.0.0"],
            parser_type="openapi",
        )
        self.parser = OpenAPIParser(self.config)

    def test_openapi_parser_initialization(self):
        """Test OpenAPIParser can be initialized."""
        assert isinstance(self.parser, OpenAPIParser)
        assert self.parser.config == self.config

    def test_openapi_parser_identifies_api_files(self):
        """Test OpenAPIParser identifies API specification files."""
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "openapi",
            "files": {
                "openapi/api.yaml": "openapi: 3.0.0\ntitle: Test API",
                "openapi/swagger.json": '{"swagger": "2.0", "info": {"title": "Test"}}',
                "openapi/readme.md": "# API Documentation",
            },
            "metadata": {"commit_sha": "abc123", "total_files": 3},
        }

        result = self.parser.parse(data)

        assert "openapi/api.yaml" in result
        assert "openapi/swagger.json" in result
        assert "openapi/readme.md" in result  # .md files contain openapi patterns

    def test_openapi_parser_extracts_spec_info(self):
        """Test OpenAPIParser extracts specification information."""
        spec_content = """
openapi: 3.0.0
info:
  title: My Test API
  version: 1.2.3
  description: This is a test API
servers:
  - url: https://api.example.com
        """

        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "openapi",
            "files": {"openapi/spec.yaml": spec_content},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)

        assert "✅ OpenAPI/Swagger specification detected" in result
        assert "Title: My Test API" in result
        assert "Version: 1.2.3" in result
        assert "Description: This is a test API" in result

    def test_openapi_parser_handles_no_api_files(self):
        """Test OpenAPIParser handles repositories without API files."""
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "docs",
            "files": {"docs/readme.md": "# Documentation"},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)
        assert "No API specification files found." in result

    def test_openapi_parser_handles_unidentified_files(self):
        """Test OpenAPIParser handles files that don't match API patterns."""
        data = {
            "repo": "test/repo",
            "version": "v1.0.0",
            "directory": "openapi",
            "files": {"openapi/config.yaml": "database: postgres"},
            "metadata": {"commit_sha": "abc123", "total_files": 1},
        }

        result = self.parser.parse(data)
        assert "File type not clearly identified as OpenAPI spec" in result


class TestParserFactory:
    """Test ParserFactory implementation."""

    def test_parser_factory_get_default_parser(self, sample_repo_config):
        """Test ParserFactory returns DefaultParser for default type."""
        factory = ParserFactory()
        parser = factory.get_parser(sample_repo_config)

        assert isinstance(parser, DefaultParser)

    def test_parser_factory_get_markdown_parser(self):
        """Test ParserFactory returns MarkdownParser for markdown type."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test",
            versions=["v1.0.0"],
            parser_type="markdown",
        )

        factory = ParserFactory()
        parser = factory.get_parser(config)

        assert isinstance(parser, MarkdownParser)

    def test_parser_factory_get_openapi_parser(self):
        """Test ParserFactory returns OpenAPIParser for openapi type."""
        config = RepoConfig(
            repo="test/repo",
            directory="openapi",
            description="Test",
            versions=["v1.0.0"],
            parser_type="openapi",
        )

        factory = ParserFactory()
        parser = factory.get_parser(config)

        assert isinstance(parser, OpenAPIParser)

    def test_parser_factory_fallback_to_default(self):
        """Test ParserFactory falls back to DefaultParser for unknown types."""
        config = RepoConfig(
            repo="test/repo",
            directory="docs",
            description="Test",
            versions=["v1.0.0"],
            parser_type="unknown_type",
        )

        factory = ParserFactory()
        parser = factory.get_parser(config)

        assert isinstance(parser, DefaultParser)

    def test_parser_factory_register_custom_parser(self, sample_repo_config):
        """Test ParserFactory can register custom parsers."""

        class CustomParser(BaseParser):
            def parse(self, data):
                return "Custom parser output"

        factory = ParserFactory()
        factory.register_parser("custom", CustomParser)

        # Verify it's registered
        assert "custom" in factory.get_available_parsers()

        # Test getting the custom parser
        sample_repo_config.parser_type = "custom"
        parser = factory.get_parser(sample_repo_config)

        assert isinstance(parser, CustomParser)

    def test_parser_factory_register_invalid_parser(self):
        """Test ParserFactory rejects invalid parser classes."""

        class InvalidParser:  # Doesn't inherit from BaseParser
            pass

        factory = ParserFactory()

        with pytest.raises(
            ValueError, match="Parser class must inherit from BaseParser"
        ):
            factory.register_parser("invalid", InvalidParser)

    def test_parser_factory_get_available_parsers(self):
        """Test ParserFactory returns list of available parser types."""
        factory = ParserFactory()
        parsers = factory.get_available_parsers()

        assert isinstance(parsers, list)
        assert "default" in parsers
        assert "markdown" in parsers
        assert "openapi" in parsers
