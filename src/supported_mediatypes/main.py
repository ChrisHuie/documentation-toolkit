#!/usr/bin/env python3
"""
Supported MediaTypes CLI - Extract media types from Prebid.js bid adapters
"""

import argparse
import sys

from dotenv import load_dotenv

from ..shared_utilities import cleanup_active_tools, get_logger
from ..shared_utilities.filename_generator import generate_output_filename
from ..shared_utilities.github_client import GitHubClient
from ..shared_utilities.output_manager import OutputManager
from ..shared_utilities.repository_config import RepositoryConfigManager
from .extractor import MediaTypeExtractor
from .output_formatter import MediaTypeOutputFormatter

# Initialize environment and logging
load_dotenv()
logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract supported media types from Prebid.js bid adapters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        type=str,
        help="Prebid.js version to analyze (e.g., v9.51.0). If not specified, uses latest.",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "csv", "markdown", "yaml", "html"],
        default="table",
        help="Output format (default: table)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (optional, defaults to stdout for table or generated filename for json/csv)",
    )

    parser.add_argument(
        "--adapter",
        type=str,
        help="Analyze only a specific adapter (e.g., appnexus)",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary statistics of media type usage",
    )

    parser.add_argument(
        "--show-json",
        action="store_true",
        help="Include JSON representation at the bottom of table output",
    )

    return parser


def main() -> int:
    """Main entry point for the supported_mediatypes tool."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Initialize components
        config_manager = RepositoryConfigManager()
        github_client = GitHubClient()
        extractor = MediaTypeExtractor(github_client)
        formatter = MediaTypeOutputFormatter()
        output_manager = OutputManager()

        # Get Prebid.js configuration
        repo_config = config_manager.get_config("prebid-js")
        repo_name = repo_config["repo"]

        # Determine version to use
        if args.version:
            version = args.version
        else:
            # Get latest version
            versions = github_client.get_semantic_versions(repo_name)
            if not versions:
                logger.error("No versions found for Prebid.js")
                return 1
            # First version after master/main is the latest
            version = versions[1].split(" ")[0] if len(versions) > 1 else versions[0]
            logger.info(f"Using latest version: {version}")

        # Extract media types
        logger.info(f"Extracting media types from {repo_name} @ {version}")
        media_types_data = extractor.extract_media_types(
            repo_name, version, specific_adapter=args.adapter
        )

        if not media_types_data["adapters"]:
            logger.warning("No adapters found or no media types extracted")
            return 1

        # Format output using the new extensible formatter
        if args.format == "table" and not args.output:
            # Special case: table format to stdout
            output = formatter.format(
                media_types_data,
                args.format,
                show_summary=args.summary,
                show_json=args.show_json,
            )
            print(output)
        else:
            # All other cases: save to file
            if args.output:
                output_path = args.output
            else:
                # Generate default filename based on format
                extension = args.format if args.format != "table" else "txt"
                filename = generate_output_filename(
                    repo_name,
                    version,
                    "supported_mediatypes",
                    custom_slug="prebid.js",
                    extension=extension,
                )

                # Use output manager to get hierarchical path
                output_path = output_manager.get_output_path(
                    tool_name="supported-mediatypes",
                    repo_name=repo_name,
                    version=version,
                    filename=filename,
                )

            # Save using the formatter
            formatter.save(
                media_types_data, output_path, args.format, show_summary=args.summary
            )
            logger.info(f"{args.format.upper()} output written to {output_path}")

        # Clean up any empty directories
        output_manager.cleanup_empty_directories("supported-mediatypes")

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    finally:
        # Clean up empty directories for tools used in this session
        cleanup_active_tools()


if __name__ == "__main__":
    sys.exit(main())
