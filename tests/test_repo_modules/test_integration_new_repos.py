"""
Integration tests for new repository configurations and parsers added on addFilesToParse branch.

This test suite validates:
- All new repo configurations (prebid-server, prebid-server-java, prebid-docs)
- New parser implementations (PrebidServerGoParser, PrebidServerJavaParser, PrebidDocsParser)
- Updated naming conventions and filename generation
- Multi-path parsing functionality
- Underscore to space conversion
- Master override for prebid.github.io
"""

from src.repo_modules_by_version.config import RepoConfig, get_available_repos
from src.repo_modules_by_version.parser_factory import (
    ParserFactory,
    PrebidDocsParser,
    PrebidJSParser,
    PrebidServerGoParser,
    PrebidServerJavaParser,
)


class TestNewRepoConfigurations:
    """Test all new repository configurations."""

    def test_all_prebid_repos_exist(self):
        """Test that all expected Prebid repositories are configured."""
        repos = get_available_repos()

        expected_repos = {
            "prebid-js",
            "prebid-server",
            "prebid-server-java",
            "prebid-docs",
        }

        assert expected_repos.issubset(
            set(repos.keys())
        ), f"Missing repos: {expected_repos - set(repos.keys())}"

    def test_prebid_js_config(self):
        """Test Prebid.js repository configuration."""
        repos = get_available_repos()
        config = repos["prebid-js"]

        assert config.repo == "prebid/Prebid.js"
        assert config.parser_type == "prebid_js"
        assert config.modules_path == "modules"
        assert "master" in config.versions

    def test_prebid_server_go_config(self):
        """Test Prebid Server Go repository configuration."""
        repos = get_available_repos()
        config = repos["prebid-server"]

        assert config.repo == "prebid/prebid-server"
        assert config.parser_type == "prebid_server_go"
        assert config.paths is not None
        assert "Bid Adapters" in config.paths
        assert "Analytics Adapters" in config.paths
        assert "General Modules" in config.paths
        assert config.paths["Bid Adapters"] == "adapters"

    def test_prebid_server_java_config(self):
        """Test Prebid Server Java repository configuration."""
        repos = get_available_repos()
        config = repos["prebid-server-java"]

        assert config.repo == "prebid/prebid-server-java"
        assert config.parser_type == "prebid_server_java"
        assert config.paths is not None
        assert "Privacy Modules" in config.paths
        assert "General Modules" in config.paths

    def test_prebid_docs_config(self):
        """Test Prebid Documentation repository configuration."""
        repos = get_available_repos()
        config = repos["prebid-docs"]

        assert config.repo == "prebid/prebid.github.io"
        assert config.parser_type == "prebid_docs"
        assert config.paths is not None
        assert "Identity Modules" in config.paths
        assert "Real-Time Data Modules" in config.paths
        assert "Video Modules" in config.paths


class TestParserFactory:
    """Test parser factory with new parser types."""

    def test_parser_factory_creates_correct_parsers(self):
        """Test that parser factory creates the correct parser instances."""
        factory = ParserFactory()

        # Test all new parser types
        test_cases = [
            ("prebid_js", PrebidJSParser),
            ("prebid_server_go", PrebidServerGoParser),
            ("prebid_server_java", PrebidServerJavaParser),
            ("prebid_docs", PrebidDocsParser),
        ]

        for parser_type, expected_class in test_cases:
            config = RepoConfig(
                repo="test/repo",
                description="Test",
                versions=["master"],
                parser_type=parser_type,
            )

            parser = factory.get_parser(config)
            assert isinstance(
                parser, expected_class
            ), f"Expected {expected_class.__name__} for {parser_type}, got {type(parser).__name__}"

    def test_parser_factory_available_parsers(self):
        """Test that all new parser types are available."""
        factory = ParserFactory()
        available = factory.get_available_parsers()

        expected_parsers = {
            "prebid_js",
            "prebid_server_go",
            "prebid_server_java",
            "prebid_docs",
        }

        assert expected_parsers.issubset(
            set(available)
        ), f"Missing parsers: {expected_parsers - set(available)}"


