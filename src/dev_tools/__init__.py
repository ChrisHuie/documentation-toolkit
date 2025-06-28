"""
Development tools for documentation-toolkit project.

This module contains utilities for maintaining code quality, documentation sync,
and project validation.
"""

from pathlib import Path

from .docs_sync import DocumentationSyncer
from .validator import ProjectValidator


def check_documentation_sync_status(project_root: Path | None = None) -> None:
    """
    Quick check for documentation sync status with user warning.

    Args:
        project_root: Project root directory (auto-detected if None)
    """
    if project_root is None:
        # Auto-detect project root
        current = Path(__file__).parent
        while current.parent != current:  # Stop at filesystem root
            if (current / "pyproject.toml").exists():
                project_root = current
                break
            current = current.parent
        else:
            return  # Can't find project root

    try:
        syncer = DocumentationSyncer(project_root)
        in_sync, out_of_sync_files = syncer.check_sync_status()

        if not in_sync and out_of_sync_files:
            print("\n⚠️  WARNING: Agent documentation files are OUT OF SYNC!")
            print(f"   Files that differ: {', '.join(out_of_sync_files)}")
            print("   Run 'validate-project' to sync all agent instruction files.")
            print(
                "   This ensures CLAUDE.md, AGENTS.md, and GEMINI.md stay consistent.\n"
            )
    except Exception:
        pass  # Ignore errors during check


__all__ = ["ProjectValidator", "DocumentationSyncer", "check_documentation_sync_status"]
