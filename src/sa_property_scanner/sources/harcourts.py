"""Harcourts source adapter.

Harcourts uses the PropertyWeb platform (same as Just Property).
Listings are rendered server-side in `.property-card-sm` anchor tags.
"""

import re

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class HarcourtsSource(SourceAdapter):
    """Adapter for harcourts.co.za (PropertyWeb platform)."""

    name = "harcourts"

    def fetch(self, url: str) -> str:
        """Fetch HTML via polite HTTP GET."""
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:  # type: ignore[override]
        """Parse listings from server-rendered HTML cards."""
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("a", class_="property-card-sm")
        listings: list[RawListing] = []

        for card in cards:
            try:
                listing_id = str(card.get("data-id", "")).strip()
                if not listing_id:
                    continue

                href = str(card.get("href", "")).strip()
                url_abs = self._make_absolute_url("https://www.harcourts.co.za", href)

                price_tag = card.select_one("p.card-price")
                price_text = price_tag.get_text(strip=True) if price_tag else None
                price = self._extract_price(price_text)

                desc_tag = card.select_one("p.card-description")
                title = desc_tag.get_text(strip=True) if desc_tag else None

                # Parse stats: "3 Bed2 Bath2 Parking207.40 m²"
                bedrooms = bathrooms = garages = size_sqm = None
                stats_tag = card.select_one("div.card-stats")
                if stats_tag:
                    stats_text = stats_tag.get_text(strip=True)
                    bed_match = re.search(r"(\d+(?:\.\d+)?)\s*Bed", stats_text)
                    if bed_match:
                        bedrooms = int(float(bed_match.group(1)))
                    bath_match = re.search(r"(\d+(?:\.\d+)?)\s*Bath", stats_text)
                    if bath_match:
                        bathrooms = int(float(bath_match.group(1)))
                    park_match = re.search(r"(\d+)\s*Parking", stats_text)
                    if park_match:
                        garages = int(park_match.group(1))
                    m2_match = re.search(r"(\d+(?:\.\d+)?)\s*m²", stats_text)
                    if m2_match:
                        size_sqm = int(float(m2_match.group(1)))

                # Extract property type from title
                property_type = None
                if title:
                    type_match = re.search(r"\d+\s+Bedroom\s+(\w+)\s+For\s+Sale", title, re.IGNORECASE)
                    if type_match:
                        property_type = type_match.group(1).lower()

                # Extract location from title
                location = None
                if title and " in " in title:
                    location = title.split(" in ")[-1].strip()

                img_tag = card.find("img")
                image_url = None
                if img_tag:
                    src = img_tag.get("src")
                    if src:
                        image_url = str(src).strip() or None

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
                        size_sqm=size_sqm,
                        image_url=image_url,
                    )
                )
            except Exception as exc:
                self.logger.warning("Failed to parse Harcourts card: %s", exc)

        self.logger.info("Harcourts parsed %d listings", len(listings))
        return listings
