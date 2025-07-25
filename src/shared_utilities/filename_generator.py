"""
Shared filename generation utilities for consistent naming across tools
"""

from datetime import datetime
from pathlib import Path


def generate_output_filename(
    repo: str,
    version: str,
    output_type: str,
    custom_slug: str | None = None,
    extension: str = "txt",
) -> str:
    """
    Generate output filename based on repository, version, and output type.

    Args:
        repo: Repository name in format "owner/repo"
        version: Version string to include in filename
        output_type: Type of output ("modules_version", "alias_mappings", etc.)
        custom_slug: Custom repository slug to override default mapping
        extension: File extension (default: "txt")

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

    # Use custom slug if provided, otherwise use predefined slug or generate from repo name
    if custom_slug:
        repo_name = custom_slug
    elif repo in repo_slugs:
        repo_name = repo_slugs[repo]
    else:
        # Extract repo name and convert dashes to dots
        owner, repo_part = repo.split("/")
        repo_name = repo_part.lower().replace("-", ".")

    # Clean version string for filename
    version_clean = clean_version_for_filename(version)

    return f"{repo_name}_{output_type}_{version_clean}.{extension}"


def clean_version_for_filename(version: str) -> str:
    """
    Clean version string to be safe for use in filenames.

    Args:
        version: Raw version string

    Returns:
        Cleaned version string safe for filenames
    """
    # Replace slashes with underscores
    version_clean = version.replace("/", "_")

    # Remove leading "v" if present (e.g., "v3.19.0" -> "3.19.0")
    if version_clean.startswith("v"):
        version_clean = version_clean[1:]

    # Replace other problematic characters
    problematic_chars = [":", "*", "?", '"', "<", ">", "|"]
    for char in problematic_chars:
        version_clean = version_clean.replace(char, "_")

    return version_clean


def generate_timestamped_filename(
    base_name: str,
    extension: str = "txt",
    include_date: bool = True,
    include_time: bool = False,
) -> str:
    """
    Generate filename with timestamp.

    Args:
        base_name: Base filename without extension
        extension: File extension (default: "txt")
        include_date: Whether to include date in timestamp
        include_time: Whether to include time in timestamp

    Returns:
        Timestamped filename
    """
    timestamp_parts = []
    now = datetime.now()

    if include_date:
        timestamp_parts.append(now.strftime("%Y%m%d"))

    if include_time:
        timestamp_parts.append(now.strftime("%H%M%S"))

    if timestamp_parts:
        timestamp = "_".join(timestamp_parts)
        return f"{base_name}_{timestamp}.{extension}"
    else:
        return f"{base_name}.{extension}"


def ensure_output_directory(file_path: str) -> Path:
    """
    Ensure the directory for the output file exists.

    Args:
        file_path: Path to the output file

    Returns:
        Path object for the file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_safe_filename(filename: str) -> str:
    """
    Convert any string to a safe filename by removing/replacing problematic characters.

    Args:
        filename: Raw filename string

    Returns:
        Safe filename string
    """
    # Replace spaces with underscores
    safe_name = filename.replace(" ", "_")

    # Remove or replace problematic characters
    problematic_chars = {
        "/": "_",
        "\\": "_",
        ":": "_",
        "*": "_",
        "?": "_",
        '"': "_",
        "<": "_",
        ">": "_",
        "|": "_",
        "\n": "_",
        "\r": "_",
        "\t": "_",
    }

    for char, replacement in problematic_chars.items():
        safe_name = safe_name.replace(char, replacement)

    # Remove multiple consecutive underscores
    while "__" in safe_name:
        safe_name = safe_name.replace("__", "_")

    # Remove leading/trailing underscores
    safe_name = safe_name.strip("_")

    return safe_name


def generate_unique_filename(
    directory: str, base_name: str, extension: str = "txt"
) -> str:
    """
    Generate a unique filename in the given directory by appending numbers if needed.

    Args:
        directory: Directory where the file will be created
        base_name: Base filename without extension
        extension: File extension

    Returns:
        Unique filename
    """
    directory_path = Path(directory)
    base_filename = f"{base_name}.{extension}"

    if not (directory_path / base_filename).exists():
        return base_filename

    counter = 1
    while True:
        numbered_filename = f"{base_name}_{counter}.{extension}"
        if not (directory_path / numbered_filename).exists():
            return numbered_filename
        counter += 1


def generate_comparison_filename(
    source_repo: str,
    source_version: str,
    target_repo: str | None = None,
    target_version: str | None = None,
    custom_source_slug: str | None = None,
    custom_target_slug: str | None = None,
    extension: str = "txt",
) -> str:
    """
    Generate filename for module comparison output.

    For same repo comparison: {repo_slug}_module_compare_{earlier_version}_{later_version}.{ext}
    For cross-repo comparison: {repo1_slug}_{version1}_module_compare_{repo2_slug}_{version2}.{ext}

    Args:
        source_repo: Source repository name in format "owner/repo"
        source_version: Source version string
        target_repo: Target repository name (None for same-repo comparison)
        target_version: Target version string (None uses source_version)
        custom_source_slug: Custom slug for source repository
        custom_target_slug: Custom slug for target repository
        extension: File extension

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

    # Get source repo slug
    if custom_source_slug:
        source_slug = custom_source_slug
    elif source_repo in repo_slugs:
        source_slug = repo_slugs[source_repo]
    else:
        owner, repo_part = source_repo.split("/")
        source_slug = repo_part.lower().replace("-", ".")

    # Clean versions
    source_version_clean = clean_version_for_filename(source_version)

    # Same repository comparison
    if target_repo is None or target_repo == source_repo:
        target_version_clean = clean_version_for_filename(
            target_version or source_version
        )

        # Determine version order (put earlier version first)
        # Simple heuristic: if source starts with a number and target is "master"/"main",
        # source is earlier. Otherwise, lexical comparison
        if target_version in ["master", "main"] and source_version[0].isdigit():
            earlier, later = source_version_clean, target_version_clean
        elif (
            source_version in ["master", "main"] and (target_version or "")[0].isdigit()
        ):
            earlier, later = target_version_clean, source_version_clean
        else:
            # Lexical comparison
            versions = sorted([source_version_clean, target_version_clean])
            earlier, later = versions[0], versions[1]

        return f"{source_slug}_module_compare_{earlier}_{later}.{extension}"

    # Cross-repository comparison
    else:
        # Get target repo slug
        if custom_target_slug:
            target_slug = custom_target_slug
        elif target_repo in repo_slugs:
            target_slug = repo_slugs[target_repo]
        else:
            owner, repo_part = target_repo.split("/")
            target_slug = repo_part.lower().replace("-", ".")

        target_version_clean = clean_version_for_filename(target_version or "latest")

        return f"{source_slug}_{source_version_clean}_module_compare_{target_slug}_{target_version_clean}.{extension}"
