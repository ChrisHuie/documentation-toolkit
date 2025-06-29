"""
Output directory management utilities for organizing tool outputs.

This module provides utilities for creating and managing a hierarchical directory
structure for tool outputs organized by repository and version, with automatic
cleanup of empty directories.
"""

import os
from pathlib import Path

from . import get_logger

logger = get_logger(__name__)


class OutputManager:
    """Manages output directory structure for tools."""

    def __init__(self, base_output_dir: str = "output"):
        """
        Initialize the output manager.

        Args:
            base_output_dir: Base directory for all outputs (default: "output")
        """
        self.base_dir = Path(base_output_dir)

    def get_output_path(
        self,
        tool_name: str,
        repo_name: str,
        version: str,
        filename: str,
        create_dirs: bool = True,
    ) -> Path:
        """
        Get the full output path for a file, creating directories if needed.

        Directory structure: output/{tool_name}/{repo_name}/{version}/{filename}

        Args:
            tool_name: Name of the tool (e.g., "supported-mediatypes")
            repo_name: Repository name (e.g., "prebid.js")
            version: Version string (e.g., "9.51.0")
            filename: Output filename
            create_dirs: Whether to create directories if they don't exist

        Returns:
            Full path to the output file
        """
        # Clean up repo name (remove owner/ prefix if present)
        if "/" in repo_name:
            repo_name = repo_name.split("/")[-1]

        # Clean up version (remove 'v' prefix if present)
        clean_version = version.lstrip("v")

        # Build the path
        output_path = self.base_dir / tool_name / repo_name / clean_version / filename

        if create_dirs:
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(
                f"Created output directory structure: {output_path.parent}",
                tool=tool_name,
                repo=repo_name,
                version=clean_version,
            )

        return output_path

    def save_output(
        self,
        content: str,
        tool_name: str,
        repo_name: str,
        version: str,
        filename: str,
    ) -> Path:
        """
        Save content to the appropriate output location.

        Args:
            content: Content to save
            tool_name: Name of the tool
            repo_name: Repository name
            version: Version string
            filename: Output filename

        Returns:
            Path to the saved file
        """
        output_path = self.get_output_path(tool_name, repo_name, version, filename)

        # Write the content
        output_path.write_text(content)
        logger.info(
            f"Saved output to {output_path}",
            tool=tool_name,
            repo=repo_name,
            version=version,
            size=len(content),
        )

        return output_path

    def cleanup_empty_directories(self, tool_name: str | None = None) -> int:
        """
        Remove empty directories in the output structure.

        Args:
            tool_name: If specified, only clean up directories for this tool.
                      If None, clean up all tools.

        Returns:
            Number of directories removed
        """
        removed_count = 0

        # Determine starting point
        if tool_name:
            start_path = self.base_dir / tool_name
        else:
            start_path = self.base_dir

        if not start_path.exists():
            return 0

        # Walk the directory tree bottom-up to remove empty directories
        for dirpath, dirnames, filenames in os.walk(start_path, topdown=False):
            dir_path = Path(dirpath)

            # Skip the base output directory itself
            if dir_path == self.base_dir:
                continue

            # Check if directory is empty (no files and no subdirectories)
            if not filenames and not dirnames:
                try:
                    dir_path.rmdir()
                    removed_count += 1
                    logger.debug(f"Removed empty directory: {dir_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove directory {dir_path}: {e}")

        if removed_count > 0:
            logger.info(
                f"Cleaned up {removed_count} empty directories",
                tool=tool_name,
            )

        return removed_count

    def get_existing_outputs(
        self,
        tool_name: str,
        repo_name: str | None = None,
        version: str | None = None,
    ) -> list[Path]:
        """
        Get a list of existing output files for a tool/repo/version.

        Args:
            tool_name: Name of the tool
            repo_name: Optional repository name filter
            version: Optional version filter

        Returns:
            List of paths to existing output files
        """
        outputs: list[Path] = []
        tool_path = self.base_dir / tool_name

        if not tool_path.exists():
            return outputs

        # If repo_name is specified
        if repo_name:
            # Clean up repo name
            if "/" in repo_name:
                repo_name = repo_name.split("/")[-1]

            repo_path = tool_path / repo_name
            if not repo_path.exists():
                return outputs

            # If version is also specified
            if version:
                clean_version = version.lstrip("v")
                version_path = repo_path / clean_version
                if version_path.exists():
                    outputs.extend(version_path.glob("*"))
            else:
                # Get all versions for this repo
                for version_dir in repo_path.iterdir():
                    if version_dir.is_dir():
                        outputs.extend(version_dir.glob("*"))
        else:
            # Get all outputs for this tool
            for repo_dir in tool_path.iterdir():
                if repo_dir.is_dir():
                    for version_dir in repo_dir.iterdir():
                        if version_dir.is_dir():
                            outputs.extend(version_dir.glob("*"))

        return [p for p in outputs if p.is_file()]

    def get_output_structure(self, tool_name: str | None = None) -> dict:
        """
        Get the current output directory structure as a nested dictionary.

        Args:
            tool_name: Optional tool name to filter by

        Returns:
            Nested dictionary representing the directory structure
        """
        structure: dict[str, dict] = {}

        if tool_name:
            start_paths = (
                [self.base_dir / tool_name]
                if (self.base_dir / tool_name).exists()
                else []
            )
        else:
            start_paths = [p for p in self.base_dir.iterdir() if p.is_dir()]

        for tool_path in start_paths:
            tool_name = tool_path.name
            structure[tool_name] = {}

            for repo_path in tool_path.iterdir():
                if repo_path.is_dir():
                    repo_name = repo_path.name
                    structure[tool_name][repo_name] = {}

                    for version_path in repo_path.iterdir():
                        if version_path.is_dir():
                            version = version_path.name
                            files = [
                                f.name for f in version_path.glob("*") if f.is_file()
                            ]
                            if files:
                                structure[tool_name][repo_name][version] = files

        return structure


# Convenience functions
_default_manager = None


def get_default_output_manager() -> OutputManager:
    """Get the default output manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = OutputManager()
    return _default_manager


def get_output_path(
    tool_name: str,
    repo_name: str,
    version: str,
    filename: str,
    create_dirs: bool = True,
) -> Path:
    """
    Get output path using the default output manager.

    See OutputManager.get_output_path for details.
    """
    return get_default_output_manager().get_output_path(
        tool_name, repo_name, version, filename, create_dirs
    )


def save_output(
    content: str,
    tool_name: str,
    repo_name: str,
    version: str,
    filename: str,
) -> Path:
    """
    Save output using the default output manager.

    See OutputManager.save_output for details.
    """
    return get_default_output_manager().save_output(
        content, tool_name, repo_name, version, filename
    )


def cleanup_empty_directories(tool_name: str | None = None) -> int:
    """
    Clean up empty directories using the default output manager.

    See OutputManager.cleanup_empty_directories for details.
    """
    return get_default_output_manager().cleanup_empty_directories(tool_name)
