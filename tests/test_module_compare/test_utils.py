"""Test utilities for module comparison tests."""

from typing import Any


def create_github_response(
    repo_name: str,
    version: str,
    paths_data: dict[str, dict[str, str]] | None = None,
    legacy_files: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a properly structured GitHub API response.

    Args:
        repo_name: Repository name (e.g., "prebid/Prebid.js")
        version: Version string (e.g., "v9.0.0")
        paths_data: Multi-path data structure (path -> files dict)
        legacy_files: Legacy single-directory files structure

    Returns:
        Properly structured response matching GitHub client output
    """
    if paths_data:
        # Multi-path structure (current)
        total_files = sum(len(files) for files in paths_data.values())
        return {
            "repo": repo_name,
            "version": version,
            "paths": paths_data,
            "files": [],  # Not used in multi-path mode
            "metadata": {
                "commit_sha": f"mock_sha_{version}",
                "total_files": total_files,
            },
        }
    elif legacy_files:
        # Legacy single-directory structure
        return {
            "repo": repo_name,
            "version": version,
            "directory": "modules",  # Default for legacy
            "files": legacy_files,
            "metadata": {
                "commit_sha": f"mock_sha_{version}",
                "total_files": len(legacy_files),
            },
        }
    else:
        # Empty response
        return {
            "repo": repo_name,
            "version": version,
            "paths": {},
            "files": [],
            "metadata": {"commit_sha": f"mock_sha_{version}", "total_files": 0},
        }


def create_module_files(path: str, filenames: list[str]) -> dict[str, str]:
    """
    Create file structure for a given path.

    Args:
        path: Directory path (e.g., "modules")
        filenames: List of filenames

    Returns:
        Dictionary mapping full paths to empty content
    """
    return {f"{path}/{name}": "" for name in filenames}


def create_prebid_js_response(
    version: str, bid_adapters: list[str], analytics: list[str] | None = None
) -> dict[str, Any]:
    """
    Create a GitHub response for Prebid.js repository.

    Args:
        version: Version string
        bid_adapters: List of bid adapter filenames
        analytics: Optional list of analytics adapter filenames

    Returns:
        Properly structured Prebid.js repository response
    """
    paths_data = {}

    if bid_adapters:
        paths_data["modules"] = create_module_files("modules", bid_adapters)

    # In real Prebid.js, analytics are in the same directory
    if analytics:
        if "modules" not in paths_data:
            paths_data["modules"] = {}
        paths_data["modules"].update(create_module_files("modules", analytics))

    return create_github_response("prebid/Prebid.js", version, paths_data)


def create_prebid_server_response(version: str, adapters: list[str]) -> dict[str, Any]:
    """
    Create a GitHub response for Prebid Server (Go) repository.

    Args:
        version: Version string
        adapters: List of adapter directory names

    Returns:
        Properly structured Prebid Server response
    """
    # Prebid Server uses directory names, not files
    paths_data = {"adapters": {f"adapters/{name}": "" for name in adapters}}

    return create_github_response("prebid/prebid-server", version, paths_data)


def create_mock_config(
    repo_name: str,
    parser_type: str = "default",
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a mock repository configuration.

    Args:
        repo_name: Repository name
        parser_type: Parser type (e.g., "prebid_js", "prebid_server_go")
        paths: Category to path mapping

    Returns:
        Mock configuration matching RepositoryConfigManager output
    """
    default_paths = {
        "prebid_js": {"Bid Adapters": "modules"},
        "prebid_server_go": {"Bid Adapters": "adapters"},
        "prebid_server_java": {
            "Bid Adapters": "src/main/java/org/prebid/server/bidder"
        },
    }

    return {
        "repo": f"prebid/{repo_name}",
        "description": f"Mock {repo_name} repository",
        "parser_type": parser_type,
        "paths": paths or default_paths.get(parser_type, {"Modules": "modules"}),
        "fetch_strategy": (
            "filenames_only" if parser_type == "prebid_js" else "directory_names"
        ),
    }
