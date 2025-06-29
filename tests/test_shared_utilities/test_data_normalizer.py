"""
Tests for the data normalizer utility
"""

from src.shared_utilities.data_normalizer import DataNormalizer


class TestDataNormalizer:
    """Test cases for DataNormalizer."""

    def test_normalize_with_percentages_raw_counts(self):
        """Test normalizing raw count data."""
        data = {
            "version": "v1.0.0",
            "total_adapters": 5,
            "adapters_with_media_types": 5,
            "adapters": {"test": {"mediaTypes": ["banner"]}},
            "summary": {
                "total_adapters": 5,
                "by_media_type": {"banner": 4, "video": 3, "native": 2},
                "by_combination": {
                    "banner": 2,
                    "banner, video": 2,
                    "banner, video, native": 1,
                },
            },
        }

        normalized = DataNormalizer.normalize_with_percentages(data)

        # Check media type percentages
        assert normalized["summary"]["by_media_type"]["banner"]["count"] == 4
        assert normalized["summary"]["by_media_type"]["banner"]["percentage"] == 80.0
        assert normalized["summary"]["by_media_type"]["video"]["percentage"] == 60.0
        assert normalized["summary"]["by_media_type"]["native"]["percentage"] == 40.0

        # Check combination percentages
        assert normalized["summary"]["by_combination"]["banner"]["percentage"] == 40.0
        assert (
            normalized["summary"]["by_combination"]["banner, video"]["percentage"]
            == 40.0
        )
        assert (
            normalized["summary"]["by_combination"]["banner, video, native"][
                "percentage"
            ]
            == 20.0
        )

    def test_normalize_already_normalized_data(self):
        """Test that already normalized data is not re-normalized."""
        data = {
            "version": "v1.0.0",
            "summary": {
                "total_adapters": 2,
                "by_media_type": {
                    "banner": {"count": 2, "percentage": 100.0},
                    "video": {"count": 1, "percentage": 50.0},
                },
                "by_combination": {
                    "banner": {"count": 1, "percentage": 50.0},
                    "banner, video": {"count": 1, "percentage": 50.0},
                },
            },
        }

        normalized = DataNormalizer.normalize_with_percentages(data)

        # Should remain the same
        assert normalized["summary"]["by_media_type"]["banner"]["percentage"] == 100.0
        assert normalized["summary"]["by_media_type"]["video"]["percentage"] == 50.0

    def test_normalize_combination_sorting(self):
        """Test that combinations are sorted by count (descending) and name."""
        data = {
            "summary": {
                "total_adapters": 10,
                "by_combination": {
                    "video": 1,
                    "banner": 3,
                    "banner, video": 3,
                    "banner, native": 2,
                    "banner, video, native": 1,
                },
            }
        }

        normalized = DataNormalizer.normalize_with_percentages(data)

        # Check order - should be sorted by count desc, then name
        combinations = list(normalized["summary"]["by_combination"].keys())
        assert combinations[0] in ["banner", "banner, video"]  # Both have count 3
        assert combinations[-1] in [
            "video",
            "banner, video, native",
        ]  # Both have count 1

    def test_get_formatted_percentage(self):
        """Test percentage formatting."""
        data = {"count": 5, "percentage": 25.5}
        assert DataNormalizer.get_formatted_percentage(data) == "5 (25.5%)"

    def test_get_media_types_display(self):
        """Test media types display formatting."""
        media_types = ["banner", "video", "native"]

        assert (
            DataNormalizer.get_media_types_display(media_types, "array")
            == "[banner, video, native]"
        )
        assert (
            DataNormalizer.get_media_types_display(media_types, "csv")
            == "banner, video, native"
        )
        assert (
            DataNormalizer.get_media_types_display(media_types, "plain")
            == "banner video native"
        )

        # Test empty
        assert DataNormalizer.get_media_types_display([], "array") == "[]"
        assert DataNormalizer.get_media_types_display([], "csv") == ""

    def test_normalize_empty_summary(self):
        """Test normalizing data without summary."""
        data = {"version": "v1.0.0", "adapters": {}}

        normalized = DataNormalizer.normalize_with_percentages(data)

        assert normalized["version"] == "v1.0.0"
        assert normalized["summary"]["total_adapters"] == 0
        assert normalized["summary"]["by_media_type"] == {}
        assert normalized["summary"]["by_combination"] == {}
