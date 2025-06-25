"""
Parser factory for creating repository-specific parsers
"""

from abc import ABC, abstractmethod
from typing import Any

from config import RepoConfig


class BaseParser(ABC):
    """Abstract base class for all parsers."""

    def __init__(self, config: RepoConfig):
        self.config = config

    @abstractmethod
    def parse(self, data: dict[str, Any]) -> str:
        """Parse repository data and return formatted result."""
        pass


class DefaultParser(BaseParser):
    """Default parser that provides basic file listing and content."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse data using default format."""
        result = []
        result.append(f"Repository: {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append(f"Directory: {data['directory']}")
        result.append(f"Total files: {data['metadata']['total_files']}")
        result.append("")

        result.append("Files found:")
        result.append("-" * 40)

        for file_path, content in data["files"].items():
            result.append(f"\n📄 {file_path}")
            result.append("-" * len(file_path))

            # Show first few lines of content
            lines = content.split("\n")
            preview_lines = lines[:10] if len(lines) > 10 else lines
            result.extend(preview_lines)

            if len(lines) > 10:
                result.append(f"... ({len(lines) - 10} more lines)")

        return "\n".join(result)


class MarkdownParser(BaseParser):
    """Parser specifically for markdown documentation."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse markdown files and extract headers/structure."""
        result = []
        result.append(f"# Documentation Structure for {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append("")

        markdown_files = {
            path: content
            for path, content in data["files"].items()
            if path.endswith(".md")
        }

        if not markdown_files:
            result.append("No markdown files found.")
            return "\n".join(result)

        for file_path, content in markdown_files.items():
            result.append(f"## {file_path}")
            result.append("")

            # Extract headers
            headers = self._extract_headers(content)
            if headers:
                for level, header in headers:
                    indent = "  " * (level - 1)
                    result.append(f"{indent}- {header}")
            else:
                result.append("No headers found.")
            result.append("")

        return "\n".join(result)

    def _extract_headers(self, content: str) -> list:
        """Extract markdown headers with their levels."""
        headers = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                header_text = line.lstrip("# ").strip()
                if header_text:
                    headers.append((level, header_text))
        return headers


class OpenAPIParser(BaseParser):
    """Parser for OpenAPI/Swagger specifications."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse OpenAPI specs and extract API information."""
        result = []
        result.append(f"# API Specifications for {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append("")

        # Look for common OpenAPI file patterns
        api_files = {
            path: content
            for path, content in data["files"].items()
            if any(
                pattern in path.lower()
                for pattern in ["openapi", "swagger", ".yaml", ".yml", ".json"]
            )
        }

        if not api_files:
            result.append("No API specification files found.")
            return "\n".join(result)

        for file_path, content in api_files.items():
            result.append(f"## {file_path}")
            result.append("")

            # Basic content analysis for API specs
            if "openapi:" in content or "swagger:" in content:
                result.append("✅ OpenAPI/Swagger specification detected")

                # Extract basic info
                lines = content.split("\n")
                for line in lines[:20]:  # Check first 20 lines
                    line = line.strip()
                    if line.startswith("title:"):
                        result.append(f"Title: {line.split(':', 1)[1].strip()}")
                    elif line.startswith("version:"):
                        result.append(f"Version: {line.split(':', 1)[1].strip()}")
                    elif line.startswith("description:"):
                        result.append(f"Description: {line.split(':', 1)[1].strip()}")
            else:
                result.append("File type not clearly identified as OpenAPI spec")

            result.append("")

        return "\n".join(result)


class ParserFactory:
    """Factory for creating appropriate parsers based on configuration."""

    _parsers = {
        "default": DefaultParser,
        "markdown": MarkdownParser,
        "openapi": OpenAPIParser,
    }

    def get_parser(self, config: RepoConfig) -> BaseParser:
        """Get appropriate parser for the given configuration."""
        parser_class = self._parsers.get(config.parser_type, DefaultParser)
        return parser_class(config)

    def register_parser(self, parser_type: str, parser_class: type) -> None:
        """Register a new parser type."""
        if not issubclass(parser_class, BaseParser):
            raise ValueError("Parser class must inherit from BaseParser")
        self._parsers[parser_type] = parser_class

    def get_available_parsers(self) -> list:
        """Get list of available parser types."""
        return list(self._parsers.keys())
