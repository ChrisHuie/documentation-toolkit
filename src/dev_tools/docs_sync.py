"""
Documentation synchronization utilities.

Keeps agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md) in sync.
"""

from pathlib import Path
import os


class DocumentationSyncer:
    """Synchronizes agent instruction files.

    This class ensures that CLAUDE.md, AGENTS.md, and GEMINI.md all contain
    the same content with only their headers differing. This prevents
    documentation drift between different AI agent platforms.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.files = {
            "claude": self.project_root / "CLAUDE.md",
            "agents": self.project_root / "AGENTS.md",
            "gemini": self.project_root / "GEMINI.md",
        }
        self.headers = {
            "claude": "# Claude Instructions\n\nThis file contains instructions and context for Claude when working on this project.",
            "agents": "# Agent Instructions\n\nThis file contains instructions and context for AI agents when working on this project.",
            "gemini": "# Gemini Instructions\n\nThis file contains instructions and context for Gemini when working on this project.",
        }

    def read_file_content(self, file_path: Path) -> str:
        """Read file content, returning empty string if file doesn't exist."""
        try:
            return file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def extract_content_after_header(self, content: str) -> str:
        """Extract content after the header section, preserving everything else."""
        lines = content.split("\n")
        if not lines:
            return ""

        # Skip the first line (title), empty lines, and the description line
        content_start = 1

        # Skip empty lines after title
        while content_start < len(lines) and not lines[content_start].strip():
            content_start += 1

        # Skip the description line if it exists
        if content_start < len(lines) and lines[content_start].startswith(
            "This file contains instructions"
        ):
            content_start += 1

        # Skip any remaining empty lines
        while content_start < len(lines) and not lines[content_start].strip():
            content_start += 1

        return "\n".join(lines[content_start:])

    def create_file_with_header(self, header: str, content: str) -> str:
        """Create file content with specified header and shared content."""
        return f"{header}\n\n{content}"

    def validate_headers(self) -> None:
        """Validate that headers are correct for each file type."""
        expected_patterns = {
            "claude": "# Claude Instructions",
            "agents": "# Agent Instructions",
            "gemini": "# Gemini Instructions",
        }

        for name, header in self.headers.items():
            if not header.startswith(expected_patterns[name]):
                raise ValueError(
                    f"Invalid header for {name}: expected to start with '{expected_patterns[name]}', got '{header.split()[0]} {header.split()[1]}'"
                )

    def sync(self) -> dict[str, bool]:
        """
        Sync all documentation files.

        Returns:
            Dict mapping file names to whether they were updated.
        """
        # Validate headers before proceeding
        self.validate_headers()

        results = {}

        # Read all files
        contents = {}
        for name, path in self.files.items():
            contents[name] = self.read_file_content(path)

        # Find the most recently modified file with content
        most_recent = None
        most_recent_time = 0.0

        for name, path in self.files.items():
            if path.exists() and contents[name].strip():
                mtime = path.stat().st_mtime
                if mtime > most_recent_time:
                    most_recent_time = mtime
                    most_recent = name

        if not most_recent:
            raise ValueError("No source file found with content")

        # Extract shared content from the most recent file
        shared_content = self.extract_content_after_header(contents[most_recent])

        # Validate that we have substantial content to sync
        if len(shared_content.strip()) < 100:
            raise ValueError(
                f"Source file {most_recent} appears to have insufficient content for sync"
            )

        print(
            f"📝 Syncing documentation from {most_recent.upper()}.md (most recent)..."
        )

        # Update all files with the shared content
        for name, path in self.files.items():
            new_content = self.create_file_with_header(
                self.headers[name], shared_content
            )

            # Only write if content has changed
            if contents[name] != new_content:
                path.write_text(new_content, encoding="utf-8")
                results[name] = True
                print(f"  ✅ Updated {name.upper()}.md")
            else:
                results[name] = False
                print(f"  ⏭️ {name.upper()}.md already in sync")

        return results

    def check_sync_status(self) -> tuple[bool, list[str]]:
        """
        Check if all documentation files are in sync.

        Returns:
            Tuple of (all_in_sync, list_of_out_of_sync_files)
        """
        try:
            # Read all files
            contents = {}
            for name, path in self.files.items():
                if path.exists():
                    contents[name] = self.extract_content_after_header(
                        self.read_file_content(path)
                    )

            if len(contents) < 2:
                return True, []  # Can't compare if we don't have enough files

            # Get the first file's content as reference
            reference_content = next(iter(contents.values()))
            out_of_sync = []

            for name, content in contents.items():
                if content.strip() != reference_content.strip():
                    out_of_sync.append(f"{name.upper()}.md")

            return len(out_of_sync) == 0, out_of_sync

        except Exception:
            # If we can't check, assume they need syncing
            return False, ["Unable to verify sync status"]
