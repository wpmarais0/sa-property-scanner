"""Private Property source adapter.

Private Property embeds schema.org JSON-LD (`<script type="application/ld+json">`)
in every search result page. Each listing is a `@type: "Residence"` object with
structured address, photo, and property attributes. We parse the JSON-LD directly
and fall back to HTML selectors for fields missing from the structured data
(notably price and title).
"""

import json
from typing import Any

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class PrivatePropertySource(SourceAdapter):
    """Adapter for privateproperty.co.za (static HTML + JSON-LD parsing)."""

    name = "private_property"
    mode = "static"

    def fetch(self, url: str) -> str:
        """Fetch search result page HTML."""
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:
        """Parse listings from JSON-LD scripts and HTML fallback."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[RawListing] = []

        # Each listing has a JSON-LD Residence script tag
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            if not script or not script.string:
                continue
            try:
                data = json.loads(script.string)
                if data.get("@type") != "Residence":
                    continue
                listing = self._parse_residence(data, soup)
                if listing:
                    listings.append(listing)
            except (json.JSONDecodeError, ValueError):
                continue

        self.logger.info("Private Property parsed %d listings", len(listings))
        return listings

    def _parse_residence(self, data: dict[str, Any], soup: BeautifulSoup) -> RawListing | None:
        """Convert a single JSON-LD Residence into a RawListing."""
        url = data.get("url", "")
        if not url:
            return None

        # External ID from URL path: /for-sale/.../T1234567
        external_id = url.rstrip("/").split("/")[-1]
        if not external_id or not external_id.startswith("T"):
            # Fallback: try to extract any trailing token
            parts = url.rstrip("/").split("/")
            external_id = parts[-1] if parts else ""
        if not external_id:
            return None

        # Address
        address = data.get("address", {})
        location = address.get("addressLocality") or address.get("addressRegion")

        # Photos
        photos = data.get("photo", [])
        image_url = None
        if photos and isinstance(photos, list):
            image_url = photos[0].get("contentUrl") if isinstance(photos[0], dict) else None

        # Features from additionalProperty
        bedrooms = bathrooms = garage = size_sqm = None
        for prop in data.get("additionalProperty", []):
            if not isinstance(prop, dict):
                continue
            name = prop.get("name", "").lower()
            value = prop.get("value")
            try:
                if name == "bedrooms":
                    bedrooms = int(float(value)) if value else None
                elif name == "bathrooms":
                    bathrooms = int(float(value)) if value else None
                elif name == "garages":
                    garage = int(float(value)) if value else None
            except (ValueError, TypeError):
                continue

        # Price and title are NOT in JSON-LD; find matching HTML card
        price_text, title = self._find_price_and_title(soup, external_id)
        price = self._extract_price(price_text)

        return RawListing(
            external_id=external_id,
            url=url,
            title=title,
            price=price,
            price_text=price_text,
            location=location,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type="house",  # URL path uses /houses-for-sale/
            size_sqm=size_sqm,
            image_url=image_url,
        )

    def _find_price_and_title(self, soup: BeautifulSoup, external_id: str) -> tuple[str | None, str | None]:
        """Find the price and title from the HTML card matching the listing ID."""
        # Private Property cards contain the listing ID in the URL
        # Look for any anchor whose href contains the external_id
        link = soup.find("a", href=lambda h: h and external_id in h)
        if not link:
            return None, None

        # Walk up to find the card container
        card = link.find_parent("div", class_=lambda c: c and "listing" in c.lower())
        if not card:
            card = link.find_parent("div")

        if not card:
            return None, None

        # Price: typically in a span/div with "price" in class name
        price_el = card.find(class_=lambda c: c and "price" in c.lower())
        price_text = price_el.get_text(strip=True) if price_el else None

        # Title: usually near the price, e.g. "3 Bedroom House in Paarl South"
        title_el = card.find(["h2", "h3", "span", "div"], class_=lambda c: c and "title" in c.lower())
        if not title_el:
            # Fallback: any text node that looks like a property title
            for tag in card.find_all(["span", "div"]):
                text = tag.get_text(strip=True)
                if "bedroom" in text.lower() and "in" in text.lower():
                    title_el = tag
                    break
        title = title_el.get_text(strip=True) if title_el else None

        return price_text, title
