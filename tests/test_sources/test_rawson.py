"""Tests for the Rawson source adapter."""

from sa_property_scanner.sources.rawson import RawsonSource

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="card">
        <a class="card__link" href="/property/12345">View</a>
        <h3 class="card__title">3 Bedroom house for sale in Secunda</h3>
        <div class="card__price">R 1 250 000</div>
        <ol class="features__list">
            <li class="features__item">3</li>
            <li class="features__item">2</li>
            <li class="features__item">1</li>
        </ol>
    </div>
    <div class="card">
        <a class="card__link" href="/property/67890">View</a>
        <h3 class="card__title">2 Bedroom apartment for sale in Cape Town</h3>
        <div class="card__price">R 2 800 000</div>
        <ol class="features__list">
            <li class="features__item">2</li>
            <li class="features__item">1</li>
        </ol>
    </div>
    <div class="card">
        <div class="card__price">R 999 000</div>
        <h3 class="card__title">No link card</h3>
    </div>
    <div class="other">Not a card</div>
</body>
</html>
"""


def test_rawson_parse():
    """Rawson adapter should extract listings from HTML card structure."""
    source = RawsonSource(search_url="https://rawson.co.za/property/for-sale")
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "12345"
    assert first.title == "3 Bedroom house for sale in Secunda"
    assert first.price == 1_250_000
    assert first.price_text == "R 1 250 000"
    assert first.location == "Secunda"
    assert first.bedrooms == 3
    assert first.bathrooms == 2
    assert first.garages == 1
    assert first.property_type == "house"
    assert first.url == "https://rawson.co.za/property/12345"

    second = listings[1]
    assert second.external_id == "67890"
    assert second.title == "2 Bedroom apartment for sale in Cape Town"
    assert second.price == 2_800_000
    assert second.location == "Cape Town"
    assert second.bedrooms == 2
    assert second.bathrooms == 1
    assert second.garages is None
    assert second.property_type == "apartment"


def test_rawson_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = RawsonSource(search_url="https://rawson.co.za/property/for-sale")
    listings = source.parse("<html><body></body></html>")
    assert listings == []


def test_rawson_fallback_id():
    """Rawson should use URL path as fallback ID when no trailing numeric ID."""
    html = """
    <html><body>
        <div class="card">
            <a class="card__link" href="/some/path/to/property">View</a>
            <h3 class="card__title">5 Bedroom house for sale in Knysna</h3>
            <div class="card__price">R 3 500 000</div>
            <ol class="features__list">
                <li class="features__item">5</li>
                <li class="features__item">3</li>
            </ol>
        </div>
    </body></html>
    """
    source = RawsonSource(search_url="https://rawson.co.za/property/for-sale")
    listings = source.parse(html)
    assert len(listings) == 1
    assert listings[0].external_id == "some-path-to-property"
    assert listings[0].url == "https://rawson.co.za/some/path/to/property"
