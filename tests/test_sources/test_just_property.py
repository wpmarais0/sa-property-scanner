"""Tests for the Just Property source adapter."""

from sa_property_scanner.sources.just_property import JustPropertySource

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <a data-id="12345" class="property-card-sm"
       href="/property/3-bedroom-house-for-sale-in-vredenburg/12345">
        <img src="https://cdn.just.property/img1.jpg" />
        <p class="card-price">R 1 850 000</p>
        <p class="card-description">3 Bedroom Freehold For Sale in Vredenburg</p>
        <div class="card-stats">3 Bed2 Bath2 Parking207.40 m²</div>
    </a>
    <a data-id="12346" class="property-card-sm"
       href="/property/2-bedroom-apartment-for-sale-in-cape-town/12346">
        <img src="/images/img2.jpg" />
        <p class="card-price">R 2 200 000</p>
        <p class="card-description">2 Bedroom Apartment For Sale in Cape Town</p>
        <div class="card-stats">2 Bed1 Bath1 Parking</div>
    </a>
    <a data-id="" class="property-card-sm"
       href="/property/no-id/">
        <p class="card-price">R 999 000</p>
        <p class="card-description">1 Bedroom House For Sale in Bellville</p>
    </a>
</body>
</html>
"""


def test_just_property_parse():
    """Just Property adapter should extract listings from PropertyWeb HTML cards."""
    source = JustPropertySource(search_url="https://www.just.property/results")
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "12345"
    assert first.title == "3 Bedroom Freehold For Sale in Vredenburg"
    assert first.price == 1_850_000
    assert first.price_text == "R 1 850 000"
    assert first.location == "Vredenburg"
    assert first.bedrooms == 3
    assert first.bathrooms == 2
    assert first.garages == 2
    assert first.size_sqm == 207
    assert first.property_type == "freehold"
    assert first.image_url == "https://cdn.just.property/img1.jpg"
    assert first.url == "https://www.just.property/property/3-bedroom-house-for-sale-in-vredenburg/12345"

    second = listings[1]
    assert second.external_id == "12346"
    assert second.price == 2_200_000
    assert second.location == "Cape Town"
    assert second.bedrooms == 2
    assert second.bathrooms == 1
    assert second.garages == 1
    assert second.property_type == "apartment"
    assert second.image_url == "https://www.just.property/images/img2.jpg"


def test_just_property_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = JustPropertySource(search_url="https://www.just.property/results")
    listings = source.parse("<html><body></body></html>")
    assert listings == []
