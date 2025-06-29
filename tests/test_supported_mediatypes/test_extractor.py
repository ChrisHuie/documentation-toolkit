"""
Tests for the MediaTypeExtractor class
"""

from unittest.mock import Mock, patch

import pytest

from src.supported_mediatypes.extractor import MediaTypeExtractor


class TestMediaTypeExtractor:
    """Test cases for MediaTypeExtractor."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock()

    @pytest.fixture
    def extractor(self, mock_github_client):
        """Create a MediaTypeExtractor instance with mock client."""
        return MediaTypeExtractor(mock_github_client)

    def test_extract_adapter_name(self, extractor):
        """Test adapter name extraction from file paths."""
        assert (
            extractor._extract_adapter_name("modules/appnexusBidAdapter.js")
            == "appnexus"
        )
        assert (
            extractor._extract_adapter_name("modules/rubiconBidAdapter.js") == "rubicon"
        )
        assert extractor._extract_adapter_name("modules/someOtherFile.js") is None
        assert extractor._extract_adapter_name("invalid/path") is None

    def test_extract_media_types_from_code_with_supported_array(self, extractor):
        """Test extraction when supportedMediaTypes array is present."""
        code = """
        import { BANNER, VIDEO } from '../src/mediaTypes.js';

        export const spec = {
            code: 'example',
            supportedMediaTypes: [BANNER, VIDEO]
        };
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert set(result) == {"banner", "video"}

    def test_extract_media_types_from_imports(self, extractor):
        """Test extraction from import statements."""
        code = """
        import { BANNER, NATIVE } from '../src/mediaTypes.js';

        export const spec = {
            code: 'example'
        };
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert set(result) == {"banner", "native"}
        # Also verify the result is sorted
        assert result == ["banner", "native"]

    def test_extract_media_types_from_references(self, extractor):
        """Test extraction from mediaTypes.* references."""
        code = """
        function buildRequests(bidRequests) {
            bidRequests.forEach(bid => {
                if (bid.mediaTypes.banner) {
                    // Handle banner
                }
                if (bid.mediaTypes.video) {
                    // Handle video
                }
            });
        }
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert set(result) == {"banner", "video"}

    def test_extract_media_types_from_is_bid_request_valid(self, extractor):
        """Test extraction from isBidRequestValid function."""
        code = """
        isBidRequestValid: function(bid) {
            return !!(bid.params.placementId &&
                     (bid.mediaTypes.banner || bid.mediaTypes.native));
        }
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert set(result) == {"banner", "native"}

    def test_extract_media_types_default_banner(self, extractor):
        """Test default banner detection for older adapters."""
        code = """
        function interpretResponse(response) {
            return {
                cpm: response.cpm,
                width: response.width,
                height: response.height,
                ad: response.ad
            };
        }
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert result == ["banner"]

    def test_extract_media_types_all_types(self, extractor):
        """Test extraction with all media types."""
        code = """
        import { BANNER, VIDEO, NATIVE } from '../src/mediaTypes.js';

        export const spec = {
            code: 'example',
            supportedMediaTypes: [BANNER, VIDEO, NATIVE]
        };
        """
        result = extractor._extract_media_types_from_code(code, "example")
        assert set(result) == {"banner", "video", "native"}
        # Verify they are returned in sorted order
        assert result == ["banner", "native", "video"]

    def test_extract_media_types_import_order_independence(self, extractor):
        """Test that import order doesn't affect the result."""
        # Test different import orders
        code1 = "import { VIDEO, BANNER, NATIVE } from '../src/mediaTypes.js';"
        code2 = "import { NATIVE, VIDEO, BANNER } from '../src/mediaTypes.js';"
        code3 = "import { BANNER, NATIVE, VIDEO } from '../src/mediaTypes.js';"

        result1 = extractor._extract_media_types_from_code(code1, "test1")
        result2 = extractor._extract_media_types_from_code(code2, "test2")
        result3 = extractor._extract_media_types_from_code(code3, "test3")

        # All should return the same sorted list
        assert result1 == result2 == result3 == ["banner", "native", "video"]

    def test_extract_media_types_empty(self, extractor):
        """Test extraction when no media types are found."""
        code = """
        export const spec = {
            code: 'example'
        };
        """
        result = extractor._extract_media_types_from_code(code, "")
        assert result == []

    def test_generate_summary(self, extractor):
        """Test summary generation."""
        adapters_data = {
            "adapter1": {"mediaTypes": ["banner"]},
            "adapter2": {"mediaTypes": ["banner", "video"]},
            "adapter3": {"mediaTypes": ["video"]},
            "adapter4": {"mediaTypes": ["banner", "video", "native"]},
        }

        summary = extractor._generate_summary(adapters_data)

        assert summary["total_adapters"] == 4
        assert summary["by_media_type"]["banner"] == 3
        assert summary["by_media_type"]["video"] == 3
        assert summary["by_media_type"]["native"] == 1
        assert summary["by_combination"]["banner"] == 1
        assert summary["by_combination"]["banner, video"] == 1
        assert summary["by_combination"]["video"] == 1
        assert summary["by_combination"]["banner, native, video"] == 1

    def test_media_type_combination_ordering(self, extractor):
        """Test that media type combinations are normalized regardless of order."""
        # Create adapters with same media types but in different orders
        adapters_data = {
            "adapter1": {"mediaTypes": ["banner", "video", "native"]},
            "adapter2": {"mediaTypes": ["video", "native", "banner"]},
            "adapter3": {"mediaTypes": ["native", "banner", "video"]},
            "adapter4": {"mediaTypes": ["video", "banner"]},
            "adapter5": {"mediaTypes": ["banner", "video"]},
        }

        summary = extractor._generate_summary(adapters_data)

        # All three adapters with all media types should be counted as the same combination
        assert summary["by_combination"]["banner, native, video"] == 3
        # Both adapters with banner+video should be counted together
        assert summary["by_combination"]["banner, video"] == 2
        # Should only have 2 different combinations total
        assert len(summary["by_combination"]) == 2

    @patch("src.supported_mediatypes.extractor.get_logger")
    def test_extract_media_types_integration(
        self, mock_logger, extractor, mock_github_client
    ):
        """Test full extraction flow."""
        # Mock the GitHub client response
        mock_github_client.fetch_repository_data.return_value = {
            "files": {
                "modules/appnexusBidAdapter.js": """
                    import { BANNER, VIDEO } from '../src/mediaTypes.js';
                    export const spec = {
                        supportedMediaTypes: [BANNER, VIDEO]
                    };
                """,
                "modules/rubiconBidAdapter.js": """
                    import { BANNER, VIDEO, NATIVE } from '../src/mediaTypes.js';
                    export const spec = {
                        supportedMediaTypes: [BANNER, VIDEO, NATIVE]
                    };
                """,
            }
        }

        result = extractor.extract_media_types("prebid/Prebid.js", "v9.0.0")

        assert result["version"] == "v9.0.0"
        assert result["total_adapters"] == 2
        assert result["adapters_with_media_types"] == 2
        assert "appnexus" in result["adapters"]
        assert set(result["adapters"]["appnexus"]["mediaTypes"]) == {"banner", "video"}
        assert "rubicon" in result["adapters"]
        assert set(result["adapters"]["rubicon"]["mediaTypes"]) == {
            "banner",
            "video",
            "native",
        }

    def test_extract_media_types_specific_adapter(self, extractor, mock_github_client):
        """Test extraction for a specific adapter."""
        mock_github_client.fetch_repository_data.return_value = {
            "files": {
                "modules/appnexusBidAdapter.js": """
                    import { BANNER } from '../src/mediaTypes.js';
                    export const spec = {
                        supportedMediaTypes: [BANNER]
                    };
                """
            }
        }

        result = extractor.extract_media_types(
            "prebid/Prebid.js", "v9.0.0", specific_adapter="appnexus"
        )

        assert result["total_adapters"] == 1
        assert "appnexus" in result["adapters"]
        assert result["adapters"]["appnexus"]["mediaTypes"] == ["banner"]
