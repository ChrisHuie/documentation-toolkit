"""
Command-line interface for development tools.
"""

import sys
from pathlib import Path

from .validator import ProjectValidator


def main():
    """Main CLI entry point for development tools."""
    project_root = Path(__file__).parent.parent.parent
    validator = ProjectValidator(project_root)

    # Run full validation
    results = validator.validate_all(cleanup=True)
    all_passed = validator.print_results(results)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
