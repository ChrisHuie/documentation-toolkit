"""
Documentation synchronization utilities.

Keeps agent instruction files (CLAUDE.md, AGENTS.md, GEMINI.md) in sync.
"""

from pathlib import Path


class DocumentationSyncer:
    """Synchronizes agent instruction files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.files = {
            "claude": self.project_root / "CLAUDE.md",
            "agents": self.project_root / "AGENTS.md",
            "gemini": self.project_root / "GEMINI.md",
        }
        self.headers = {
            "claude": "# Claude Instructions\n\nThis file contains instructions and context for Claude when working on this project.",
            "agents": "# Claude Instructions\n\nThis file contains instructions and context for Claude when working on this project.",
            "gemini": "# Gemini Instructions\n\nThis file contains instructions and context for Gemini when working on this project.",
        }

    def read_file_content(self, file_path: Path) -> str:
        """Read file content, returning empty string if file doesn't exist."""
        try:
            return file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def extract_content_after_header(self, content: str) -> str:
        """Extract content after the first heading, preserving everything else."""
        lines = content.split("\n")
        if not lines:
            return ""

        # Skip the first line (title) and any empty lines after it
        content_start = 1
        while content_start < len(lines) and not lines[content_start].strip():
            content_start += 1

        return "\n".join(lines[content_start:])

    def create_file_with_header(self, header: str, content: str) -> str:
        """Create file content with specified header and shared content."""
        return f"{header}\n\n{content}"

    def sync(self) -> dict[str, bool]:
        """
        Sync all documentation files.

        Returns:
            Dict mapping file names to whether they were updated.
        """
        results = {}

        # Read all files
        contents = {}
        for name, path in self.files.items():
            contents[name] = self.read_file_content(path)

        # Find the most recently modified file with content
        most_recent = None
        most_recent_time = 0

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

        # Update all files with the shared content
        for name, path in self.files.items():
            new_content = self.create_file_with_header(
                self.headers[name], shared_content
            )

            # Only write if content has changed
            if contents[name] != new_content:
                path.write_text(new_content, encoding="utf-8")
                results[name] = True
            else:
                results[name] = False

        return results
