"""Rawson source adapter.

Rawson listings are rendered server-side in `.card` divs.
"""

import re
from contextlib import suppress

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class RawsonSource(SourceAdapter):
    """Adapter for rawson.co.za."""

    name = "rawson"

    def fetch(self, url: str) -> str:
        """Fetch HTML via polite HTTP GET.

        Rawson blocks requests that include an ``Accept-Encoding`` header,
        so we strip it from the default set.
        """
        return self._http_get(url, headers={"Accept-Encoding": ""})

    def parse(self, html: str) -> list[RawListing]:  # type: ignore[override]
        """Parse listings from server-rendered HTML cards."""
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="card")
        listings: list[RawListing] = []

        for card in cards:
            try:
                link_tag = card.select_one("a.card__link")
                if not link_tag:
                    continue

                href = str(link_tag.get("href", "")).strip()
                if not href:
                    continue

                url_abs = self._make_absolute_url("https://rawson.co.za", href)

                # Extract listing ID from URL if possible
                listing_id = None
                id_match = re.search(r"/(\d+)$", href)
                if id_match:
                    listing_id = id_match.group(1)
                else:
                    # Use URL path as fallback ID
                    listing_id = href.replace("https://rawson.co.za", "").strip("/").replace("/", "-")

                price_tag = card.select_one("div.card__price")
                price_text = price_tag.get_text(strip=True) if price_tag else None
                price = self._extract_price(price_text)

                title_tag = card.select_one("h3.card__title")
                title = title_tag.get_text(strip=True) if title_tag else None

                # Parse features: ol.features__list with li.features__item
                # Order: bedrooms, bathrooms, garages
                bedrooms = bathrooms = garages = None
                features_list = card.select_one("ol.features__list")
                if features_list:
                    items = features_list.select("li.features__item")
                    if len(items) >= 1:
                        beds_text = items[0].get_text(strip=True)
                        with suppress(ValueError):
                            bedrooms = int(beds_text)
                    if len(items) >= 2:
                        baths_text = items[1].get_text(strip=True)
                        with suppress(ValueError):
                            bathrooms = int(baths_text)
                    if len(items) >= 3:
                        garages_text = items[2].get_text(strip=True)
                        with suppress(ValueError):
                            garages = int(garages_text)

                # Extract property type from title, e.g. "3 Bedroom house for sale in Secunda"
                property_type = None
                if title:
                    type_match = re.search(r"\d+\s+Bedroom\s+(\w+)\s+for\s+sale", title, re.IGNORECASE)
                    if type_match:
                        property_type = type_match.group(1).lower()

                # Extract location from title
                location = None
                if title and " in " in title:
                    location = title.split(" in ")[-1].strip()

                listings.append(
                    RawListing(
                        external_id=listing_id,
                        url=url_abs or href,
                        title=title,
                        price=price,
                        price_text=price_text,
                        location=location,
                        bedrooms=bedrooms,
                        bathrooms=bathrooms,
                        garages=garages,
                        property_type=property_type,
                    )
                )
            except Exception as exc:
                self.logger.warning("Failed to parse Rawson card: %s", exc)

        self.logger.info("Rawson parsed %d listings", len(listings))
        return listings
