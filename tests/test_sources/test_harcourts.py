"""Tests for the Harcourts source adapter."""

from sa_property_scanner.sources.harcourts import HarcourtsSource

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <a data-id="54321" class="property-card-sm"
       href="/property/4-bedroom-house-for-sale-in-stellenbosch/54321">
        <img src="https://cdn.harcourts.co.za/img1.jpg" />
        <p class="card-price">R 4 500 000</p>
        <p class="card-description">4 Bedroom House For Sale in Stellenbosch</p>
        <div class="card-stats">4 Bed3 Bath2 Parking350 m²</div>
    </a>
    <a data-id="54322" class="property-card-sm"
       href="/property/2-bedroom-freehold-for-sale-in-paarl/54322">
        <img src="/media/img2.jpg" />
        <p class="card-price">R 1 200 000</p>
        <p class="card-description">2 Bedroom Freehold For Sale in Paarl</p>
        <div class="card-stats">2 Bed1 Bath</div>
    </a>
</body>
</html>
"""


def test_harcourts_parse():
    """Harcourts adapter should extract listings from PropertyWeb HTML cards."""
    source = HarcourtsSource(search_url="https://www.harcourts.co.za/results")
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "54321"
    assert first.title == "4 Bedroom House For Sale in Stellenbosch"
    assert first.price == 4_500_000
    assert first.price_text == "R 4 500 000"
    assert first.location == "Stellenbosch"
    assert first.bedrooms == 4
    assert first.bathrooms == 3
    assert first.garages == 2
    assert first.size_sqm == 350
    assert first.property_type == "house"
    assert first.image_url == "https://cdn.harcourts.co.za/img1.jpg"
    assert first.url == "https://www.harcourts.co.za/property/4-bedroom-house-for-sale-in-stellenbosch/54321"

    second = listings[1]
    assert second.external_id == "54322"
    assert second.price == 1_200_000
    assert second.location == "Paarl"
    assert second.bedrooms == 2
    assert second.bathrooms == 1
    assert second.garages is None
    assert second.size_sqm is None
    assert second.property_type == "freehold"
    assert second.image_url == "https://www.harcourts.co.za/media/img2.jpg"


def test_harcourts_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = HarcourtsSource(search_url="https://www.harcourts.co.za/results")
    listings = source.parse("<html><body></body></html>")
    assert listings == []
