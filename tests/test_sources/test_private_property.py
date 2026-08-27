"""Tests for the Private Property source adapter."""

import pytest

from sa_property_scanner.sources.private_property import PrivatePropertySource


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="listing-results">
        <a href="/for-sale/western-cape/boland/paarl/paarl-south/T4662739">
            <div class="listing-card">
                <span class="listing-price">R 11 114 850</span>
                <span class="listing-title">4 Bedroom House in Paarl South</span>
            </div>
        </a>
    </div>
    <script type="application/ld+json">
    {
        "@context": "http://schema.org",
        "@type": "Residence",
        "photo": [{"@type": "ImageObject", "contentUrl": "https://images.pp.co.za/listing/10443187/img1.jpg"}],
        "address": {"@type": "PostalAddress", "addressLocality": "Paarl South, Paarl", "addressRegion": "Western Cape"},
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Bedrooms", "value": "4"},
            {"@type": "PropertyValue", "name": "Bathrooms", "value": "3.5"},
            {"@type": "PropertyValue", "name": "Garages", "value": "2"}
        ],
        "url": "https://www.privateproperty.co.za/for-sale/western-cape/boland/paarl/paarl-south/T4662739"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "http://schema.org",
        "@type": "Residence",
        "photo": [{"@type": "ImageObject", "contentUrl": "https://images.pp.co.za/listing/10372849/img2.jpg"}],
        "address": {"@type": "PostalAddress", "addressLocality": "Paarl South, Paarl", "addressRegion": "Western Cape"},
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Bedrooms", "value": "3"},
            {"@type": "PropertyValue", "name": "Bathrooms", "value": "2"},
            {"@type": "PropertyValue", "name": "Garages", "value": "2"}
        ],
        "url": "https://www.privateproperty.co.za/for-sale/western-cape/boland/paarl/paarl-south/T4621138"
    }
    </script>
    <a href="/for-sale/western-cape/boland/paarl/paarl-south/T4621138">
        <div class="listing-card">
            <span class="listing-price">R 7 140 000</span>
            <span class="listing-title">3 Bedroom House in Paarl South</span>
        </div>
    </a>
</body>
</html>
"""


def test_private_property_parse():
    """Private Property adapter should extract listings from JSON-LD + HTML fallback."""
    source = PrivatePropertySource(
        search_url="https://www.privateproperty.co.za/houses-for-sale/western-cape/4"
    )
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "T4662739"
    assert first.title == "4 Bedroom House in Paarl South"
    assert first.price == 11_114_850
    assert first.price_text == "R 11 114 850"
    assert first.location == "Paarl South, Paarl"
    assert first.bedrooms == 4
    assert first.bathrooms == 3
    assert first.garages == 2
    assert first.property_type == "house"
    assert first.image_url == "https://images.pp.co.za/listing/10443187/img1.jpg"
    assert first.url == "https://www.privateproperty.co.za/for-sale/western-cape/boland/paarl/paarl-south/T4662739"

    second = listings[1]
    assert second.external_id == "T4621138"
    assert second.title == "3 Bedroom House in Paarl South"
    assert second.price == 7_140_000
    assert second.bedrooms == 3
    assert second.bathrooms == 2
    assert second.garages == 2


def test_private_property_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = PrivatePropertySource(
        search_url="https://www.privateproperty.co.za/houses-for-sale/western-cape/4"
    )
    listings = source.parse("<html><body></body></html>")
    assert listings == []


def test_private_property_no_price_fallback():
    """If HTML card is missing, listing should still parse with JSON-LD data only."""
    html = """
    <html><body>
    <script type="application/ld+json">
    {
        "@type": "Residence",
        "address": {"addressLocality": "Somerset West"},
        "additionalProperty": [{"name": "Bedrooms", "value": "2"}],
        "url": "https://www.privateproperty.co.za/for-sale/western-cape/T9999999"
    }
    </script>
    </body></html>
    """
    source = PrivatePropertySource(
        search_url="https://www.privateproperty.co.za/houses-for-sale/western-cape/4"
    )
    listings = source.parse(html)
    assert len(listings) == 1
    assert listings[0].external_id == "T9999999"
    assert listings[0].location == "Somerset West"
    assert listings[0].bedrooms == 2
    assert listings[0].price is None
    assert listings[0].title is None
