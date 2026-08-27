"""Sotheby's Realty / Lew Geffen Sotheby's source adapter.

Lew Geffen merged with Sotheby's International Realty. Their site uses
clean HTML with <a class="property-card-sm"> cards.
"""

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class SothebysSource(SourceAdapter):
    """Adapter for sothebysrealty.co.za (static HTML scraping)."""

    name = "sothebys"
    mode = "static"

    def fetch(self, url: str) -> str:
        """Fetch search result page HTML."""
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:
        """Parse listing cards from HTML into RawListing objects."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[RawListing] = []

        # Sotheby's uses <a class="property-card-sm" data-id="3423786">
        cards = soup.find_all("a", class_="property-card-sm")

        for card in cards:
            try:
                external_id = str(card.get("data-id", ""))
                if not external_id:
                    continue

                href = card.get("href")
                url_abs = self._make_absolute_url(self.search_url, href)

                price_tag = card.select_one(".card-price")
                price_text = price_tag.get_text(strip=True) if price_tag else None
                price = self._extract_price(price_text)

                desc_tag = card.select_one(".card-description")
                title = desc_tag.get_text(strip=True) if desc_tag else None

                # Location is usually in the title, e.g. "... For Sale in Sandy Point"
                location = None
                if title and " in " in title:
                    location = title.split(" in ", 1)[-1].strip()

                # Extract property type from title if present
                property_type = None
                if title:
                    type_keywords = ["house", "apartment", "townhouse", "villa", "plot", "land", "farm", "freehold", "duplex", "penthouse"]
                    title_lower = title.lower()
                    for kw in type_keywords:
                        if kw in title_lower:
                            property_type = kw
                            break

                # Extract features from text nodes
                bedrooms = bathrooms = garage = size_sqm = None
                exclusive_mandate = False
                for text_node in card.find_all(string=True):
                    text = str(text_node).strip()
                    if not text:
                        continue
                    text_lower = text.lower()

                    if bedrooms is None and "bed" in text_lower and text[0].isdigit():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bedrooms = int(digits) if digits else None
                    elif bathrooms is None and "bath" in text_lower and text[0].isdigit():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bathrooms = int(digits) if digits else None
                    elif garage is None and "parking" in text_lower and text[0].isdigit():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        garage = int(digits) if digits else None
                    elif size_sqm is None and "m\u00b2" in text:
                        digits = "".join(ch for ch in text if ch.isdigit() and ch != "\u00b2")
                        size_sqm = int(digits) if digits else None
                    elif "exclusive mandate" in text_lower:
                        exclusive_mandate = True

                img_tag = card.select_one("img")
                image_url = None
                if img_tag:
                    image_url = self._make_absolute_url(
                        self.search_url,
                        img_tag.get("src") or img_tag.get("data-src"),
                    )

                listing = RawListing(
                    external_id=external_id,
                    url=url_abs or href or "",
                    title=title,
                    price=price,
                    price_text=price_text,
                    location=location,
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    garages=garage,
                    property_type=property_type,
                    size_sqm=size_sqm,
                    image_url=image_url,
                )
                listings.append(listing)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Failed to parse Sotheby's card: %s", exc)
                continue

        self.logger.info("Sotheby's parsed %d listings", len(listings))
        return listings
