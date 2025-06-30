"""Tests for module rename detection functionality."""

from unittest.mock import Mock

import pytest

from src.module_compare.comparator import ModuleComparator
from src.module_compare.data_models import ModuleInfo


class TestRenameDetection:
    """Test module rename detection functionality."""

    @pytest.fixture
    def comparator(self):
        """Create a comparator instance."""
        mock_github = Mock()
        mock_config = Mock()
        return ModuleComparator(mock_github, mock_config)

    def test_git_history_renames(self, comparator):
        """Test detection of known renames from git history."""
        removed = [
            ModuleInfo(
                name="imds",
                path="modules/imdsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="gothamads",
                path="modules/gothamadsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="advertising",
                path="modules/advertisingBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="intenze",
                path="modules/intenzeBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed, added
        )

        assert len(renames) == 2
        assert len(remaining_removed) == 0
        assert len(remaining_added) == 0

        # Check specific renames
        rename_map = {r.old_module.name: r for r in renames}

        assert rename_map["imds"].new_module.name == "advertising"
        assert rename_map["imds"].detection_method == "git_history"
        assert rename_map["imds"].similarity_score == 1.0

        assert rename_map["gothamads"].new_module.name == "intenze"
        assert rename_map["gothamads"].detection_method == "git_history"
        assert rename_map["gothamads"].similarity_score == 1.0

    def test_case_change_detection(self, comparator):
        """Test detection of case changes (camelCase to snake_case)."""
        removed = [
            ModuleInfo(
                name="cadentApertureMX",
                path="modules/cadentApertureMXBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="epomDsp",
                path="modules/epomDspBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="cadent_aperture_mx",
                path="modules/cadent_aperture_mxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="epom_dsp",
                path="modules/epom_dspBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed, added)

        assert len(renames) == 2

        # All should be detected as case changes
        for rename in renames:
            assert rename.detection_method == "case_change"
            assert rename.similarity_score == 0.95

    def test_abbreviation_detection(self, comparator):
        """Test detection of abbreviations."""
        removed = [
            ModuleInfo(
                name="incrx",
                path="modules/incrxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="rtbx",
                path="modules/rtbxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="incrementx",
                path="modules/incrementxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="realtimebidexchange",
                path="modules/realtimebidexchangeBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed, added)

        assert len(renames) == 2

        rename_map = {r.old_module.name: r for r in renames}

        # incrx -> incrementx should be detected as abbreviation
        assert rename_map["incrx"].new_module.name == "incrementx"
        assert rename_map["incrx"].detection_method == "abbreviation"
        assert rename_map["incrx"].similarity_score == 0.9

        # rtbx -> realtimebidexchange should be detected as abbreviation
        assert rename_map["rtbx"].new_module.name == "realtimebidexchange"
        assert rename_map["rtbx"].detection_method == "abbreviation"
        assert rename_map["rtbx"].similarity_score == 0.9

    def test_substring_detection(self, comparator):
        """Test detection of substring matches."""
        removed = [
            ModuleInfo(
                name="amazon",
                path="modules/amazonBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="google",
                path="modules/googleBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="amazonuam",
                path="modules/amazonuamBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="googleads",
                path="modules/googleadsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed, added)

        assert len(renames) == 2

        for rename in renames:
            assert rename.detection_method == "substring"
            assert rename.similarity_score == 0.85

    def test_similarity_detection(self, comparator):
        """Test character similarity detection."""
        removed = [
            ModuleInfo(
                name="bidder1",
                path="modules/bidder1BidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="bidder2",
                path="modules/bidder2BidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, _, _ = comparator._detect_renames(removed, added)

        assert len(renames) == 1
        assert renames[0].detection_method == "similarity"
        assert (
            0.7 <= renames[0].similarity_score <= 0.9
        )  # Allow higher similarity for similar names

    def test_no_rename_detection(self, comparator):
        """Test when modules are too different to be considered renames."""
        removed = [
            ModuleInfo(
                name="appnexus",
                path="modules/appnexusBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="rubicon",
                path="modules/rubiconBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed, added
        )

        assert len(renames) == 0
        assert len(remaining_removed) == 1
        assert len(remaining_added) == 1
        assert remaining_removed[0].name == "appnexus"
        assert remaining_added[0].name == "rubicon"

    def test_category_mismatch_no_rename(self, comparator):
        """Test that modules in different categories are not considered renames."""
        removed = [
            ModuleInfo(
                name="appnexus",
                path="modules/appnexusBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="appnexus",
                path="modules/appnexusAnalyticsAdapter.js",
                category="Analytics Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed, added
        )

        assert len(renames) == 0
        assert len(remaining_removed) == 1
        assert len(remaining_added) == 1

    def test_multiple_potential_matches(self, comparator):
        """Test handling of multiple potential rename matches."""
        removed = [
            ModuleInfo(
                name="ad",
                path="modules/adBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="adtech",
                path="modules/adtechBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="adserver",
                path="modules/adserverBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="adform",
                path="modules/adformBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed, added
        )

        # Should pick the best match
        assert len(renames) == 1
        assert len(remaining_removed) == 0
        assert len(remaining_added) == 2

        # The rename should be to one of the added modules
        assert renames[0].old_module.name == "ad"
        assert renames[0].new_module.name in ["adtech", "adserver", "adform"]

    def test_mixed_detection_methods(self, comparator):
        """Test a mix of different rename detection methods."""
        removed = [
            ModuleInfo(
                name="imds",
                path="modules/imdsBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="cadentApertureMX",
                path="modules/cadentApertureMXBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="incrx",
                path="modules/incrxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="unmatched",
                path="modules/unmatchedBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        added = [
            ModuleInfo(
                name="advertising",
                path="modules/advertisingBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="cadent_aperture_mx",
                path="modules/cadent_aperture_mxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="incrementx",
                path="modules/incrementxBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
            ModuleInfo(
                name="newmodule",
                path="modules/newmoduleBidAdapter.js",
                category="Bid Adapters",
                repo="prebid-js",
            ),
        ]

        renames, remaining_removed, remaining_added = comparator._detect_renames(
            removed, added
        )

        assert len(renames) == 3
        assert len(remaining_removed) == 1
        assert len(remaining_added) == 1

        # Check detection methods
        rename_map = {r.old_module.name: r for r in renames}

        assert rename_map["imds"].detection_method == "git_history"
        assert rename_map["cadentApertureMX"].detection_method == "case_change"
        assert rename_map["incrx"].detection_method == "abbreviation"

        # Check unmatched
        assert remaining_removed[0].name == "unmatched"
        assert remaining_added[0].name == "newmodule"
