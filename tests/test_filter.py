"""Tests for the scraper filtering logic."""

import contextlib
from unittest.mock import patch

import pytest

from sa_property_scanner.schemas import RawListing
from sa_property_scanner.scraper import ScraperOrchestrator


@pytest.fixture
def orchestrator():
    return ScraperOrchestrator()


@pytest.fixture(autouse=True)
def disable_location_filter():
    """Disable the Western Cape location filter for filter unit tests."""
    with patch("sa_property_scanner.scraper.settings.western_cape_only", False):
        yield


class TestPriceFilter:
    @contextlib.contextmanager
    def _price_patches(self, min_price=None, max_price=None):
        """Patch global price settings and clear property-type overrides."""
        with (
            patch("sa_property_scanner.scraper.settings.min_price", min_price),
            patch("sa_property_scanner.scraper.settings.max_price", max_price),
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", None),
        ):
            yield

    def test_price_within_range(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_500_000)
        with self._price_patches(min_price=None, max_price=1_800_000):
            assert orchestrator._passes_filter(raw) is True

    def test_price_above_max(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=2_000_000)
        with self._price_patches(min_price=None, max_price=1_800_000):
            assert orchestrator._passes_filter(raw) is False

    def test_price_below_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=500_000)
        with self._price_patches(min_price=1_000_000, max_price=None):
            assert orchestrator._passes_filter(raw) is False

    def test_missing_price_is_rejected(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=None, price_text="POA")
        with self._price_patches(max_price=1_800_000):
            assert orchestrator._passes_filter(raw) is False

    def test_missing_price_allowed_when_no_price_config(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=None, price_text="POA")
        with self._price_patches(min_price=None, max_price=None):
            assert orchestrator._passes_filter(raw) is True

    def test_house_price_uses_house_range(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_500_000, property_type="house")
        with (
            patch("sa_property_scanner.scraper.settings.house_min_price", 850_000),
            patch("sa_property_scanner.scraper.settings.house_max_price", 2_000_000),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", None),
            patch("sa_property_scanner.scraper.settings.min_price", None),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_house_price_above_house_max(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=2_500_000, property_type="house")
        with (
            patch("sa_property_scanner.scraper.settings.house_min_price", 850_000),
            patch("sa_property_scanner.scraper.settings.house_max_price", 2_000_000),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", None),
            patch("sa_property_scanner.scraper.settings.min_price", None),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_vacant_land_price_uses_land_range(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=500_000, property_type="vacant land")
        with (
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", 250_000),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", 850_000),
            patch("sa_property_scanner.scraper.settings.min_price", None),
            patch("sa_property_scanner.scraper.settings.max_price", None),
            patch("sa_property_scanner.scraper.settings.property_types", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_vacant_land_price_above_land_max(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, property_type="stand")
        with (
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", 250_000),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", 850_000),
            patch("sa_property_scanner.scraper.settings.min_price", None),
            patch("sa_property_scanner.scraper.settings.max_price", None),
            patch("sa_property_scanner.scraper.settings.property_types", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_vacant_land_fallback_heuristic(self, orchestrator):
        raw = RawListing(
            external_id="x",
            url="y",
            price=400_000,
            title="Vacant stand for sale in Velddrif",
        )
        with (
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.vacant_land_min_price", 250_000),
            patch("sa_property_scanner.scraper.settings.vacant_land_max_price", 850_000),
            patch("sa_property_scanner.scraper.settings.min_price", None),
            patch("sa_property_scanner.scraper.settings.max_price", None),
            patch("sa_property_scanner.scraper.settings.property_types", None),
        ):
            assert orchestrator._passes_filter(raw) is True


class TestBedroomFilter:
    def test_bedrooms_meets_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, bedrooms=3)
        with (
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_bedrooms_below_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, bedrooms=2)
        with (
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False


class TestBathroomFilter:
    def test_bathrooms_meets_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, bathrooms=2)
        with (
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_bathrooms_below_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, bathrooms=1)
        with (
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False


class TestPropertyTypeFilter:
    def test_type_matches(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, property_type="house")
        with (
            patch("sa_property_scanner.scraper.settings.property_types", ["house", "apartment"]),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_type_no_match(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, property_type="farm")
        with (
            patch("sa_property_scanner.scraper.settings.property_types", ["house", "apartment"]),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False


class TestGarageFilter:
    def test_garages_meets_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, garages=2)
        with (
            patch("sa_property_scanner.scraper.settings.garage_min", 1),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_garages_below_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, garages=0)
        with (
            patch("sa_property_scanner.scraper.settings.garage_min", 1),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

class TestExcludedLocationsFilter:
    def test_excluded_location_rejected(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, location="Mitchells Plain")
        with (
            patch("sa_property_scanner.scraper.settings.excluded_locations", ["mitchells plain"]),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_non_excluded_location_allowed(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, location="Langebaan")
        with (
            patch("sa_property_scanner.scraper.settings.excluded_locations", ["mitchells plain"]),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_excluded_substring_match(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, location="House in Bonteheuwel, Cape Town")
        with (
            patch("sa_property_scanner.scraper.settings.excluded_locations", ["bonteheuwel"]),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_missing_garages_skips_filter(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, garages=None)
        with (
            patch("sa_property_scanner.scraper.settings.garage_min", 1),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True


class TestCombinedFilter:
    def test_all_criteria_met(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_500_000, bedrooms=3, bathrooms=2, property_type="house")
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.property_types", ["house"]),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_one_criteria_fails(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=2_000_000, bedrooms=3, bathrooms=2, property_type="house")
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.house_min_price", None),
            patch("sa_property_scanner.scraper.settings.house_max_price", None),
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.property_types", ["house"]),
        ):
            assert orchestrator._passes_filter(raw) is False
