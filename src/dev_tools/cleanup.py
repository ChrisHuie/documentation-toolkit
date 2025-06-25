"""
Project cleanup utilities.

Removes artifact files and directories that shouldn't be committed to git.
"""

import shutil
from pathlib import Path


class ProjectCleaner:
    """Cleans up project artifacts and temporary files."""

    # Files and directories that should not be committed
    ARTIFACT_PATTERNS = {
        # Python artifacts
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        # Virtual environments
        ".venv/",
        "venv/",
        "ENV/",
        "env/",
        # IDE and editor files
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        # Testing
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
        ".tox/",
        # Mypy
        ".mypy_cache/",
        ".dmypy.json",
        "dmypy.json",
        # Version control (excluding root .git)
        # ".git/",  # Commented out to preserve git repository
        # OS files
        "Thumbs.db",
        # Project-specific artifacts
        ".python-version",  # pyenv version file
        "*.log",
        ".env",  # Keep .env.example but not .env
    }

    # Files to definitely keep (even if they match patterns)
    KEEP_FILES = {
        ".env.example",
        ".gitignore", 
        ".gitkeep",
        ".git",  # Always preserve git repository
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def find_artifacts(self) -> list[Path]:
        """Find all artifact files and directories in the project."""
        artifacts = []

        for item in self.project_root.rglob("*"):
            # Skip if it's in a git directory (except root .git)
            if ".git" in item.parts and item != self.project_root / ".git":
                continue

            item_name = item.name
            item_relative = item.relative_to(self.project_root)

            # Check if we should keep this file
            if item_name in self.KEEP_FILES:
                continue

            # Check against patterns
            should_remove = False
            for pattern in self.ARTIFACT_PATTERNS:
                if pattern.endswith("/"):
                    # Directory pattern
                    if item.is_dir() and (
                        item_name == pattern[:-1]
                        or str(item_relative).startswith(pattern)
                    ):
                        should_remove = True
                        break
                elif "*" in pattern:
                    # Glob pattern
                    if item_relative.match(pattern):
                        should_remove = True
                        break
                else:
                    # Exact match
                    if item_name == pattern:
                        should_remove = True
                        break

            if should_remove:
                artifacts.append(item)

        return artifacts

    def clean(self, dry_run: bool = False) -> list[Path]:
        """
        Clean up project artifacts.

        Args:
            dry_run: If True, only return what would be removed without actually removing.

        Returns:
            List of paths that were (or would be) removed.
        """
        artifacts = self.find_artifacts()
        removed = []

        for artifact in artifacts:
            if dry_run:
                removed.append(artifact)
            else:
                try:
                    if artifact.is_dir():
                        shutil.rmtree(artifact)
                    else:
                        artifact.unlink()
                    removed.append(artifact)
                except (OSError, PermissionError) as e:
                    # Log but don't fail on permission errors
                    print(f"Warning: Could not remove {artifact}: {e}")

        return removed