class TestUnderscoreToSpaceConversion:
    """Test underscore to space conversion in parser outputs."""

    def test_prebid_server_go_underscore_conversion(self):
        """Test that PrebidServerGoParser converts underscores to spaces."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={"Bid Adapters": "adapters"},
        )
        parser = PrebidServerGoParser(config)

        # Mock data with underscores
        test_data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {
                "adapters": {
                    "adapters/test_adapter": "",
                    "adapters/another_test": "",
                    "adapters/normal": "",
                }
            },
        }

        result = parser.parse(test_data)

        # Check that underscores are converted to spaces
        assert "test adapter" in result
        assert "another test" in result
        assert "normal" in result
        assert "test_adapter" not in result
        assert "another_test" not in result

    def test_prebid_server_java_underscore_conversion(self):
        """Test that PrebidServerJavaParser handles naming correctly."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={"General Modules": "extra/modules"},
        )
        parser = PrebidServerJavaParser(config)

        # Mock data with dashes and pb- prefix
        test_data = {
            "repo": "prebid/prebid-server-java",
            "version": "master",
            "paths": {
                "extra/modules": {
                    "extra/modules/pb-test-module": "",
                    "extra/modules/another-module": "",
                }
            },
        }

        result = parser.parse(test_data)

        # Check that dashes are converted to spaces and pb- prefix is removed
        assert "test module" in result
        assert "another module" in result
        assert "pb-test-module" not in result


class TestMultiPathParsing:
    """Test multi-path parsing functionality."""

    def test_prebid_server_go_multi_path_parsing(self):
        """Test that PrebidServerGoParser handles multiple paths correctly."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={
                "Bid Adapters": "adapters",
                "Analytics Adapters": "analytics",
                "General Modules": "modules",
            },
        )
        parser = PrebidServerGoParser(config)

        test_data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {
                "adapters": {
                    "adapters/appnexus": "",
                    "adapters/rubicon": "",
                },
                "analytics": {
                    "analytics/pubstack": "",
                    "analytics/build": "",  # Should be excluded
                },
                "modules": {
                    "modules/fiftyonedegrees": "",
                    "modules/fiftyonedegrees/devicedetection": "",
                },
            },
        }

        result = parser.parse(test_data)

        # Check all categories appear
        assert "📦 Bid Adapters" in result
        assert "📦 Analytics Adapters" in result
        assert "📦 General Modules" in result

        # Check correct items appear
        assert "appnexus" in result
        assert "rubicon" in result
        assert "pubstack" in result
        assert "fiftyonedegrees devicedetection" in result

        # Check excluded items don't appear
        assert "build" not in result

    def test_prebid_docs_multi_path_parsing(self):
        """Test that PrebidDocsParser handles file-based parsing correctly."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Test",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Real-Time Data Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        test_data = {
            "repo": "prebid/prebid.github.io",
            "version": "master",
            "paths": {
                "dev-docs/bidders": {
                    "dev-docs/bidders/appnexus.md": "",
                    "dev-docs/bidders/rubicon.md": "",
                },
                "dev-docs/modules": {
                    "dev-docs/modules/confiantRtdProvider.md": "",
                    "dev-docs/modules/currency.md": "",
                },
            },
        }

        result = parser.parse(test_data)

        # Check categories appear
        assert "📦 Bid Adapters" in result
        assert "📦 Real-Time Data Modules" in result

        # Check suffix removal works
        assert "confiant" in result  # RtdProvider removed
        assert "confiantRtdProvider" not in result

        # Note: currency.md doesn't have a special suffix, so it won't appear in RTD modules
        # The parser only categorizes files with specific suffixes in the RTD category


