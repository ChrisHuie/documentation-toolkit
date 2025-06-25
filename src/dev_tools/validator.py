"""
Project validation utilities.

Handles code formatting, linting, type checking, testing, and documentation updates.
"""

import datetime
import subprocess
from pathlib import Path

from .cleanup import ProjectCleaner
from .docs_sync import DocumentationSyncer


class ValidationResult:
    """Result of a validation step."""

    def __init__(
        self, name: str, passed: bool, output: str = "", critical: bool = True
    ):
        self.name = name
        self.passed = passed
        self.output = output
        self.critical = critical

    def __str__(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        criticality = "" if self.critical else " (non-critical)"
        return f"{status} {self.name}{criticality}"


class ProjectValidator:
    """Comprehensive project validation and maintenance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cleaner = ProjectCleaner(project_root)
        self.syncer = DocumentationSyncer(project_root)

    def run_command(self, cmd: list[str], description: str) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root, check=False
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def format_code(self) -> list[ValidationResult]:
        """Format code with ruff and black."""
        results = []

        # Ruff formatting
        success, output = self.run_command(
            ["uv", "run", "ruff", "format", "."], "Formatting with ruff"
        )
        results.append(
            ValidationResult("Code formatting (ruff)", success, output, critical=True)
        )

        # Black formatting (backup)
        success, output = self.run_command(
            ["uv", "run", "black", "."], "Formatting with black"
        )
        results.append(
            ValidationResult("Code formatting (black)", success, output, critical=False)
        )

        return results

    def lint_code(self) -> ValidationResult:
        """Run linting with ruff."""
        success, output = self.run_command(
            ["uv", "run", "ruff", "check", "."], "Linting with ruff"
        )
        return ValidationResult("Code linting", success, output, critical=True)

    def type_check(self) -> ValidationResult:
        """Run type checking with mypy."""
        success, output = self.run_command(
            ["uv", "run", "mypy", "src/"], "Type checking with mypy"
        )
        return ValidationResult("Type checking", success, output, critical=False)

    def run_tests(self) -> ValidationResult:
        """Run tests with pytest."""
        success, output = self.run_command(
            ["uv", "run", "pytest", "-v"], "Running tests"
        )
        return ValidationResult("Tests", success, output, critical=False)

    def update_readme_timestamp(self) -> ValidationResult:
        """Update README.md with current timestamp."""
        readme_path = self.project_root / "README.md"

        try:
            if not readme_path.exists():
                return ValidationResult(
                    "README update", False, "README.md not found", critical=True
                )

            content = readme_path.read_text()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if "Last updated:" in content:
                # Update existing timestamp
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("Last updated:"):
                        lines[i] = f"Last updated: {timestamp}"
                        break
                content = "\n".join(lines)
            else:
                # Add timestamp at the end
                content += f"\n\nLast updated: {timestamp}\n"

            readme_path.write_text(content)
            return ValidationResult(
                "README timestamp update", True, f"Updated to {timestamp}"
            )

        except Exception as e:
            return ValidationResult("README update", False, str(e), critical=True)

    def sync_documentation(self) -> ValidationResult:
        """Sync agent documentation files."""
        try:
            results = self.syncer.sync()
            updated_files = [name for name, updated in results.items() if updated]

            if updated_files:
                output = f"Updated files: {', '.join(updated_files)}"
            else:
                output = "All files already in sync"

            return ValidationResult("Documentation sync", True, output)

        except Exception as e:
            return ValidationResult("Documentation sync", False, str(e), critical=True)

    def cleanup_artifacts(self, dry_run: bool = False) -> ValidationResult:
        """Clean up project artifacts."""
        try:
            removed = self.cleaner.clean(dry_run=dry_run)

            if removed:
                action = "Would remove" if dry_run else "Removed"
                output = f"{action} {len(removed)} artifacts: {', '.join(str(p.name) for p in removed[:5])}"
                if len(removed) > 5:
                    output += f" and {len(removed) - 5} more"
            else:
                output = "No artifacts to clean"

            return ValidationResult("Artifact cleanup", True, output, critical=False)

        except Exception as e:
            return ValidationResult("Artifact cleanup", False, str(e), critical=False)

    def validate_all(self, cleanup: bool = True) -> dict[str, list[ValidationResult]]:
        """
        Run all validation steps.

        Args:
            cleanup: Whether to clean up artifacts.

        Returns:
            Dictionary of validation results grouped by category.
        """
        results = {}

        # Cleanup first (optional)
        if cleanup:
            results["cleanup"] = [self.cleanup_artifacts()]

        # Code quality
        results["formatting"] = self.format_code()
        results["linting"] = [self.lint_code()]
        results["type_checking"] = [self.type_check()]
        results["testing"] = [self.run_tests()]

        # Documentation
        results["documentation"] = [
            self.update_readme_timestamp(),
            self.sync_documentation(),
        ]

        return results

    def print_results(self, results: dict[str, list[ValidationResult]]) -> bool:
        """
        Print validation results in a nice format.

        Returns:
            True if all critical validations passed.
        """
        all_critical_passed = True

        print("🚀 Project Validation Results\n")

        for category, category_results in results.items():
            print(f"📋 {category.title().replace('_', ' ')}")
            print("-" * 40)

            for result in category_results:
                print(f"   {result}")
                if result.output and not result.passed:
                    # Show first few lines of error output
                    lines = result.output.split("\n")[:3]
                    for line in lines:
                        if line.strip():
                            print(f"      {line}")

                if not result.passed and result.critical:
                    all_critical_passed = False

            print()

        print("=" * 50)
        if all_critical_passed:
            print("🎉 All critical validations passed!")
        else:
            print("💥 Some critical validations failed. Please review and fix.")

        return all_critical_passed
