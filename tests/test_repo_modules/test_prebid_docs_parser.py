"""
Tests for the PrebidDocsParser
"""

from src.repo_modules_by_version.config import RepoConfig
from src.repo_modules_by_version.parser_factory import PrebidDocsParser


class TestPrebidDocsParser:
    """Test suite for PrebidDocsParser."""

    def test_prebid_docs_parser_creation(self):
        """Test that PrebidDocsParser can be created with proper config."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)
        assert parser.config == config

    def test_prebid_docs_parser_categorize_bid_adapters(self):
        """Test categorizing bid adapters from documentation files."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for bid adapters
        files = {
            "dev-docs/bidders/appnexus.md": "",
            "dev-docs/bidders/rubicon.md": "",
            "dev-docs/bidders/pubmatic.md": "",
        }

        result = parser._categorize_by_path("Bid Adapters", "dev-docs/bidders", files)

        assert "Bid Adapters" in result
        assert set(result["Bid Adapters"]) == {"appnexus", "rubicon", "pubmatic"}

    def test_prebid_docs_parser_categorize_analytics_adapters(self):
        """Test categorizing analytics adapters from documentation files."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for analytics adapters
        files = {
            "dev-docs/analytics/pubstack.md": "",
            "dev-docs/analytics/agma.md": "",
            "dev-docs/analytics/generic.md": "",
        }

        result = parser._categorize_by_path(
            "Analytics Adapters", "dev-docs/analytics", files
        )

        assert "Analytics Adapters" in result
        assert set(result["Analytics Adapters"]) == {"pubstack", "agma", "generic"}

    def test_prebid_docs_parser_categorize_identity_modules(self):
        """Test categorizing identity modules from documentation files."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for identity modules
        files = {
            "dev-docs/modules/userid-submodules/id5.md": "",
            "dev-docs/modules/userid-submodules/liveintent.md": "",
            "dev-docs/modules/userid-submodules/criteo.md": "",
        }

        result = parser._categorize_by_path(
            "Identity Modules", "dev-docs/modules/userid-submodules", files
        )

        assert "Identity Modules" in result
        assert set(result["Identity Modules"]) == {"id5", "liveintent", "criteo"}

    def test_prebid_docs_parser_categorize_rtd_modules(self):
        """Test categorizing Real-Time Data modules with proper suffix removal."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for RTD modules
        files = {
            "dev-docs/modules/confiantRtdProvider.md": "",
            "dev-docs/modules/greenbidsRtdProvider.md": "",
            "dev-docs/modules/51DegreesRtdProvider.md": "",
        }

        result = parser._categorize_by_path(
            "Real-Time Data Modules", "dev-docs/modules", files
        )

        assert "Real-Time Data Modules" in result
        assert set(result["Real-Time Data Modules"]) == {
            "confiant",
            "greenbids",
            "51Degrees",
        }

    def test_prebid_docs_parser_categorize_video_modules(self):
        """Test categorizing Video modules with proper suffix removal."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for Video modules
        files = {
            "dev-docs/modules/jwplayerVideoProvider.md": "",
            "dev-docs/modules/videojsVideoProvider.md": "",
        }

        result = parser._categorize_by_path("Video Modules", "dev-docs/modules", files)

        assert "Video Modules" in result
        assert set(result["Video Modules"]) == {"jwplayer", "videojs"}

    def test_prebid_docs_parser_categorize_other_modules(self):
        """Test categorizing Other modules (no special suffix)."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock data for other modules
        files = {
            "dev-docs/modules/currency.md": "",
            "dev-docs/modules/floors.md": "",
            "dev-docs/modules/debugging.md": "",
        }

        result = parser._categorize_by_path("Other Modules", "dev-docs/modules", files)

        assert "Other Modules" in result
        assert set(result["Other Modules"]) == {"currency", "floors", "debugging"}

    def test_prebid_docs_parser_parse_full_data(self):
        """Test parsing complete data structure."""
        config = RepoConfig(
            repo="prebid/prebid.github.io",
            description="Prebid documentation site",
            versions=["master"],
            parser_type="prebid_docs",
            paths={
                "Bid Adapters": "dev-docs/bidders",
                "Analytics Adapters": "dev-docs/analytics",
                "Identity Modules": "dev-docs/modules/userid-submodules",
                "Real-Time Data Modules": "dev-docs/modules",
                "Video Modules": "dev-docs/modules",
                "Other Modules": "dev-docs/modules",
            },
        )
        parser = PrebidDocsParser(config)

        # Mock complete data structure
        data = {
            "repo": "prebid/prebid.github.io",
            "version": "master",
            "paths": {
                "dev-docs/bidders": {
                    "dev-docs/bidders/appnexus.md": "",
                    "dev-docs/bidders/rubicon.md": "",
                },
                "dev-docs/analytics": {
                    "dev-docs/analytics/pubstack.md": "",
                    "dev-docs/analytics/agma.md": "",
                },
                "dev-docs/modules/userid-submodules": {
                    "dev-docs/modules/userid-submodules/id5.md": "",
                },
                "dev-docs/modules": {
                    "dev-docs/modules/confiantRtdProvider.md": "",
                    "dev-docs/modules/currency.md": "",
                },
            },
        }

        result = parser.parse(data)

        # Verify the output contains all sections
        assert "Repository: prebid/prebid.github.io" in result
        assert "Version: master" in result
        assert "Prebid Documentation Categories:" in result
        assert "📦 Bid Adapters" in result
        assert "📦 Analytics Adapters" in result
        assert "📦 Identity Modules" in result
        assert "📦 Real-Time Data Modules" in result
        assert "📦 Other Modules" in result
        assert "JSON Output:" in result

        # Verify specific content
        assert "appnexus" in result
        assert "rubicon" in result
        assert "pubstack" in result
        assert "agma" in result
        assert "id5" in result
        assert "confiant" in result  # Should have RtdProvider removed
        assert "currency" in result