class TestDisplayNamingConsistency:
    """Test that display names follow consistent naming conventions."""

    def test_prebid_js_display_name(self):
        """Test PrebidJSParser display name."""
        config = RepoConfig(
            repo="prebid/Prebid.js",
            description="Test",
            versions=["master"],
            parser_type="prebid_js",
            modules_path="modules",
        )
        parser = PrebidJSParser(config)

        test_data = {
            "repo": "prebid/Prebid.js",
            "version": "master",
            "directory": "modules",
            "files": {"modules/testBidAdapter.js": ""},
            "metadata": {"total_files": 1},
        }

        result = parser.parse(test_data)
        assert "Prebid.js Module Categories:" in result

    def test_prebid_server_go_display_name(self):
        """Test PrebidServerGoParser display name."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={"Bid Adapters": "adapters"},
        )
        parser = PrebidServerGoParser(config)

        test_data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {"adapters": {"adapters/test": ""}},
        }

        result = parser.parse(test_data)
        assert "Prebid Server Go Categories:" in result

    def test_prebid_server_java_display_name(self):
        """Test PrebidServerJavaParser display name."""
        config = RepoConfig(
            repo="prebid/prebid-server-java",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_java",
            paths={"Bid Adapters": "src/main/java/org/prebid/server/bidder"},
        )
        parser = PrebidServerJavaParser(config)

        test_data = {
            "repo": "prebid/prebid-server-java",
            "version": "master",
            "paths": {
                "src/main/java/org/prebid/server/bidder": {
                    "src/main/java/org/prebid/server/bidder/test": ""
                }
            },
        }

        result = parser.parse(test_data)
        assert "Prebid Server Java Categories:" in result

    def test_prebid_docs_display_name(self):
        """Test PrebidDocsParser display name."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Test",
            versions=["master"],
            parser_type="prebid_docs",
            paths={"Bid Adapters": "dev-docs/bidders"},
        )
        parser = PrebidDocsParser(config)

        test_data = {
            "repo": "prebid/prebid.github.io",
            "version": "master",
            "paths": {"dev-docs/bidders": {"dev-docs/bidders/test.md": ""}},
        }

        result = parser.parse(test_data)
        assert "Prebid Documentation Categories:" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_data_handling(self):
        """Test parsers handle empty data gracefully."""
        parsers = [
            ("prebid_js", PrebidJSParser),
            ("prebid_server_go", PrebidServerGoParser),
            ("prebid_server_java", PrebidServerJavaParser),
            ("prebid_docs", PrebidDocsParser),
        ]

        for parser_type, parser_class in parsers:
            config = RepoConfig(
                repo="test/repo",
                description="Test",
                versions=["master"],
                parser_type=parser_type,
                paths={"Test": "test"} if parser_type != "prebid_js" else None,
                modules_path="modules" if parser_type == "prebid_js" else None,
            )
            parser = parser_class(config)

            # Test with empty data
            if parser_type == "prebid_js":
                empty_data = {
                    "repo": "test/repo",
                    "version": "master",
                    "directory": "modules",
                    "files": {},
                    "metadata": {"total_files": 0},
                }
            else:
                empty_data = {"repo": "test/repo", "version": "master", "paths": {}}

            # Should not crash
            result = parser.parse(empty_data)
            assert isinstance(result, str)
            assert "test/repo" in result

    def test_malformed_file_paths(self):
        """Test parsers handle malformed file paths gracefully."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={"Bid Adapters": "adapters"},
        )
        parser = PrebidServerGoParser(config)

        # Test with malformed paths
        test_data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {
                "adapters": {
                    "adapters/": "",  # Empty adapter name
                    "adapters": "",  # No subdirectory
                    "adapters/valid": "",  # Valid
                }
            },
        }

        result = parser.parse(test_data)

        # Should handle gracefully and include valid entries
        assert "valid" in result
        # Should not crash on malformed entries

    def test_general_modules_filtering(self):
        """Test that General Modules filtering works correctly for PrebidServerGoParser."""
        config = RepoConfig(
            repo="prebid/prebid-server",
            description="Test",
            versions=["master"],
            parser_type="prebid_server_go",
            paths={"General Modules": "modules"},
        )
        parser = PrebidServerGoParser(config)

        test_data = {
            "repo": "prebid/prebid-server",
            "version": "master",
            "paths": {
                "modules": {
                    "modules/single": "",  # Should be excluded (no subdirectory)
                    "modules/valid/subdir": "",  # Should be included
                    "modules/another/sub/deep": "",  # Should be included
                }
            },
        }

        result = parser.parse(test_data)

        # Should only include modules with subdirectories
        assert "valid subdir" in result
        assert "another sub" in result
        assert "single" not in result
