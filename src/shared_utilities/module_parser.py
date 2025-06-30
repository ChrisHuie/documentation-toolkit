"""
Shared module parser for consistent module categorization across all tools.

This module provides a unified way to parse and categorize modules from various
repository types (Prebid.js, Prebid Server Go/Java, etc.) ensuring consistency
across all tools in the documentation toolkit.
"""

from collections import defaultdict
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


class ModuleInfo:
    """Information about a parsed module."""

    def __init__(self, name: str, path: str, category: str, repo: str):
        self.name = name
        self.path = path
        self.category = category
        self.repo = repo

    def __eq__(self, other):
        if not isinstance(other, ModuleInfo):
            return False
        return (
            self.name == other.name
            and self.category == other.category
            and self.repo == other.repo
        )

    def __hash__(self):
        return hash((self.name, self.category, self.repo))

    def __repr__(self):
        return f"ModuleInfo(name='{self.name}', category='{self.category}', repo='{self.repo}')"


class ModuleParser:
    """Unified module parser for all repository types."""

    def parse_modules(
        self,
        repo_data: dict[str, Any],
        parser_type: str,
        repo_key: str,
        paths_config: dict[str, str] | None = None,
    ) -> dict[str, list[ModuleInfo]]:
        """
        Parse modules from repository data based on parser type.

        Args:
            repo_data: Repository data from GitHub client
            parser_type: Type of parser to use (e.g., 'prebid_js', 'prebid_server_go')
            repo_key: Repository identifier/key
            paths_config: Optional paths configuration for the repository

        Returns:
            Dictionary mapping category names to lists of ModuleInfo objects
        """
        if parser_type == "prebid_js":
            return self._parse_prebid_js(repo_data, repo_key)
        elif parser_type == "prebid_server_go":
            return self._parse_prebid_server_go(repo_data, repo_key, paths_config)
        elif parser_type == "prebid_server_java":
            return self._parse_prebid_server_java(repo_data, repo_key, paths_config)
        elif parser_type == "prebid_docs":
            return self._parse_prebid_docs(repo_data, repo_key, paths_config)
        else:
            # Default parser - just extract all files without categorization
            return self._parse_default(repo_data, repo_key)

    def _parse_prebid_js(
        self, repo_data: dict[str, Any], repo_key: str
    ) -> dict[str, list[ModuleInfo]]:
        """Parse Prebid.js modules with proper categorization."""
        categories: defaultdict[str, list[ModuleInfo]] = defaultdict(list)

        # Handle multi-path structure
        if "paths" in repo_data:
            paths_data = repo_data["paths"]
            modules_path_data = paths_data.get("modules", {})
        else:
            # Legacy structure
            modules_path_data = repo_data.get("files", {})

        # Track modules by name to handle .js/.ts duplicates
        seen_modules = {}

        for file_path, _ in modules_path_data.items():
            # Process both .js and .ts files
            if not (file_path.endswith(".js") or file_path.endswith(".ts")):
                continue

            # Skip TypeScript declaration files
            if file_path.endswith(".d.ts"):
                continue

            # Extract filename without path
            filename = file_path.split("/")[-1]

            # Skip if it's in a subdirectory (we only want root level files)
            # Check if there are any slashes after removing the initial "modules/" part
            relative_path = file_path.replace("modules/", "", 1)
            if "/" in relative_path:
                continue

            # Remove .js or .ts extension to get base filename
            if filename.endswith(".ts"):
                base_filename = filename[:-3]
            elif filename.endswith(".js"):
                base_filename = filename[:-3]
            else:
                base_filename = filename

            # Categorize based on filename patterns
            category = None
            module_name = None

            if base_filename.endswith("BidAdapter"):
                module_name = base_filename[:-10]  # Remove "BidAdapter"
                category = "Bid Adapters"
                # Skip if module name is empty
                if not module_name:
                    continue
            elif base_filename.endswith("AnalyticsAdapter"):
                module_name = base_filename[:-16]  # Remove "AnalyticsAdapter"
                category = "Analytics Adapters"
                # Skip if module name is empty
                if not module_name:
                    continue
            elif base_filename.endswith("RtdProvider"):
                module_name = base_filename[:-11]  # Remove "RtdProvider"
                category = "Real-Time Data Modules"
                if not module_name:
                    continue
            elif base_filename.endswith("IdSystem"):
                module_name = base_filename[:-8]  # Remove "IdSystem"
                category = "User ID Modules"
                if not module_name:
                    continue
            else:
                # Other modules
                module_name = base_filename
                category = "Other Modules"
                if not module_name:
                    continue

            # Create unique key for deduplication (name + category)
            module_key = (module_name, category)

            # Only add if we haven't seen this module yet, or if this is a .ts file
            # (prefer .ts over .js for the same module)
            if module_key not in seen_modules or file_path.endswith(".ts"):
                module = ModuleInfo(
                    name=module_name,
                    path=file_path,
                    category=category,
                    repo=repo_key,
                )
                seen_modules[module_key] = module

        # Convert seen_modules dict to categories dict
        for module in seen_modules.values():
            categories[module.category].append(module)

        return dict(categories)

    def _parse_prebid_server_go(
        self,
        repo_data: dict[str, Any],
        repo_key: str,
        paths_config: dict[str, str] | None = None,
    ) -> dict[str, list[ModuleInfo]]:
        """Parse Prebid Server Go modules."""
        categories: defaultdict[str, list[ModuleInfo]] = defaultdict(list)

        if "paths" not in repo_data:
            return dict(categories)

        paths_data = repo_data["paths"]

        # Use paths_config to map paths to categories
        if not paths_config:
            paths_config = {
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            }

        for category_name, path in paths_config.items():
            path_data = paths_data.get(path, {})

            if category_name == "Bid Adapters" and path_data:
                # Get directory names from adapters/
                adapters = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 1:  # e.g., "adapters/33across/..."
                        adapter_name = parts[1]
                        adapters.add(adapter_name)

                for adapter_name in adapters:
                    module = ModuleInfo(
                        name=adapter_name,
                        path=f"{path}/{adapter_name}",
                        category="Bid Adapters",
                        repo=repo_key,
                    )
                    categories["Bid Adapters"].append(module)

            elif category_name == "Analytics Adapters" and path_data:
                # Get directory names from analytics/, excluding some
                excluded = {"build", "clients", "filesystem"}
                analytics = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 1:
                        adapter_name = parts[1]
                        if adapter_name not in excluded:
                            analytics.add(adapter_name)

                for adapter_name in analytics:
                    module = ModuleInfo(
                        name=adapter_name,
                        path=f"{path}/{adapter_name}",
                        category="Analytics Adapters",
                        repo=repo_key,
                    )
                    categories["Analytics Adapters"].append(module)

            elif category_name == "General Modules" and path_data:
                # Get modules with subdirectories
                modules = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) >= 3:  # e.g., "modules/prebid/ortb2blocking"
                        # Combine module and submodule
                        module_name = f"{parts[1]}/{parts[2]}"
                        modules.add(module_name)

                for module_name in modules:
                    module = ModuleInfo(
                        name=module_name.replace("/", "_"),
                        path=f"{path}/{module_name}",
                        category="General Modules",
                        repo=repo_key,
                    )
                    categories["General Modules"].append(module)

        return dict(categories)

    def _parse_prebid_server_java(
        self,
        repo_data: dict[str, Any],
        repo_key: str,
        paths_config: dict[str, str] | None = None,
    ) -> dict[str, list[ModuleInfo]]:
        """Parse Prebid Server Java modules."""
        categories: defaultdict[str, list[ModuleInfo]] = defaultdict(list)

        if "paths" not in repo_data:
            return dict(categories)

        paths_data = repo_data["paths"]

        # Use paths_config to map paths to categories
        if not paths_config:
            paths_config = {
                "Bid Adapters": "src/main/java/org/prebid/server/bidder",
                "Analytics Adapters": "src/main/java/org/prebid/server/analytics/reporter",
                "General Modules": "extra/modules",
                "Privacy Modules": "src/main/java/org/prebid/server/activity/infrastructure/privacy",
            }

        for category_name, path in paths_config.items():
            path_data = paths_data.get(path, {})

            if category_name == "Bid Adapters" and path_data:
                # Get the last directory name as adapter name
                adapters = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 0:
                        adapter_name = parts[-1]
                        adapters.add(adapter_name)

                for adapter_name in adapters:
                    module = ModuleInfo(
                        name=adapter_name,
                        path=f"{path}/{adapter_name}",
                        category="Bid Adapters",
                        repo=repo_key,
                    )
                    categories["Bid Adapters"].append(module)

            elif category_name == "Analytics Adapters" and path_data:
                excluded = {"log"}
                analytics = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 0:
                        adapter_name = parts[-1]
                        if adapter_name not in excluded:
                            analytics.add(adapter_name)

                for adapter_name in analytics:
                    module = ModuleInfo(
                        name=adapter_name,
                        path=f"{path}/{adapter_name}",
                        category="Analytics Adapters",
                        repo=repo_key,
                    )
                    categories["Analytics Adapters"].append(module)

            elif category_name == "General Modules" and path_data:
                modules = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 0:
                        module_name = parts[-1]
                        # Remove "pb-" prefix if present
                        if module_name.startswith("pb-"):
                            module_name = module_name[3:]
                        modules.add(module_name)

                for module_name in modules:
                    module = ModuleInfo(
                        name=module_name,
                        path=f"{path}/{module_name}",
                        category="General Modules",
                        repo=repo_key,
                    )
                    categories["General Modules"].append(module)

            elif category_name == "Privacy Modules" and path_data:
                privacy = set()
                for file_path in path_data.keys():
                    parts = file_path.split("/")
                    if len(parts) > 0:
                        module_name = parts[-1]
                        privacy.add(module_name)

                for module_name in privacy:
                    module = ModuleInfo(
                        name=module_name,
                        path=f"{path}/{module_name}",
                        category="Privacy Modules",
                        repo=repo_key,
                    )
                    categories["Privacy Modules"].append(module)

        return dict(categories)

    def _parse_prebid_docs(
        self,
        repo_data: dict[str, Any],
        repo_key: str,
        paths_config: dict[str, str] | None = None,
    ) -> dict[str, list[ModuleInfo]]:
        """Parse Prebid documentation site modules."""
        categories: defaultdict[str, list[ModuleInfo]] = defaultdict(list)

        if "paths" not in repo_data:
            return dict(categories)

        paths_data = repo_data["paths"]

        # Use paths_config to map paths to categories
        if not paths_config:
            paths_config = {
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "User ID Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            }

        for category_name, path in paths_config.items():
            path_data = paths_data.get(path, {})

            if category_name == "Bid Adapters" and path_data:
                for file_path in path_data.keys():
                    if file_path.endswith(".md"):
                        filename = file_path.split("/")[-1]
                        adapter_name = filename[:-3]  # Remove .md
                        module = ModuleInfo(
                            name=adapter_name,
                            path=file_path,
                            category="Bid Adapters",
                            repo=repo_key,
                        )
                        categories["Bid Adapters"].append(module)

            elif category_name == "Analytics Adapters" and path_data:
                for file_path in path_data.keys():
                    if file_path.endswith(".md"):
                        filename = file_path.split("/")[-1]
                        adapter_name = filename[:-3]  # Remove .md
                        module = ModuleInfo(
                            name=adapter_name,
                            path=file_path,
                            category="Analytics Adapters",
                            repo=repo_key,
                        )
                        categories["Analytics Adapters"].append(module)

            elif category_name == "User ID Modules" and path_data:
                for file_path in path_data.keys():
                    if file_path.endswith(".md"):
                        filename = file_path.split("/")[-1]
                        module_name = filename[:-3]  # Remove .md
                        module = ModuleInfo(
                            name=module_name,
                            path=file_path,
                            category="User ID Modules",
                            repo=repo_key,
                        )
                        categories["User ID Modules"].append(module)

            elif (
                category_name in ["Real-Time Data Modules", "Other Modules"]
                and path == "dev-docs/modules"
            ):
                # Special handling for modules path that contains multiple types
                rtd_modules = []
                other_modules = []

                for file_path in path_data.keys():
                    if file_path.endswith(".md"):
                        filename = file_path.split("/")[-1]
                        base_name = filename[:-3]  # Remove .md

                        # Skip analytics adapters in modules directory
                        if base_name.endswith("AnalyticsAdapter"):
                            continue

                        # Categorize RTD providers
                        if base_name.endswith("RtdProvider"):
                            clean_name = base_name[:-11]  # Remove "RtdProvider"
                            module = ModuleInfo(
                                name=clean_name,
                                path=file_path,
                                category="Real-Time Data Modules",
                                repo=repo_key,
                            )
                            rtd_modules.append(module)
                        else:
                            module = ModuleInfo(
                                name=base_name,
                                path=file_path,
                                category="Other Modules",
                                repo=repo_key,
                            )
                            other_modules.append(module)

                if category_name == "Real-Time Data Modules":
                    categories["Real-Time Data Modules"].extend(rtd_modules)
                elif category_name == "Other Modules":
                    categories["Other Modules"].extend(other_modules)

        return dict(categories)

    def _parse_default(
        self, repo_data: dict[str, Any], repo_key: str
    ) -> dict[str, list[ModuleInfo]]:
        """Default parser for unsupported repository types."""
        categories: defaultdict[str, list[ModuleInfo]] = defaultdict(list)

        # Handle multi-path structure
        if "paths" in repo_data:
            for _, files in repo_data["paths"].items():
                for file_path, _ in files.items():
                    filename = file_path.split("/")[-1]
                    # Remove common extensions
                    name = filename
                    for ext in [".js", ".go", ".java", ".py", ".md"]:
                        if name.endswith(ext):
                            name = name[: -len(ext)]
                            break

                    module = ModuleInfo(
                        name=name,
                        path=file_path,
                        category="Modules",
                        repo=repo_key,
                    )
                    categories["Modules"].append(module)
        else:
            # Legacy structure
            for file_path, _ in repo_data.get("files", {}).items():
                filename = file_path.split("/")[-1]
                # Remove common extensions
                name = filename
                for ext in [".js", ".go", ".java", ".py", ".md"]:
                    if name.endswith(ext):
                        name = name[: -len(ext)]
                        break

                module = ModuleInfo(
                    name=name,
                    path=file_path,
                    category="Modules",
                    repo=repo_key,
                )
                categories["Modules"].append(module)

        return dict(categories)
