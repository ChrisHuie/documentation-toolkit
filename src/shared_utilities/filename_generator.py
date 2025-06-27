"""
Shared filename generation utilities for consistent naming across tools
"""


def generate_output_filename(repo: str, version: str, output_type: str) -> str:
    """
    Generate output filename based on repository, version, and output type.

    Args:
        repo: Repository name in format "owner/repo"
        version: Version string to include in filename
        output_type: Type of output ("modules_version", "alias_mappings")

    Returns:
        Generated filename string
    """
    # Map repository names to standardized slugs
    repo_slugs = {
        "prebid/Prebid.js": "prebid.js",
        "prebid/prebid-server": "prebid.server.go", 
        "prebid/prebid-server-java": "prebid.server.java",
        "prebid/prebid.github.io": "prebid.github.io",
    }
    
    # Use predefined slug if available, otherwise generate from repo name
    if repo in repo_slugs:
        repo_name = repo_slugs[repo]
    else:
        # Extract repo name and convert dashes to dots
        owner, repo_part = repo.split("/")
        repo_name = repo_part.lower().replace("-", ".")
    
    # Clean version string for filename
    version_clean = version.replace("/", "_")
    # Remove leading "v" if present (e.g., "v3.19.0" -> "3.19.0")
    if version_clean.startswith("v"):
        version_clean = version_clean[1:]
    
    return f"{repo_name}_{output_type}_{version_clean}.txt"