"""Tests for the Seeff source adapter."""

import pytest

from sa_property_scanner.sources.seeff import SeeffSource


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="listing-results-cards">
        <div id="1918694" data-id="1918694" data-model="residential"
             class="seeff-listing-card">
            <div class="card-header">
                <a href="/results/residential/for-sale/tulbagh/tulbagh/farm/1918694/">
                    <div class="card-img">
                        <img src="https://cdn.example.com/img1.jpg" />
                    </div>
                </a>
            </div>
            <div class="card-price">R 3 200 000</div>
            <div class="card-heading">3 Bedroom House For Sale in Knysna</div>
            <div class="card-features">
                <span>3 Beds</span>
                <span>2 Baths</span>
                <span>2 Parkings</span>
            </div>
        </div>
        <div id="2993410" data-id="2993410" data-model="residential"
             class="seeff-listing-card">
            <div class="card-header">
                <a href="/results/residential/for-sale/danielskuil/danielskuil/lodge/2993410/">
                    <div class="card-img">
                        <img src="https://cdn.example.com/img2.jpg" />
                    </div>
                </a>
            </div>
            <div class="card-price">POA</div>
            <div class="card-heading">14 Bedroom Lodge For Sale in Danielskuil</div>
            <div class="card-features">
                <span>14 Beds</span>
                <span>14 Baths</span>
                <span>16 Parkings</span>
            </div>
        </div>
    </div>
</body>
</html>
"""


def test_seeff_parse():
    """Seeff adapter should extract listings from real HTML structure."""
    source = SeeffSource(search_url="https://www.seeff.com/results/residential/for-sale/?s=-price")
    listings = source.parse(SAMPLE_HTML)

    assert len(listings) == 2

    first = listings[0]
    assert first.external_id == "1918694"
    assert first.title == "3 Bedroom House For Sale in Knysna"
    assert first.price == 3_200_000
    assert first.price_text == "R 3 200 000"
    assert first.location == "Knysna"
    assert first.bedrooms == 3
    assert first.bathrooms == 2
    assert first.image_url == "https://cdn.example.com/img1.jpg"
    assert first.url == (
        "https://www.seeff.com/results/residential/for-sale/"
        "tulbagh/tulbagh/farm/1918694/"
    )

    second = listings[1]
    assert second.external_id == "2993410"
    assert second.title == "14 Bedroom Lodge For Sale in Danielskuil"
    assert second.price is None  # POA cannot be parsed
    assert second.price_text == "POA"
    assert second.location == "Danielskuil"
    assert second.bedrooms == 14
    assert second.bathrooms == 14


def test_seeff_empty_html():
    """Empty HTML should return an empty list without crashing."""
    source = SeeffSource(search_url="https://www.seeff.com/results/residential/for-sale/?s=-price")
    listings = source.parse("<html><body></body></html>")
    assert listings == []
