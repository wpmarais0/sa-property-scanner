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

    def parse(self, html: str) -> list[RawListing]:  # type: ignore[override]
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

        if price is None and price_text is None:
            price_text = "Price on request"

        return RawListing(
            external_id=external_id,
            url=url,
            title=title,
            price=price,
            price_text=price_text,
            location=location,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            garages=garage,
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

        # For featured listings the anchor itself is the card; for standard
        # listings the details live inside the anchor or its immediate card
        # container. Search the link first so we stay inside the correct card.
        card = link.find_parent("div", class_=lambda c: c and "listing" in c.lower())
        search_roots = [link, card] if card else [link]

        # Find the first price element whose text actually parses to a number.
        # Banners such as ``listing-banner--price-reduced`` contain the word
        # "price" in their class but only hold the text "Reduced", so we skip
        # them by requiring a successful numeric extraction.
        price_text: str | None = None
        for root in search_roots:
            if root is None:
                continue
            candidates = root.find_all(class_=lambda c: c and "price" in c.lower())
            for candidate in candidates:
                text = str(candidate.get_text(strip=True))
                if self._extract_price(text) is not None:
                    price_text = text
                    break
            if price_text:
                break
            # If nothing parses, fall back to the first candidate so the raw
            # label (e.g. "POA") is still captured.
            if not price_text and candidates:
                price_text = str(candidates[0].get_text(strip=True))

        # Title: look for a heading/title element.
        title: str | None = None
        for root in search_roots:
            if root is None:
                continue
            title_el = root.find(["h2", "h3", "span", "div"], class_=lambda c: c and "title" in c.lower())
            if title_el:
                # Use a space separator so titles with nested formatting such as
                # "House in <strong>Paarl</strong>" render as "House in Paarl".
                title = str(title_el.get_text(separator=" ", strip=True))
                break
            # Fallback: any text node that looks like a property title
            for tag in root.find_all(["span", "div"]):
                text = str(tag.get_text(separator=" ", strip=True))
                if "bedroom" in text.lower() and " in " in text.lower():
                    title = text
                    break
            if title:
                break

        return price_text, title

    def verify_price(self, url: str, html: str | None = None) -> int | None:
        """Fetch the detail page and extract the displayed price.

        Private Property search-result prices usually match the detail page, but
        verifying before notification catches any listings whose price changed
        between index caching and the scrape.
        """
        try:
            if html is None:
                html = self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("Failed to fetch detail page for price verification %s: %s", url, exc)
            return None

        # Primary selector used on Private Property detail pages.
        price_el = soup.select_one(".listing-price-display__price")
        if price_el:
            return self._extract_price(price_el.get_text(strip=True))

        # Fallback: any element whose class contains "price" and parses to a number.
        for candidate in soup.find_all(class_=lambda c: c and "price" in c.lower()):
            text = str(candidate.get_text(strip=True))
            price = self._extract_price(text)
            if price is not None:
                return price

        return None
