"""
Media type extraction logic for Prebid.js bid adapters
"""

import re
from typing import Any

from ..shared_utilities import get_logger
from ..shared_utilities.github_client import GitHubClient


class MediaTypeExtractor:
    """Extracts supported media types from Prebid.js bid adapter source code."""

    def __init__(self, github_client: GitHubClient):
        self.github_client = github_client
        self.logger = get_logger(__name__)

    def extract_media_types(
        self, repo_name: str, version: str, specific_adapter: str | None = None
    ) -> dict[str, Any]:
        """
        Extract media types from bid adapters.

        Args:
            repo_name: Repository name (e.g., "prebid/Prebid.js")
            version: Version to analyze
            specific_adapter: Optional specific adapter to analyze

        Returns:
            Dictionary with adapter media type information
        """
        self.logger.info(f"Fetching bid adapters from {repo_name} @ {version}")

        # Fetch bid adapter files
        if specific_adapter:
            # Fetch specific adapter
            adapter_file = f"modules/{specific_adapter}BidAdapter.js"
            try:
                data = self.github_client.fetch_repository_data(
                    repo_name,
                    version,
                    directory=None,
                    modules_path=adapter_file,
                    fetch_strategy="full_content",
                )
                files_data = {adapter_file: data["files"].get(adapter_file, "")}
            except Exception as e:
                self.logger.error(f"Failed to fetch adapter {specific_adapter}: {e}")
                return {"version": version, "adapters": {}, "summary": {}}
        else:
            # Fetch all adapters
            data = self.github_client.fetch_repository_data(
                repo_name,
                version,
                directory="modules",
                fetch_strategy="full_content",
            )
            # Filter to only bid adapters
            files_data = {
                path: content
                for path, content in data["files"].items()
                if path.endswith("BidAdapter.js")
            }

        self.logger.info(f"Found {len(files_data)} bid adapter(s)")

        # Extract media types from each adapter
        adapters_data = {}
        for file_path, content in files_data.items():
            adapter_name = self._extract_adapter_name(file_path)
            if adapter_name and content:
                media_types = self._extract_media_types_from_code(content, adapter_name)
                if media_types:
                    adapters_data[adapter_name] = {
                        "mediaTypes": media_types,
                        "file": file_path,
                    }

        # Generate summary statistics
        summary = self._generate_summary(adapters_data)

        return {
            "version": version,
            "adapters": adapters_data,
            "summary": summary,
            "total_adapters": len(files_data),
            "adapters_with_media_types": len(adapters_data),
        }

    def _extract_adapter_name(self, file_path: str) -> str | None:
        """Extract adapter name from file path."""
        match = re.search(r"/([^/]+)BidAdapter\.js$", file_path)
        return match.group(1) if match else None

    def _extract_media_types_from_code(self, code: str, adapter_name: str) -> list[str]:
        """
        Extract supported media types from adapter code.

        This looks for various patterns indicating media type support:
        1. supportedMediaTypes array
        2. mediaTypes imports from src/mediaTypes.js
        3. References to BANNER, VIDEO, NATIVE, AUDIO constants
        4. isBidRequestValid or buildRequests logic checking mediaTypes
        """
        media_types = set()

        # Pattern 1: Direct supportedMediaTypes declaration
        supported_pattern = r"supportedMediaTypes\s*[:=]\s*\[(.*?)\]"
        match = re.search(supported_pattern, code, re.DOTALL)
        if match:
            types_str = match.group(1)
            # Extract BANNER, VIDEO, NATIVE, AUDIO from the array
            if "BANNER" in types_str:
                media_types.add("banner")
            if "VIDEO" in types_str:
                media_types.add("video")
            if "NATIVE" in types_str:
                media_types.add("native")
            if "AUDIO" in types_str:
                media_types.add("audio")

        # Pattern 2: Import statements from mediaTypes
        import_pattern = (
            r"import\s*\{([^}]+)\}\s*from\s*['\"](?:\.\./)*src/mediaTypes(?:\.js)?['\"]"
        )
        match = re.search(import_pattern, code)
        if match:
            imports = match.group(1)
            if "BANNER" in imports:
                media_types.add("banner")
            if "VIDEO" in imports:
                media_types.add("video")
            if "NATIVE" in imports:
                media_types.add("native")
            if "AUDIO" in imports:
                media_types.add("audio")

        # Pattern 3: Direct references to mediaTypes.banner/video/native/audio
        if re.search(r"mediaTypes\s*\.\s*banner", code, re.IGNORECASE):
            media_types.add("banner")
        if re.search(r"mediaTypes\s*\.\s*video", code, re.IGNORECASE):
            media_types.add("video")
        if re.search(r"mediaTypes\s*\.\s*native", code, re.IGNORECASE):
            media_types.add("native")
        if re.search(r"mediaTypes\s*\.\s*audio", code, re.IGNORECASE):
            media_types.add("audio")

        # Pattern 4: Check for specific media type handling in isBidRequestValid
        if re.search(
            r"isBidRequestValid.*?mediaTypes.*?banner", code, re.DOTALL | re.IGNORECASE
        ):
            media_types.add("banner")
        if re.search(
            r"isBidRequestValid.*?mediaTypes.*?video", code, re.DOTALL | re.IGNORECASE
        ):
            media_types.add("video")
        if re.search(
            r"isBidRequestValid.*?mediaTypes.*?native", code, re.DOTALL | re.IGNORECASE
        ):
            media_types.add("native")
        if re.search(
            r"isBidRequestValid.*?mediaTypes.*?audio", code, re.DOTALL | re.IGNORECASE
        ):
            media_types.add("audio")

        # Pattern 5: Check spec object for supportedMediaTypes
        spec_pattern = (
            r"export\s+const\s+spec\s*=\s*\{([^}]+supportedMediaTypes[^}]+)\}"
        )
        match = re.search(spec_pattern, code, re.DOTALL)
        if match:
            spec_content = match.group(1)
            if "BANNER" in spec_content:
                media_types.add("banner")
            if "VIDEO" in spec_content:
                media_types.add("video")
            if "NATIVE" in spec_content:
                media_types.add("native")
            if "AUDIO" in spec_content:
                media_types.add("audio")

        # If no explicit media types found but adapter exists, check for banner as default
        # Many older adapters only support banner without explicitly declaring it
        if not media_types and adapter_name and len(adapter_name) > 0:
            # Look for bid response handling that suggests banner support
            if re.search(r"\b(width|height|sizes)\b", code, re.IGNORECASE):
                media_types.add("banner")

        return sorted(media_types)

    def _generate_summary(self, adapters_data: dict[str, Any]) -> dict[str, Any]:
        """Generate summary statistics of media type usage."""
        summary: dict[str, Any] = {
            "total_adapters": len(adapters_data),
            "by_media_type": {"banner": 0, "video": 0, "native": 0, "audio": 0},
            "by_combination": {},
        }

        for data in adapters_data.values():
            media_types = data["mediaTypes"]

            # Count individual media types
            for mt in media_types:
                summary["by_media_type"][mt] += 1

            # Count combinations
            combination = ", ".join(sorted(media_types))
            if combination:
                summary["by_combination"][combination] = (
                    summary["by_combination"].get(combination, 0) + 1
                )

        return summary
