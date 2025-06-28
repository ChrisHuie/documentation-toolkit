"""
Core functionality for finding bid adapter aliases in GitHub repositories
"""

import re
import time
from typing import Any

import yaml

from ..repo_modules.github_client import GitHubClient
from ..shared_utilities.telemetry import trace_function


class AliasFinder:
    """Find bid adapter files containing aliases in GitHub repositories."""

    def __init__(self, token: str | None = None):
        """Initialize with optional GitHub token."""
        self.client = GitHubClient(token)

    @trace_function("find_adapter_files_with_aliases", include_args=True)
    def find_adapter_files_with_aliases(
        self, repo_name: str, version: str, directory: str, limit: int | None = None
    ) -> dict[str, Any]:
        """
        Find BidAdapter.js files containing 'aliases' and extract the alias values.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository

        Returns:
            Dictionary with matching files and their extracted aliases
        """
        try:
            print(f"Searching for 'aliases' in {repo_name}/{directory}...")

            # Use GitHub search API to find files containing aliases
            matching_files = self._search_files_with_aliases(repo_name, directory)

            # Filter to only BidAdapter.js files
            adapter_files_with_aliases = [
                f
                for f in matching_files
                if f.endswith("BidAdapter.js") and f.startswith(f"{directory}/")
            ]

            print(
                f"Found {len(adapter_files_with_aliases)} BidAdapter.js files with aliases"
            )
            print("Extracting alias values from each file...")

            # Extract aliases from each file
            file_aliases = {}
            files_to_process = (
                adapter_files_with_aliases[:limit]
                if limit
                else adapter_files_with_aliases
            )

            for file_path in files_to_process:
                try:
                    aliases = self._extract_aliases_from_file(
                        repo_name, version, file_path
                    )
                    file_aliases[file_path] = aliases
                    if aliases.get("aliases", []):
                        print(f"  ✓ {file_path} - {len(aliases['aliases'])} aliases")
                    else:
                        print(f"  ! {file_path} - no aliases extracted")
                except Exception as e:
                    print(f"  ! {file_path} - error: {str(e)}")
                    file_aliases[file_path] = {
                        "aliases": [],
                        "has_aliases_in_comments": False,
                        "has_aliases_in_code": False,
                        "commented_only": False,
                        "not_in_version": False,
                    }

            # Get commit SHA for metadata
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)

            return {
                "repo": repo_name,
                "version": version,
                "directory": directory,
                "file_aliases": file_aliases,
                "metadata": {
                    "commit_sha": ref,
                    "total_files": len(adapter_files_with_aliases),
                    "files_with_aliases": len(
                        [f for f in file_aliases.values() if f.get("aliases", [])]
                    ),
                },
            }

        except Exception as e:
            raise Exception(
                f"Error finding adapter files with aliases: {str(e)}"
            ) from e

    def find_adapter_files_with_aliases_batch(
        self,
        repo_name: str,
        version: str,
        directory: str,
        limit: int | None = None,
        batch_size: int = 20,
        delay: int = 2,
        request_delay: float = 0.6,
        start_from: int = 0,
    ) -> dict[str, Any]:
        """
        Find BidAdapter.js files with aliases using batch processing and rate limiting.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository
            limit: Maximum number of files to process
            batch_size: Number of files to process per batch
            delay: Delay in seconds between batches
            request_delay: Delay in seconds between individual requests
            start_from: Starting file index (for resuming)

        Returns:
            Dictionary with matching files and their extracted aliases
        """
        try:
            print(f"Searching for 'aliases' in {repo_name}/{directory}...")

            # Set current repo and version for the search phase
            self._current_repo = repo_name
            self._current_version = version

            # Use GitHub search API to find files containing aliases
            matching_files = self._search_files_with_aliases(repo_name, directory)

            # Filter to only BidAdapter.js files
            adapter_files_with_aliases = [
                f
                for f in matching_files
                if f.endswith("BidAdapter.js") and f.startswith(f"{directory}/")
            ]

            print(
                f"Found {len(adapter_files_with_aliases)} BidAdapter.js files with aliases"
            )

            # Apply limits and start_from
            if start_from > 0:
                adapter_files_with_aliases = adapter_files_with_aliases[start_from:]
                print(f"Starting from index {start_from}")

            if limit:
                adapter_files_with_aliases = adapter_files_with_aliases[:limit]
                print(f"Limited to {limit} files")

            print(
                f"Processing {len(adapter_files_with_aliases)} files in batches of {batch_size}"
            )
            print("Extracting alias values from each file...")

            # Process files in batches
            file_aliases = {}
            total_batches = (
                len(adapter_files_with_aliases) + batch_size - 1
            ) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(adapter_files_with_aliases))
                batch_files = adapter_files_with_aliases[start_idx:end_idx]

                print(
                    f"\n📦 Batch {batch_num + 1}/{total_batches} ({len(batch_files)} files)"
                )

                # Process batch
                for i, file_path in enumerate(batch_files):
                    try:
                        result = self._extract_aliases_from_file(
                            repo_name, version, file_path
                        )
                        file_aliases[file_path] = result

                        aliases = result["aliases"]
                        if aliases:
                            print(f"  ✓ {file_path} - {len(aliases)} aliases")
                        elif result["commented_only"]:
                            print(f"  # {file_path} - aliases in comments only")
                        else:
                            print(f"  - {file_path} - no aliases")

                    except Exception as e:
                        # Check if it's a 404 error (file doesn't exist in this version)
                        is_404_error = "404" in str(e)
                        if is_404_error:
                            print(f"  - {file_path} - not in {version}")
                        else:
                            print(f"  ! {file_path} - error: {str(e)}")

                        file_aliases[file_path] = {
                            "aliases": [],
                            "has_aliases_in_comments": False,
                            "has_aliases_in_code": False,
                            "commented_only": False,
                            "not_in_version": is_404_error,
                        }

                    # Delay between individual requests to avoid per-minute rate limits
                    if (
                        request_delay > 0 and i < len(batch_files) - 1
                    ):  # Don't delay after last file in batch
                        time.sleep(request_delay)

                # Delay between batches (except for the last batch)
                if batch_num < total_batches - 1:
                    print(f"⏳ Waiting {delay} seconds before next batch...")
                    time.sleep(delay)

            # Get commit SHA for metadata
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)

            # Calculate statistics
            files_with_aliases = len([f for f in file_aliases.values() if f["aliases"]])
            files_with_commented_aliases = len(
                [f for f in file_aliases.values() if f["commented_only"]]
            )
            files_not_in_version = len(
                [f for f in file_aliases.values() if f.get("not_in_version", False)]
            )
            files_with_empty_aliases = len(
                [
                    f
                    for f in file_aliases.values()
                    if not f["aliases"]
                    and not f["commented_only"]
                    and not f.get("not_in_version", False)
                ]
            )

            return {
                "repo": repo_name,
                "version": version,
                "directory": directory,
                "file_aliases": file_aliases,
                "metadata": {
                    "commit_sha": ref,
                    "total_files": len(file_aliases),
                    "files_with_aliases": files_with_aliases,
                    "files_with_commented_aliases": files_with_commented_aliases,
                    "files_not_in_version": files_not_in_version,
                    "files_with_empty_aliases": files_with_empty_aliases,
                },
            }

        except Exception as e:
            raise Exception(
                f"Error finding adapter files with aliases: {str(e)}"
            ) from e

    def _search_files_with_aliases(self, repo_name: str, directory: str) -> list[str]:
        """Use GitHub search API to find files containing aliases keyword."""
        try:
            matching_files = []

            # Search for "aliases" only (covers both lowercase and likely catches ALIASES too)
            query = f"aliases repo:{repo_name} path:{directory} extension:js filename:BidAdapter"

            print(f"Searching with query: {query}")

            # Use GitHub search API
            result = self.client.github.search_code(query)

            # Add all files from search for now (comment filtering temporarily disabled)
            for item in result:
                file_path = item.path
                matching_files.append(file_path)
                print(f"  ✓ {file_path}")

            return matching_files

        except Exception as e:
            raise Exception(f"Error searching files with GitHub API: {str(e)}") from e

    def _fetch_single_file_content(
        self, repo_name: str, version: str, file_path: str
    ) -> str:
        """Fetch content of a single file."""
        try:
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)
            content_file = repo.get_contents(file_path, ref=ref)
            if isinstance(content_file, list):
                raise Exception(f"Expected single file but got directory: {file_path}")
            return self.client._get_file_content(content_file)
        except Exception as e:
            raise Exception(f"Error fetching content for {file_path}: {str(e)}") from e

    def _file_exists_in_version(
        self, repo_name: str, version: str, file_path: str
    ) -> bool:
        """Check if a file exists in a specific version/tag/branch."""
        try:
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)
            repo.get_contents(file_path, ref=ref)
            return True
        except Exception:
            return False

    def _extract_aliases_from_file(
        self, repo_name: str, version: str, file_path: str
    ) -> dict[str, Any]:
        """Extract alias values from a BidAdapter.js file."""
        try:
            content = self._fetch_single_file_content(repo_name, version, file_path)
            # Store the version for use in library file fetching
            self._current_version = version
            self._current_repo = repo_name

            # Check if file has aliases in comments but not in code
            has_aliases_in_comments = self._contains_aliases(content)
            content_no_comments = self._remove_js_comments(content)
            has_aliases_in_code = self._contains_aliases(content_no_comments)

            aliases = self._parse_aliases_from_content(content)

            return {
                "aliases": aliases,
                "has_aliases_in_comments": has_aliases_in_comments,
                "has_aliases_in_code": has_aliases_in_code,
                "commented_only": has_aliases_in_comments and not has_aliases_in_code,
                "not_in_version": False,
            }
        except Exception as e:
            raise Exception(
                f"Error extracting aliases from {file_path}: {str(e)}"
            ) from e

    def _parse_aliases_from_content(self, content: str) -> list[str]:
        """Parse aliases from JavaScript file content."""
        aliases: list[str] = []

        # Remove comments before parsing to avoid extracting commented-out aliases
        content = self._remove_js_comments(content)

        # First, handle import statements and fetch external alias definitions
        imported_aliases = self._handle_imported_aliases(content)
        aliases.extend(imported_aliases)

        # Handle constant references within the same file
        constant_aliases = self._handle_constant_references(content)
        aliases.extend(constant_aliases)

        # Pattern 1: Direct array assignment - aliases: ['alias1', 'alias2'] or alias: ['alias1', 'alias2']
        direct_patterns = [
            r"aliases\s*:\s*\[(.*?)\]",  # aliases: [...]
            r"alias\s*:\s*\[(.*?)\]",  # alias: [...]  (singular)
        ]

        for pattern in direct_patterns:
            direct_matches = re.findall(pattern, content, re.DOTALL)
            for match in direct_matches:
                # Parse mixed array content more carefully
                self._parse_mixed_array_content(match, aliases, content)

        # Pattern 2: Variable reference - aliases: VARIABLE_NAME or alias: VARIABLE_NAME
        var_patterns = [
            r"aliases\s*:\s*([A-Z_][A-Z0-9_]*)",  # aliases: VARIABLE
            r"alias\s*:\s*([A-Z_][A-Z0-9_]*)",  # alias: VARIABLE (singular)
        ]

        var_matches = []
        for pattern in var_patterns:
            var_matches.extend(re.findall(pattern, content))

        for var_name in var_matches:
            # Skip debug/config objects that aren't aliases
            if any(
                debug_word in var_name.lower()
                for debug_word in ["debug", "config", "param", "query", "map"]
            ):
                continue

            # Look for array variable definition
            var_def_patterns = [
                # const/var/let VARIABLE = ['alias1', 'alias2']
                rf"(?:const|var|let)\s+{var_name}\s*=\s*\[(.*?)\]",
                # VARIABLE = ['alias1', 'alias2']
                rf"{var_name}\s*=\s*\[(.*?)\]",
            ]

            for pattern in var_def_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    # Use smart parsing for mixed array content
                    self._parse_mixed_array_content(match, aliases, content)

            # Look for object variable definition where aliases are keys
            obj_def_patterns = [
                # const/var/let VARIABLE = { 'alias1': {...}, 'alias2': {...} }
                rf"(?:const|var|let)\s+{var_name}\s*=\s*\{{(.*?)\}}",
                # VARIABLE = { 'alias1': {...}, 'alias2': {...} }
                rf"{var_name}\s*=\s*\{{(.*?)\}}",
            ]

            for pattern in obj_def_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    # Extract keys from object (quoted strings followed by colon)
                    alias_keys = re.findall(r'[\'"`]([^\'"`]+)[\'"`]\s*:', match)
                    aliases.extend(alias_keys)

        # Pattern 3: Direct object with aliases as keys - aliases: { 'alias1': {...}, 'alias2': {...} }
        obj_direct_pattern = r"aliases\s*:\s*\{(.*?)\}"
        obj_direct_matches = re.findall(obj_direct_pattern, content, re.DOTALL)

        for match in obj_direct_matches:
            # Extract keys from object (quoted strings followed by colon)
            alias_keys = re.findall(r'[\'"`]([^\'"`]+)[\'"`]\s*:', match)
            aliases.extend(alias_keys)

        # Pattern 4: Object.keys() usage - Object.keys(ALIASES)
        keys_pattern = r"Object\.keys\(([A-Z_][A-Z0-9_]*)\)"
        keys_matches = re.findall(keys_pattern, content)

        for var_name in keys_matches:
            # Skip debug/config objects that aren't aliases
            if any(
                debug_word in var_name.lower()
                for debug_word in ["debug", "config", "param", "query", "map"]
            ):
                continue

            # This indicates the variable contains an object with aliases as keys
            obj_def_patterns = [
                rf"(?:const|var|let)\s+{var_name}\s*=\s*\{{(.*?)\}}",
                rf"{var_name}\s*=\s*\{{(.*?)\}}",
            ]

            for pattern in obj_def_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    alias_keys = re.findall(r'[\'"`]([^\'"`]+)[\'"`]\s*:', match)
                    aliases.extend(alias_keys)

        # Pattern 5: Standalone aliases variable - const aliases = [{ code: 'alias', gvlid: 123 }]
        standalone_patterns = [
            r"(?:const|var|let)\s+aliases\s*=\s*\[(.*?)\]",  # const aliases = [...]
            r"this\.aliases\s*=\s*\[(.*?)\]",  # this.aliases = [...]
        ]

        for pattern in standalone_patterns:
            standalone_matches = re.findall(pattern, content, re.DOTALL)
            for match in standalone_matches:
                # Parse mixed array content more carefully
                self._parse_mixed_array_content(match, aliases, content)

        # Remove duplicates and return
        return list(set(aliases))

    def _parse_mixed_array_content(
        self, array_content: str, aliases: list, full_content: str
    ) -> None:
        """Parse array content that may contain strings, objects, and variable references."""

        # Split by commas, but be careful of nested structures
        elements = self._split_array_elements(array_content)

        for element in elements:
            element = element.strip()

            # Skip empty elements
            if not element:
                continue

            # Case 1: Simple quoted string
            simple_string_match = re.match(r'^[\'"`]([^\'"`]+)[\'"`]$', element)
            if simple_string_match:
                alias_name = simple_string_match.group(1)
                # Only add if it's not a URL
                if not alias_name.startswith(("http://", "https://", "//")):
                    aliases.append(alias_name)
                continue

            # Case 2: Object with code property
            if element.strip().startswith("{") and "code" in element:
                # Extract code property value
                code_matches = re.findall(r'code\s*:\s*[\'"`]([^\'"`]+)[\'"`]', element)
                aliases.extend(code_matches)

                # Also handle variable references in code
                code_var_matches = re.findall(r"code\s*:\s*([A-Z_][A-Z0-9_]*)", element)
                for var_name in code_var_matches:
                    var_def_patterns = [
                        rf'(?:const|var|let)\s+{var_name}\s*=\s*[\'"`]([^\'"`]+)[\'"`]',
                        rf'{var_name}\s*=\s*[\'"`]([^\'"`]+)[\'"`]',
                    ]
                    for pattern in var_def_patterns:
                        var_matches = re.findall(pattern, full_content)
                        aliases.extend(var_matches)
                continue

            # Case 3: Variable reference
            var_match = re.match(r"^([A-Z_][A-Z0-9_]*)$", element)
            if var_match:
                var_name = var_match.group(1)
                var_def_patterns = [
                    rf'(?:const|var|let)\s+{var_name}\s*=\s*[\'"`]([^\'"`]+)[\'"`]',
                    rf'{var_name}\s*=\s*[\'"`]([^\'"`]+)[\'"`]',
                ]
                for pattern in var_def_patterns:
                    var_matches = re.findall(pattern, full_content)
                    aliases.extend(var_matches)

    def _split_array_elements(self, array_content: str) -> list[str]:
        """Split array content by commas, respecting nested braces."""
        elements = []
        current_element = ""
        brace_count = 0
        in_quotes = False
        quote_char = None

        for char in array_content:
            if char in ['"', "'", "`"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif not in_quotes:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "," and brace_count == 0:
                    elements.append(current_element.strip())
                    current_element = ""
                    continue

            current_element += char

        # Add the last element
        if current_element.strip():
            elements.append(current_element.strip())

        return elements

    def _remove_js_comments(self, content: str) -> str:
        """Remove JavaScript comments (both single-line and multi-line) from content."""
        # Remove multi-line comments /* ... */
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Remove single-line comments // ... (but preserve URLs like https://)
        # This regex looks for // that's not preceded by http: or https:
        content = re.sub(
            r"(?<!https:)(?<!http:)//.*?$", "", content, flags=re.MULTILINE
        )

        return content

    def _handle_imported_aliases(self, content: str) -> list[str]:
        """Handle imported alias variables by fetching and parsing external library files."""
        aliases: list[str] = []

        # Find import statements from libraries directory (including multi-line imports)
        import_pattern = (
            r'import\s*\{([^}]+)\}\s*from\s*[\'"`](\.\./libraries/[^\'"`]+)[\'"`]'
        )
        import_matches = re.findall(import_pattern, content, re.DOTALL)

        for imported_vars, import_path in import_matches:
            # Get all imported variables
            all_imported_vars = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)", imported_vars)

            # Check which imported variables are used in aliases/alias assignments
            alias_vars = []
            for var in all_imported_vars:
                # Check if this variable is used in aliases: VAR or alias: VAR
                if re.search(rf"aliases?\s*:\s*{re.escape(var)}\b", content):
                    alias_vars.append(var)

            if alias_vars:
                print(f"  Found alias imports: {alias_vars} from {import_path}")

                # Convert relative path to absolute library path
                library_path = import_path.replace("../libraries/", "libraries/")

                try:
                    library_content = self._fetch_library_file(library_path)
                    if library_content:
                        for alias_var in alias_vars:
                            library_aliases = self._extract_aliases_from_library(
                                library_content, alias_var
                            )
                            print(
                                f"  Extracted {len(library_aliases)} aliases from {alias_var}"
                            )
                            aliases.extend(library_aliases)
                except Exception as e:
                    print(
                        f"  Warning: Could not process import {import_path}: {str(e)}"
                    )

        return aliases

    def _fetch_library_file(self, library_path: str) -> str:
        """Fetch content from a library file in the same repository."""
        try:
            repo = self.client.github.get_repo(self._current_repo)
            ref = self.client._get_reference(repo, self._current_version)
            content_file = repo.get_contents(library_path, ref=ref)
            if isinstance(content_file, list):
                raise Exception(
                    f"Expected single file but got directory: {library_path}"
                )
            return self.client._get_file_content(content_file)
        except Exception as e:
            print(f"  Warning: Could not fetch library file {library_path}: {str(e)}")
            return ""

    def _extract_aliases_from_library(
        self, library_content: str, alias_var_name: str
    ) -> list[str]:
        """Extract alias definitions from a library file."""
        aliases: list[str] = []

        # Remove comments from library content
        library_content = self._remove_js_comments(library_content)

        # Look for the exported alias variable definition
        export_patterns = [
            # export const aliasVar = [...]
            rf"export\s+const\s+{alias_var_name}\s*=\s*\[(.*?)\]",
            # const aliasVar = [...]; export { aliasVar };
            rf"const\s+{alias_var_name}\s*=\s*\[(.*?)\]",
        ]

        for pattern in export_patterns:
            matches = re.findall(pattern, library_content, re.DOTALL)
            if matches:
                # Parse the alias array content from the first match
                self._parse_mixed_array_content(matches[0], aliases, library_content)
                break  # Found the definition, stop looking with other patterns

        return aliases

    def _handle_constant_references(self, content: str) -> list[str]:
        """Handle constant references like aliases: BIDDER_ALIASES or aliases: aliasBidderCode."""
        aliases: list[str] = []

        # Find aliases property that references a constant (both UPPERCASE and camelCase)
        alias_ref_pattern = r"aliases\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)"
        alias_ref_matches = re.findall(alias_ref_pattern, content)

        for const_name in alias_ref_matches:
            # Skip debug/config objects and type annotations
            if any(
                debug_word in const_name.lower()
                for debug_word in [
                    "debug",
                    "config",
                    "param",
                    "query",
                    "map",
                    "string",
                    "array",
                ]
            ):
                continue

            # Look for the constant definition in the same file
            const_def_patterns = [
                rf"const\s+{re.escape(const_name)}\s*=\s*\[(.*?)\]",
                rf"let\s+{re.escape(const_name)}\s*=\s*\[(.*?)\]",
                rf"var\s+{re.escape(const_name)}\s*=\s*\[(.*?)\]",
            ]

            for pattern in const_def_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    # Parse the alias array content
                    self._parse_mixed_array_content(match, aliases, content)

        return aliases

    def _contains_aliases(self, content: str) -> bool:
        """
        Check if file content contains 'aliases' or 'ALIASES' keywords.

        Args:
            content: File content to search

        Returns:
            True if aliases are found, False otherwise
        """
        # Search for both 'aliases' and 'ALIASES' as whole words
        # Using word boundaries to avoid matching substrings
        aliases_pattern = r"\b(?:aliases|ALIASES)\b"
        return bool(re.search(aliases_pattern, content, re.IGNORECASE))

    def find_server_aliases_from_yaml(
        self,
        repo_name: str,
        version: str,
        directory: str = "static/bidder-info",
        limit: int | None = None,
        batch_size: int = 20,
        delay: int = 2,
        request_delay: float = 0.6,
        start_from: int = 0,
    ) -> dict[str, Any]:
        """
        Find aliases in Prebid Server by searching YAML files for aliasOf keys.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository (default: static/bidder-info)
            limit: Maximum number of files to process
            batch_size: Number of files to process per batch
            delay: Delay in seconds between batches
            request_delay: Delay in seconds between individual requests
            start_from: Starting file index (for resuming)

        Returns:
            Dictionary with matching files and their extracted aliases
        """
        try:
            print(
                f"Searching for YAML files with 'aliasOf' in {repo_name}/{directory}..."
            )

            # Set current repo and version
            self._current_repo = repo_name
            self._current_version = version

            # Use GitHub search API to find YAML files containing aliasOf
            matching_files = self._search_yaml_files_with_alias_of(repo_name, directory)

            print(f"Found {len(matching_files)} YAML files with aliasOf")

            # Apply limits and start_from
            if start_from > 0:
                matching_files = matching_files[start_from:]
                print(f"Starting from index {start_from}")

            if limit:
                matching_files = matching_files[:limit]
                print(f"Limited to {limit} files")

            print(f"Processing {len(matching_files)} files in batches of {batch_size}")
            print("Extracting alias information from each YAML file...")

            # Process files in batches
            file_aliases = {}
            total_batches = (len(matching_files) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(matching_files))
                batch_files = matching_files[start_idx:end_idx]

                print(
                    f"\n📦 Batch {batch_num + 1}/{total_batches} ({len(batch_files)} files)"
                )

                # Process batch
                for i, file_path in enumerate(batch_files):
                    try:
                        result = self._extract_alias_from_yaml_file(
                            repo_name, version, file_path
                        )
                        file_aliases[file_path] = result

                        if result["alias_name"]:
                            print(
                                f"  ✓ {file_path} - alias: {result['alias_name']} -> {result['alias_of']}"
                            )
                        else:
                            print(f"  ! {file_path} - no valid alias found")

                    except Exception as e:
                        # Check if it's a 404 error (file doesn't exist in this version)
                        is_404_error = "404" in str(e)
                        if is_404_error:
                            print(f"  - {file_path} - not in {version}")
                        else:
                            print(f"  ! {file_path} - error: {str(e)}")

                        file_aliases[file_path] = {
                            "alias_name": None,
                            "alias_of": None,
                            "has_alias_of": False,
                            "not_in_version": is_404_error,
                        }

                    # Delay between individual requests to avoid per-minute rate limits
                    if request_delay > 0 and i < len(batch_files) - 1:
                        time.sleep(request_delay)

                # Delay between batches (except for the last batch)
                if batch_num < total_batches - 1:
                    print(f"⏳ Waiting {delay} seconds before next batch...")
                    time.sleep(delay)

            # Get commit SHA for metadata
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)

            # Calculate statistics
            files_with_aliases = len(
                [f for f in file_aliases.values() if f["alias_name"]]
            )
            files_not_in_version = len(
                [f for f in file_aliases.values() if f.get("not_in_version", False)]
            )
            files_with_empty_aliases = len(
                [
                    f
                    for f in file_aliases.values()
                    if not f["alias_name"] and not f.get("not_in_version", False)
                ]
            )

            return {
                "repo": repo_name,
                "version": version,
                "directory": directory,
                "file_aliases": file_aliases,
                "metadata": {
                    "commit_sha": ref,
                    "total_files": len(file_aliases),
                    "files_with_aliases": files_with_aliases,
                    "files_not_in_version": files_not_in_version,
                    "files_with_empty_aliases": files_with_empty_aliases,
                },
            }

        except Exception as e:
            raise Exception(f"Error finding server aliases from YAML: {str(e)}") from e

    def _search_yaml_files_with_alias_of(
        self, repo_name: str, directory: str
    ) -> list[str]:
        """Use GitHub search API to find YAML files containing aliasOf keyword."""
        try:
            matching_files = []

            # Search for "aliasOf" in YAML files
            query = f"aliasOf repo:{repo_name} path:{directory} extension:yaml"

            print(f"Searching with query: {query}")

            # Use GitHub search API
            result = self.client.github.search_code(query)

            for item in result:
                file_path = item.path
                matching_files.append(file_path)
                print(f"  ✓ {file_path}")

            return matching_files

        except Exception as e:
            raise Exception(
                f"Error searching YAML files with GitHub API: {str(e)}"
            ) from e

    def _extract_alias_from_yaml_file(
        self, repo_name: str, version: str, file_path: str
    ) -> dict[str, Any]:
        """Extract alias information from a YAML file."""
        try:
            content = self._fetch_single_file_content(repo_name, version, file_path)

            # Parse YAML content
            yaml_data = yaml.safe_load(content)

            # Extract alias name from filename (remove .yaml extension and directory path)
            filename = file_path.split("/")[-1]
            alias_name = (
                filename.replace(".yaml", "")
                if filename.endswith(".yaml")
                else filename
            )

            # Extract aliasOf value
            alias_of = yaml_data.get("aliasOf") if yaml_data else None

            return {
                "alias_name": alias_name,
                "alias_of": alias_of,
                "has_alias_of": alias_of is not None,
                "not_in_version": False,
            }

        except Exception as e:
            raise Exception(
                f"Error extracting alias from YAML file {file_path}: {str(e)}"
            ) from e

    def find_java_server_aliases_from_yaml(
        self,
        repo_name: str,
        version: str,
        directory: str = "src/main/resources/bidder-config",
        limit: int | None = None,
        batch_size: int = 20,
        delay: int = 2,
        request_delay: float = 0.6,
        start_from: int = 0,
    ) -> dict[str, Any]:
        """
        Find aliases in Prebid Server Java by searching bidder-config YAML files for aliases keys.

        Args:
            repo_name: Repository name in format "owner/repo"
            version: Git reference (tag, branch, commit SHA)
            directory: Directory path within repository (default: src/main/resources/bidder-config)
            limit: Maximum number of files to process
            batch_size: Number of files to process per batch
            delay: Delay in seconds between batches
            request_delay: Delay in seconds between individual requests
            start_from: Starting file index (for resuming)

        Returns:
            Dictionary with matching files and their extracted aliases
        """
        try:
            print(
                f"Searching for YAML files with 'aliases' in {repo_name}/{directory}..."
            )

            # Set current repo and version
            self._current_repo = repo_name
            self._current_version = version

            # Use GitHub search API to find YAML files containing aliases
            matching_files = self._search_java_yaml_files_with_aliases(
                repo_name, directory
            )

            print(f"Found {len(matching_files)} YAML files with aliases")

            # Apply limits and start_from
            if start_from > 0:
                matching_files = matching_files[start_from:]
                print(f"Starting from index {start_from}")

            if limit:
                matching_files = matching_files[:limit]
                print(f"Limited to {limit} files")

            print(f"Processing {len(matching_files)} files in batches of {batch_size}")
            print("Extracting alias information from each YAML file...")

            # Process files in batches
            file_aliases = {}
            total_batches = (len(matching_files) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(matching_files))
                batch_files = matching_files[start_idx:end_idx]

                print(
                    f"\n📦 Batch {batch_num + 1}/{total_batches} ({len(batch_files)} files)"
                )

                # Process batch
                for i, file_path in enumerate(batch_files):
                    try:
                        result = self._extract_java_aliases_from_yaml_file(
                            repo_name, version, file_path
                        )
                        file_aliases[file_path] = result

                        aliases_count = len(result["aliases"])
                        if aliases_count > 0:
                            print(f"  ✓ {file_path} - {aliases_count} aliases")
                        else:
                            print(f"  ! {file_path} - no aliases found")

                    except Exception as e:
                        # Check if it's a 404 error (file doesn't exist in this version)
                        is_404_error = "404" in str(e)
                        if is_404_error:
                            print(f"  - {file_path} - not in {version}")
                        else:
                            print(f"  ! {file_path} - error: {str(e)}")

                        file_aliases[file_path] = {
                            "aliases": [],
                            "bidder_name": None,
                            "not_in_version": is_404_error,
                        }

                    # Delay between individual requests to avoid per-minute rate limits
                    if request_delay > 0 and i < len(batch_files) - 1:
                        time.sleep(request_delay)

                # Delay between batches (except for the last batch)
                if batch_num < total_batches - 1:
                    print(f"⏳ Waiting {delay} seconds before next batch...")
                    time.sleep(delay)

            # Get commit SHA for metadata
            repo = self.client.github.get_repo(repo_name)
            ref = self.client._get_reference(repo, version)

            # Calculate statistics
            files_with_aliases = len([f for f in file_aliases.values() if f["aliases"]])
            files_not_in_version = len(
                [f for f in file_aliases.values() if f.get("not_in_version", False)]
            )
            files_with_empty_aliases = len(
                [
                    f
                    for f in file_aliases.values()
                    if not f["aliases"] and not f.get("not_in_version", False)
                ]
            )

            return {
                "repo": repo_name,
                "version": version,
                "directory": directory,
                "file_aliases": file_aliases,
                "metadata": {
                    "commit_sha": ref,
                    "total_files": len(file_aliases),
                    "files_with_aliases": files_with_aliases,
                    "files_not_in_version": files_not_in_version,
                    "files_with_empty_aliases": files_with_empty_aliases,
                },
            }

        except Exception as e:
            raise Exception(
                f"Error finding Java server aliases from YAML: {str(e)}"
            ) from e

    def _search_java_yaml_files_with_aliases(
        self, repo_name: str, directory: str
    ) -> list[str]:
        """Use GitHub search API to find YAML files containing aliases keyword in Java server."""
        try:
            matching_files = []

            # Search for "aliases" in YAML files within the bidder-config directory
            query = f"aliases repo:{repo_name} path:{directory} extension:yaml"

            print(f"Searching with query: {query}")

            # Use GitHub search API
            result = self.client.github.search_code(query)

            for item in result:
                file_path = item.path
                matching_files.append(file_path)
                print(f"  ✓ {file_path}")

            return matching_files

        except Exception as e:
            raise Exception(
                f"Error searching Java YAML files with GitHub API: {str(e)}"
            ) from e

    def _extract_java_aliases_from_yaml_file(
        self, repo_name: str, version: str, file_path: str
    ) -> dict[str, Any]:
        """Extract alias information from a Java bidder-config YAML file."""
        try:
            content = self._fetch_single_file_content(repo_name, version, file_path)

            # Parse YAML content
            yaml_data = yaml.safe_load(content)

            # Extract bidder name from filename (remove .yaml extension and directory path)
            filename = file_path.split("/")[-1]
            bidder_name = (
                filename.replace(".yaml", "")
                if filename.endswith(".yaml")
                else filename
            )

            # Extract aliases from the nested structure: adapters.{bidder_name}.aliases
            aliases_list = []
            if yaml_data and "adapters" in yaml_data:
                adapters = yaml_data["adapters"]
                if isinstance(adapters, dict) and bidder_name in adapters:
                    bidder_config = adapters[bidder_name]
                    if isinstance(bidder_config, dict) and "aliases" in bidder_config:
                        aliases_dict = bidder_config["aliases"]
                        if isinstance(aliases_dict, dict):
                            # Get all keys from the aliases dictionary - these are the alias names
                            aliases_list = list(aliases_dict.keys())

            return {
                "aliases": aliases_list,
                "bidder_name": bidder_name,
                "not_in_version": False,
            }

        except Exception as e:
            raise Exception(
                f"Error extracting Java aliases from YAML file {file_path}: {str(e)}"
            ) from e
