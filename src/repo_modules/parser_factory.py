"""
Parser factory for creating repository-specific parsers
"""

from abc import ABC, abstractmethod
from typing import Any

from .config import RepoConfig


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


class PrebidJSParser(BaseParser):
    """Parser specifically for Prebid.js modules directory to categorize adapters."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse Prebid.js modules and categorize by adapter type."""
        result = []
        result.append(f"Repository: {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append(f"Modules Directory: {data['directory']}")
        result.append("")

        # Categorize modules
        modules = self._categorize_modules(data["files"])

        # Display categories
        result.append("Prebid.js Module Categories:")
        result.append("=" * 40)
        result.append("")

        for category, files in modules.items():
            if files:
                result.append(
                    f"📦 {category.replace('_', ' ').title()} ({len(files)}):"
                )
                result.append("-" * 30)
                for file in sorted(files):
                    result.append(f"{file}")
                result.append("")

        # Add JSON output
        result.append("JSON Output:")
        result.append("-" * 20)
        import json

        result.append(json.dumps(modules, indent=2))

        return "\n".join(result)

    def _categorize_modules(self, files: dict[str, str]) -> dict[str, list[str]]:
        """Categorize .js files by adapter type."""
        categories: dict[str, list[str]] = {
            "bid_adapters": [],
            "analytics_adapters": [],
            "rtd_modules": [],
            "identity_modules": [],
            "other_modules": [],
        }

        for file_path, _ in files.items():
            # Only process .js files in the root of modules directory
            if not file_path.endswith(".js"):
                continue

            # Extract just the filename without path
            filename = file_path.split("/")[-1]

            # Skip if it's in a subdirectory (we only want root level files)
            if "/" in file_path.replace("modules/", ""):
                continue

            # Categorize based on filename patterns
            if filename.endswith("BidAdapter.js"):
                adapter_name = filename.replace("BidAdapter.js", "")
                categories["bid_adapters"].append(adapter_name)
            elif filename.endswith("AnalyticsAdapter.js"):
                adapter_name = filename.replace("AnalyticsAdapter.js", "")
                categories["analytics_adapters"].append(adapter_name)
            elif filename.endswith("RtdProvider.js"):
                module_name = filename.replace("RtdProvider.js", "")
                categories["rtd_modules"].append(module_name)
            elif filename.endswith("IdSystem.js"):
                system_name = filename.replace("IdSystem.js", "")
                categories["identity_modules"].append(system_name)
            else:
                # Other .js modules
                module_name = filename.replace(".js", "")
                categories["other_modules"].append(module_name)

        return categories


class PrebidServerGoParser(BaseParser):
    """Parser specifically for Prebid Server Go implementation to categorize adapters and modules."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse Prebid Server Go directories and categorize by type."""
        result = []
        result.append(f"Repository: {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append("")

        # Parse each configured path
        all_categories = {}
        paths = self.config.paths or {}

        for category_name, path in paths.items():
            path_data = data.get("paths", {}).get(path, {})
            if path_data:
                categories = self._categorize_by_path(category_name, path, path_data)
                all_categories.update(categories)

        # Display categories
        result.append("Prebid Server Go Categories:")
        result.append("=" * 40)
        result.append("")

        for category, items in all_categories.items():
            if items:
                result.append(f"📦 {category} ({len(items)}):")
                result.append("-" * 30)
                for item in sorted(items):
                    result.append(f"{item}")
                result.append("")

        # Add JSON output
        result.append("JSON Output:")
        result.append("-" * 20)
        import json

        result.append(json.dumps(all_categories, indent=2))

        return "\n".join(result)

    def _categorize_by_path(
        self, category_name: str, path: str, files: dict[str, str]
    ) -> dict[str, list[str]]:
        """Categorize items based on the path type."""
        categories: dict[str, list[str]] = {}

        if category_name == "Bid Adapters":
            # For adapters path, get directory names (subdirectories of adapters/)
            adapters = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 1:  # Should be like "adapters/33across"
                    adapter_name = parts[1]  # Get the adapter name, not "adapters"
                    # Convert underscores to spaces
                    adapter_name = adapter_name.replace("_", " ")
                    adapters.add(adapter_name)
            categories["Bid Adapters"] = list(adapters)

        elif category_name == "Analytics Adapters":
            # For analytics path, get directory names excluding specified ones
            excluded = {"build", "clients", "filesystem"}
            analytics = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 1:  # Should be like "analytics/pubstack"
                    adapter_name = parts[1]  # Get the adapter name, not "analytics"
                    if adapter_name not in excluded:
                        # Convert underscores to spaces
                        adapter_name = adapter_name.replace("_", " ")
                        analytics.add(adapter_name)
            categories["Analytics Adapters"] = list(analytics)

        elif category_name == "General Modules":
            # For modules path, get directories with subdirectories and combine names
            modules = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                # Only include paths that have at least 3 levels (modules/dir/subdir)
                # This ensures we only get directories that have subdirectories
                if len(parts) >= 3:
                    # Combine first two directory levels after "modules"
                    # e.g., "modules/fiftyonedegrees/devicedetection" -> "fiftyonedegrees devicedetection"
                    module_name = f"{parts[1]} {parts[2]}"
                    modules.add(module_name)
            categories["General Modules"] = list(modules)

        return categories


class PrebidServerJavaParser(BaseParser):
    """Parser specifically for Prebid Server Java implementation to categorize adapters and modules."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse Prebid Server Java directories and categorize by type."""
        result = []
        result.append(f"Repository: {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append("")

        # Parse each configured path
        all_categories = {}
        paths = self.config.paths or {}

        for category_name, path in paths.items():
            path_data = data.get("paths", {}).get(path, {})
            if path_data:
                categories = self._categorize_by_path(category_name, path, path_data)
                all_categories.update(categories)

        # Display categories
        result.append("Prebid Server Java Categories:")
        result.append("=" * 40)
        result.append("")

        for category, items in all_categories.items():
            if items:
                result.append(f"📦 {category} ({len(items)}):")
                result.append("-" * 30)
                for item in sorted(items):
                    result.append(f"{item}")
                result.append("")

        # Add JSON output
        result.append("JSON Output:")
        result.append("-" * 20)
        import json

        result.append(json.dumps(all_categories, indent=2))

        return "\n".join(result)

    def _categorize_by_path(
        self, category_name: str, path: str, files: dict[str, str]
    ) -> dict[str, list[str]]:
        """Categorize items based on the path type."""
        categories: dict[str, list[str]] = {}

        if category_name == "Bid Adapters":
            # For bidder path, get directory names (subdirectories of bidder/)
            adapters = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if (
                    len(parts) > 1
                ):  # Should be like "src/main/java/org/prebid/server/bidder/adapter_name"
                    adapter_name = parts[-1]  # Get the last part (adapter name)
                    adapters.add(adapter_name)
            categories["Bid Adapters"] = list(adapters)

        elif category_name == "Analytics Adapters":
            # For analytics path, get directory names excluding specified ones
            excluded = {"log"}
            analytics = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if (
                    len(parts) > 1
                ):  # Should be like "src/main/java/org/prebid/server/analytics/reporter/adapter_name"
                    adapter_name = parts[-1]  # Get the last part (adapter name)
                    if adapter_name not in excluded:
                        analytics.add(adapter_name)
            categories["Analytics Adapters"] = list(analytics)

        elif category_name == "General Modules":
            # For modules path, get directory names and format them
            modules = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 1:  # Should be like "extra/modules/module_name"
                    module_name = parts[-1]  # Get the last part (module name)
                    # Replace `-` with space
                    formatted_name = module_name.replace("-", " ")
                    # Remove "pb-" prefix if present
                    if formatted_name.startswith("pb "):
                        formatted_name = formatted_name[3:]  # Remove "pb "
                    modules.add(formatted_name)
            categories["General Modules"] = list(modules)

        elif category_name == "Privacy Modules":
            # For privacy path, get directory names
            privacy = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if (
                    len(parts) > 1
                ):  # Should be like "src/main/java/org/prebid/server/activity/infrastructure/privacy/module_name"
                    module_name = parts[-1]  # Get the last part (module name)
                    privacy.add(module_name)
            categories["Privacy Modules"] = list(privacy)

        return categories


class PrebidDocsParser(BaseParser):
    """Parser specifically for Prebid Documentation site to categorize adapters and modules from documentation files."""

    def parse(self, data: dict[str, Any]) -> str:
        """Parse Prebid Documentation files and categorize by type."""
        result = []
        result.append(f"Repository: {data['repo']}")
        result.append(f"Version: {data['version']}")
        result.append("")

        # Parse each configured path
        all_categories = {}
        paths = self.config.paths or {}

        for category_name, path in paths.items():
            path_data = data.get("paths", {}).get(path, {})
            if path_data:
                categories = self._categorize_by_path(category_name, path, path_data)
                all_categories.update(categories)

        # Display categories
        result.append("Prebid Documentation Categories:")
        result.append("=" * 40)
        result.append("")

        for category, items in all_categories.items():
            if items:
                result.append(f"📦 {category} ({len(items)}):")
                result.append("-" * 30)
                for item in sorted(items):
                    result.append(f"{item}")
                result.append("")

        # Add JSON output
        result.append("JSON Output:")
        result.append("-" * 20)
        import json

        result.append(json.dumps(all_categories, indent=2))

        return "\n".join(result)

    def _categorize_by_path(
        self, category_name: str, path: str, files: dict[str, str]
    ) -> dict[str, list[str]]:
        """Categorize items based on the path type."""
        categories: dict[str, list[str]] = {}

        if category_name == "Bid Adapters":
            # For bidders path, get file names (remove .md extension)
            adapters = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 0:
                    file_name = parts[-1]  # Get the file name
                    if file_name.endswith(".md"):
                        adapter_name = file_name[:-3]  # Remove .md extension
                        adapters.add(adapter_name)
            categories["Bid Adapters"] = list(adapters)

        elif category_name == "Analytics Adapters":
            # Handle analytics adapters from different paths
            analytics = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 0:
                    file_name = parts[-1]  # Get the file name
                    if file_name.endswith(".md"):
                        base_name = file_name[:-3]  # Remove .md extension

                        # Handle different analytics adapter types based on path
                        if path == "dev-docs/modules" and base_name.endswith(
                            "AnalyticsAdapter"
                        ):
                            # For modules path, remove AnalyticsAdapter suffix
                            clean_name = base_name[:-16]  # Remove "AnalyticsAdapter"
                            analytics.add(clean_name)
                        elif path != "dev-docs/modules":
                            # For dedicated analytics path, use the base name as-is
                            analytics.add(base_name)

            if analytics:
                categories["Analytics Adapters"] = list(analytics)

        elif category_name == "Identity Modules":
            # For userid-submodules path, get file names (remove .md extension)
            identity = set()
            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 0:
                    file_name = parts[-1]  # Get the file name
                    if file_name.endswith(".md"):
                        module_name = file_name[:-3]  # Remove .md extension
                        identity.add(module_name)
            categories["Identity Modules"] = list(identity)

        elif (
            category_name
            in ["Real-Time Data Modules", "Video Modules", "Other Modules"]
            and path == "dev-docs/modules"
        ):
            # For modules path, categorize by file endings
            rtd_modules = set()
            video_modules = set()
            other_modules = set()

            for file_path in files.keys():
                parts = file_path.split("/")
                if len(parts) > 0:
                    file_name = parts[-1]  # Get the file name
                    if file_name.endswith(".md"):
                        base_name = file_name[:-3]  # Remove .md extension

                        # Remove redundant endings and categorize
                        if base_name.endswith("RtdProvider"):
                            clean_name = base_name[:-11]  # Remove "RtdProvider"
                            rtd_modules.add(clean_name)
                        elif base_name.endswith("VideoProvider"):
                            clean_name = base_name[:-13]  # Remove "VideoProvider"
                            video_modules.add(clean_name)
                        else:
                            other_modules.add(base_name)

            # Only add categories that have items and match the current category being processed
            if category_name == "Real-Time Data Modules" and rtd_modules:
                categories["Real-Time Data Modules"] = list(rtd_modules)
            elif category_name == "Video Modules" and video_modules:
                categories["Video Modules"] = list(video_modules)
            elif category_name == "Other Modules" and other_modules:
                categories["Other Modules"] = list(other_modules)

        return categories


class ParserFactory:
    """Factory for creating appropriate parsers based on configuration."""

    _parsers = {
        "default": DefaultParser,
        "markdown": MarkdownParser,
        "openapi": OpenAPIParser,
        "prebid_js": PrebidJSParser,
        "prebid_server_go": PrebidServerGoParser,
        "prebid_server_java": PrebidServerJavaParser,
        "prebid_docs": PrebidDocsParser,
    }

    def get_parser(self, config: RepoConfig) -> BaseParser:
        """Get appropriate parser for the given configuration."""
        parser_class = self._parsers.get(config.parser_type, DefaultParser)
        return parser_class(config)  # type: ignore[abstract]

    def register_parser(self, parser_type: str, parser_class: type[BaseParser]) -> None:
        """Register a new parser type."""
        if not issubclass(parser_class, BaseParser):
            raise ValueError("Parser class must inherit from BaseParser")
        self._parsers[parser_type] = parser_class

    def get_available_parsers(self) -> list:
        """Get list of available parser types."""
        return list(self._parsers.keys())
