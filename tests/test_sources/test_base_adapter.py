"""Tests for the shared SourceAdapter helpers."""

import pytest

from sa_property_scanner.sources.base import SourceAdapter


class DummyAdapter(SourceAdapter):
    """Minimal concrete adapter for testing base helpers."""

    name = "dummy"

    def fetch(self, url: str):
        return ""

    def parse(self, data):
        return []


@pytest.fixture
def adapter():
    return DummyAdapter(search_url="https://example.com")


class TestExtractPrice:
    """Price parsing should handle the formats used by South African portals."""

    def test_extract_price_with_spaces(self, adapter):
        assert adapter._extract_price("R 1 300 000") == 1_300_000

    def test_extract_price_with_commas(self, adapter):
        assert adapter._extract_price("R1,300,000") == 1_300_000

    def test_extract_price_million_shorthand(self, adapter):
        assert adapter._extract_price("R 1.3 million") == 1_300_000

    def test_extract_price_million_abbreviation(self, adapter):
        assert adapter._extract_price("R 13m") == 13_000_000

    def test_extract_price_million_with_comma_decimal(self, adapter):
        assert adapter._extract_price("R 2,5 million") == 2_500_000

    def test_extract_price_high_value(self, adapter):
        assert adapter._extract_price("R 13 000 000") == 13_000_000

    def test_extract_price_poa_returns_none(self, adapter):
        assert adapter._extract_price("POA") is None

    def test_extract_price_empty_returns_none(self, adapter):
        assert adapter._extract_price("") is None

    def test_extract_price_none_returns_none(self, adapter):
        assert adapter._extract_price(None) is None

    def test_extract_price_full_price_preferred_over_million_text(self, adapter):
        # An explicit full price should not be overridden by a "million" mention
        # elsewhere in the text (e.g. "was 1.3 million").
        assert adapter._extract_price("R 2 000 000 (was 1.3 million)") == 2_000_000

    def test_extract_price_thousand_shorthand(self, adapter):
        assert adapter._extract_price("R 850k") == 850_000
