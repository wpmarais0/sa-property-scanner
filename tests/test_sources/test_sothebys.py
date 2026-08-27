"""Tests for the Sotheby's source adapter."""


from sa_property_scanner.sources.sothebys import SothebysSource

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="listing-results-cards">
        <a id="3423786" data-id="3423786" data-model="residential"
           class="property-card-sm"
           href="/results/residential/for-sale/st-helena-bay/sandy-point/house/3423786/96-beach-road/">
            <div class="card-header">
                <img src="https://cdn.example.com/img1.avif" />
            </div>
            <div class="card-price">R3,650,000</div>
            <div class="card-description">3 Bedroom House For Sale in Sandy Point</div>
            <div class="card-features">
                <span>3 Bed</span>
                <span>2 Bath</span>
                <span>2 Parking</span>
            </div>
        </a>
        <a id="2993410" data-id="2993410" data-model="residential"
           class="property-card-sm"
           href="/results/residential/for-sale/constantia/constantia/freehold/2993410/">
            <div class="card-header">
                <img src="https://cdn.example.com/img2.avif" />
            </div>
            <div class="card-price">R12,500,000</div>
            <div class="card-description">4 Bedroom Freehold For Sale in Constantia</div>
            <div class="card-features">
                <span>4 Bed</span>
                <span>4.5 Bath</span>
            </div>
        </a>
        <a id="3423787" data-id="3423787" data-model="residential"
           class="property-card-sm"
           href="/results/residential/for-sale/outeniqua-strand/outeniqua-strand/house/3423787/">
            <div class="card-header">
                <img src="https://cdn.example.com/img3.avif" />
            </div>
            <div class="card-price">R1,450,000</div>
            <div class="card-description">3 Bedroom House For Sale in Outeniqua Strand</div>
            <div class="card-features">
                <span>3 Bed</span>
                <span>2 Bath</span>
                <span>1 Parking</span>
                <span>250 m²</span>
                <span>Exclusive Mandate</span>
            </div>
        </a>
    </div>
</body>
</html>
"""


def test_sothebys_parse():
    """Sotheby's adapter should extract listings from real HTML structure."""
    source = SothebysSource(
        search_url="https://www.sothebysrealty.co.za/results/residential/for-sale"
    )
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 3

    first = listings[0]
    assert first.external_id == "3423786"
    assert first.title == "3 Bedroom House For Sale in Sandy Point"
    assert first.price == 3_650_000
    assert first.price_text == "R3,650,000"
    assert first.location == "Sandy Point"
    assert first.bedrooms == 3
    assert first.bathrooms == 2
    assert first.property_type == "house"
    assert first.image_url == "https://cdn.example.com/img1.avif"
    assert first.url == (
        "https://www.sothebysrealty.co.za/results/residential/for-sale/"
        "st-helena-bay/sandy-point/house/3423786/96-beach-road/"
    )

    second = listings[1]
    assert second.external_id == "2993410"
    assert second.title == "4 Bedroom Freehold For Sale in Constantia"
    assert second.price == 12_500_000
    assert second.location == "Constantia"
    assert second.bedrooms == 4
    assert second.bathrooms == 4
    assert second.property_type == "freehold"

    third = listings[2]
    assert third.external_id == "3423787"
    assert third.title == "3 Bedroom House For Sale in Outeniqua Strand"
    assert third.price == 1_450_000
    assert third.location == "Outeniqua Strand"
    assert third.bedrooms == 3
    assert third.bathrooms == 2
    assert third.size_sqm == 250


def test_sothebys_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = SothebysSource(
        search_url="https://www.sothebysrealty.co.za/results/residential/for-sale"
    )
    listings = source.parse("<html><body></body></html>")
    assert listings == []
