"""Seeff source adapter.

Seeff uses a custom property platform with clear CSS classes.
We use static scraping on the server-rendered HTML.
"""

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class SeeffSource(SourceAdapter):
    """Adapter for seeff.com (static HTML scraping)."""

    name = "seeff"
    mode = "static"

    def fetch(self, url: str) -> str:
        """Fetch search result page HTML."""
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:
        """Parse listing cards from HTML into RawListing objects."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[RawListing] = []

        # Seeff uses <div class="seeff-listing-card" data-id="1918694">
        cards = soup.find_all("div", class_="seeff-listing-card")

        for card in cards:
            try:
                external_id = str(card.get("data-id", ""))
                if not external_id:
                    continue

                link_tag = card.select_one('a[href^="/results/"]')
                href = link_tag.get("href") if link_tag else None
                url_abs = self._make_absolute_url(self.search_url, href)

                price_tag = card.select_one(".card-price")
                price_text = price_tag.get_text(strip=True) if price_tag else None
                price = self._extract_price(price_text)

                title_tag = card.select_one(".card-heading")
                title = title_tag.get_text(strip=True) if title_tag else None

                # Location is usually in the title, e.g. "... For Sale in Tulbagh"
                location = None
                if title and " in " in title:
                    location = title.split(" in ", 1)[-1].strip()

                # Beds / Baths / Garage are text nodes matching patterns
                bedrooms = bathrooms = garages = None
                for el in card.find_all(string=True):
                    text = str(el).strip()
                    if not text:
                        continue
                    if bedrooms is None and "bed" in text.lower():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bedrooms = int(digits) if digits else None
                    elif bathrooms is None and "bath" in text.lower():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bathrooms = int(digits) if digits else None
                    elif garages is None and "garage" in text.lower():
                        digits = "".join(ch for ch in text if ch.isdigit())
                        garages = int(digits) if digits else None

                img_tag = card.select_one(".card-img img")
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
                    garages=garages,
                    image_url=image_url,
                )
                listings.append(listing)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Failed to parse Seeff card: %s", exc)
                continue

        self.logger.info("Seeff parsed %d listings", len(listings))
        return listings
