"""Tests for the scraper filtering logic."""

from unittest.mock import patch

import pytest

from sa_property_scanner.schemas import RawListing
from sa_property_scanner.scraper import ScraperOrchestrator


@pytest.fixture
def orchestrator():
    return ScraperOrchestrator()


class TestPriceFilter:
    def test_price_within_range(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_500_000)
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.min_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_price_above_max(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=2_000_000)
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.min_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_price_below_min(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=500_000)
        with (
            patch("sa_property_scanner.scraper.settings.min_price", 1_000_000),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is False

    def test_missing_price_skips_filter(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=None, price_text="POA")
        with patch("sa_property_scanner.scraper.settings.max_price", 1_800_000):
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

    def test_missing_garages_skips_filter(self, orchestrator):
        raw = RawListing(external_id="x", url="y", price=1_000_000, garages=None)
        with (
            patch("sa_property_scanner.scraper.settings.garage_min", 1),
            patch("sa_property_scanner.scraper.settings.max_price", None),
        ):
            assert orchestrator._passes_filter(raw) is True


class TestCombinedFilter:
    def test_all_criteria_met(self, orchestrator):
        raw = RawListing(
            external_id="x", url="y", price=1_500_000,
            bedrooms=3, bathrooms=2, property_type="house"
        )
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.property_types", ["house"]),
        ):
            assert orchestrator._passes_filter(raw) is True

    def test_one_criteria_fails(self, orchestrator):
        raw = RawListing(
            external_id="x", url="y", price=2_000_000,
            bedrooms=3, bathrooms=2, property_type="house"
        )
        with (
            patch("sa_property_scanner.scraper.settings.max_price", 1_800_000),
            patch("sa_property_scanner.scraper.settings.bedrooms_min", 3),
            patch("sa_property_scanner.scraper.settings.bathrooms_min", 2),
            patch("sa_property_scanner.scraper.settings.property_types", ["house"]),
        ):
            assert orchestrator._passes_filter(raw) is False
