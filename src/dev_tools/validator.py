"""
Project validation utilities.

Handles code formatting, linting, type checking, testing, and documentation updates.
"""

import datetime
import subprocess
from pathlib import Path

from ..shared_utilities import get_logger
from .docs_sync import DocumentationSyncer


class ValidationResult:
    """Result of a validation step."""

    def __init__(self, name: str, passed: bool, output: str = ""):
        self.name = name
        self.passed = passed
        self.output = output

    def __str__(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return f"{status} {self.name}"


class ProjectValidator:
    """Comprehensive project validation and maintenance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.syncer = DocumentationSyncer(project_root)
        self.logger = get_logger(__name__)

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
        results.append(ValidationResult("Code formatting (ruff)", success, output))

        # Black formatting (backup)
        success, output = self.run_command(
            ["uv", "run", "black", "."], "Formatting with black"
        )
        results.append(ValidationResult("Code formatting (black)", success, output))

        return results

    def lint_code(self) -> ValidationResult:
        """Run linting with ruff."""
        success, output = self.run_command(
            ["uv", "run", "ruff", "check", "."], "Linting with ruff"
        )
        return ValidationResult("Code linting", success, output)

    def type_check(self) -> ValidationResult:
        """Run type checking with mypy."""
        success, output = self.run_command(
            ["uv", "run", "mypy", "src/"], "Type checking with mypy"
        )
        return ValidationResult("Type checking", success, output)

    def run_tests(self) -> ValidationResult:
        """Run tests with pytest."""
        success, output = self.run_command(
            ["uv", "run", "pytest", "-v"], "Running tests"
        )
        return ValidationResult("Tests", success, output)

    def update_readme_timestamp(self) -> ValidationResult:
        """Update README.md with current timestamp."""
        readme_path = self.project_root / "README.md"

        try:
            if not readme_path.exists():
                return ValidationResult("README update", False, "README.md not found")

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
            return ValidationResult("README update", False, str(e))

    def sync_documentation(self) -> ValidationResult:
        """Sync agent documentation files."""
        try:
<<<<<<< HEAD
            self.logger.info("Starting documentation sync")
            results = self.syncer.sync()
            updated_files = [name for name, updated in results.items() if updated]
            total_files = len(results)

            # Log detailed sync results
            for name, updated in results.items():
                self.logger.info(
                    "Documentation file sync",
                    file=f"{name.upper()}.md",
                    updated=updated,
                )

            if updated_files:
                output = f"Updated {len(updated_files)}/{total_files} files: {', '.join(f'{name.upper()}.md' for name in updated_files)}"
                self.logger.info(
                    "Documentation sync completed",
                    updated_count=len(updated_files),
                    total_count=total_files,
                    updated_files=[f"{name.upper()}.md" for name in updated_files],
                )
            else:
                output = f"All {total_files} agent files already in sync"
                self.logger.info(
                    "Documentation sync completed",
                    updated_count=0,
                    total_count=total_files,
                    status="all_in_sync",
                )
=======
            print("\n📚 Syncing agent documentation files...")
            results = self.syncer.sync()
            updated_files = [name for name, updated in results.items() if updated]
            total_files = len(results)
            synced_files = len(updated_files)

            if updated_files:
                output = f"Updated {synced_files}/{total_files} files: {', '.join(f'{name.upper()}.md' for name in updated_files)}"
                print(f"✅ Documentation sync completed: {output}")
            else:
                output = f"All {total_files} agent files already in sync"
                print(f"✅ Documentation sync completed: {output}")
>>>>>>> main

            return ValidationResult("Documentation sync", True, output)

        except Exception as e:
<<<<<<< HEAD
            self.logger.error(
                "Documentation sync failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return ValidationResult("Documentation sync", False, str(e))
=======
            error_msg = f"Documentation sync failed: {str(e)}"
            print(f"❌ {error_msg}")
            return ValidationResult("Documentation sync", False, error_msg)
>>>>>>> main

    # Cleanup functionality removed for safety - manual cleanup only

    def validate_all(self) -> dict[str, list[ValidationResult]]:
        """
        Run all validation steps.

        Returns:
            Dictionary of validation results grouped by category.
        """
        results = {}

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
        Log validation results and display summary.

        Returns:
            True if all validations passed.
        """
        all_passed = True
        critical_failed = False

<<<<<<< HEAD
        # Log structured results for each category
=======
        print("\n🚀 Project Validation Results\n")

>>>>>>> main
        for category, category_results in results.items():
            for result in category_results:
                self.logger.info(
                    "Validation result",
                    category=category,
                    validation=result.name,
                    passed=result.passed,
                    output=result.output if not result.passed else None,
                )

                if not result.passed:
                    all_passed = False
                    # Mark critical categories that should always pass
                    if category in ["formatting", "linting", "documentation"]:
                        critical_failed = True

        # Log overall validation summary
        self.logger.info(
            "Validation summary",
            total_categories=len(results),
            all_passed=all_passed,
            critical_failed=critical_failed,
        )

<<<<<<< HEAD
        # Display user-friendly console output (minimal)
        if all_passed:
            print("🎉 All validations passed!")
            print(
                "📝 Documentation sync keeps CLAUDE.md, AGENTS.md, and GEMINI.md in sync"
=======
        print("=" * 60)
        if all_passed:
            print("🎉 All validations passed!")
            print(
                "\n📝 Remember: Documentation sync keeps CLAUDE.md, AGENTS.md, and GEMINI.md in sync"
>>>>>>> main
            )
        else:
            if critical_failed:
                print(
                    "💥 CRITICAL validations failed. These must be fixed before proceeding:"
                )
                print("   - Formatting errors prevent consistent code style")
                print("   - Linting errors indicate code quality issues")
                print("   - Documentation sync failures cause agent instruction drift")
            else:
                print("⚠️  Some non-critical validations failed (type checking/tests).")
                print("   These should be addressed but don't block development.")

<<<<<<< HEAD
            print("📝 Always run 'validate-project' after making changes!")
=======
            print("\n📝 Always run 'validate-project' after making changes!")
>>>>>>> main

        return all_passed
