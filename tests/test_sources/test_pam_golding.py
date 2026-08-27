"""Tests for the Pam Golding source adapter."""


from sa_property_scanner.sources.pam_golding import PamGoldingSource

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <article class="results__item">
        <div class="results__item-image-container">
            <img src="/images/999.jpg" />
        </div>
        <div class="results__item-body-container">
            <h3 class="results__item-heading">
                <a href="/property-details/3-bed-knysna/bed1750466"
                   class="results__item-heading-link"
                   title="3 Bedroom House in Knysna - BED1750466">
                   3 Bedroom House in Knysna
                </a>
            </h3>
            <div class="results__item-price-contact">
                <div class="results__item-price">
                    <div class="price-display">R 3 200 000</div>
                </div>
            </div>
            <div class="results__item-body">
                <ul class="results__item-body-list">
                    <li class="results__item-body-item">3 beds </li>
                    <li class="results__item-body-item">2 baths </li>
                    <li class="results__item-body-item">2 parking </li>
                </ul>
            </div>
        </div>
    </article>
    <article class="results__item">
        <div class="results__item-image-container">
            <img src="/images/888.jpg" />
        </div>
        <div class="results__item-body-container">
            <h3 class="results__item-heading">
                <a href="/property-details/apartment-plett/bed1750467"
                   class="results__item-heading-link">
                   Modern Apartment in Plettenberg Bay
                </a>
            </h3>
            <div class="results__item-price-contact">
                <div class="results__item-price">
                    <div class="price-display">R 1 850 000</div>
                </div>
            </div>
            <div class="results__item-body">
                <ul class="results__item-body-list">
                    <li class="results__item-body-item">2 beds </li>
                    <li class="results__item-body-item">1 bath </li>
                </ul>
            </div>
        </div>
    </article>
</body>
</html>
"""


def test_pam_golding_parse():
    """Pam Golding adapter should extract listings from real HTML structure."""
    source = PamGoldingSource(search_url="https://pamgolding.co.za/search")
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "bed1750466"
    assert first.title == "3 Bedroom House in Knysna"
    assert first.price == 3_200_000
    assert first.price_text == "R 3 200 000"
    assert first.location == "Knysna"
    assert first.bedrooms == 3
    assert first.bathrooms == 2
    assert first.image_url == "https://pamgolding.co.za/images/999.jpg"
    assert first.url == "https://pamgolding.co.za/property-details/3-bed-knysna/bed1750466"

    second = listings[1]
    assert second.external_id == "bed1750467"
    assert second.price == 1_850_000
    assert second.location == "Plettenberg Bay"


def test_pam_golding_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = PamGoldingSource(search_url="https://pamgolding.co.za/search")
    listings = source.parse("<html><body></body></html>")
    assert listings == []
