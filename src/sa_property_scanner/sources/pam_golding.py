"""Pam Golding source adapter.

Pam Golding's site is a Nuxt/Vue SPA. We use static scraping on the
server-rendered HTML which contains the listing grid.
"""

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter


class PamGoldingSource(SourceAdapter):
    """Adapter for pamgolding.co.za (static HTML scraping)."""

    name = "pam_golding"
    mode = "static"

    def fetch(self, url: str) -> str:
        """Fetch search result page HTML."""
        return self._http_get(url)

    def parse(self, html: str) -> list[RawListing]:  # type: ignore[override]
        """Parse listing cards from HTML into RawListing objects."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[RawListing] = []

        # Pam Golding uses <article class="results__item"> for each card
        cards = soup.find_all("article", class_="results__item")

        for card in cards:
            try:
                link_tag = card.select_one("h3.results__item-heading a.results__item-heading-link")
                href = str(link_tag.get("href")) if link_tag else None
                title = str(link_tag.get_text(strip=True)) if link_tag else None
                url_abs = self._make_absolute_url(self.search_url, href)

                # Derive external_id from href slug, e.g. /property-details/.../bed1750466
                external_id = ""
                if href:
                    parts = href.rstrip("/").split("/")
                    external_id = parts[-1] if parts else href

                price_tag = card.select_one(".results__item-price")
                price_text = price_tag.get_text(strip=True) if price_tag else None
                price = self._extract_price(price_text)

                # Details are in .results__item-body-item ("3 beds", "2 baths", etc.)
                bedrooms = bathrooms = garages = None
                for item in card.select(".results__item-body-item"):
                    text = item.get_text(strip=True).lower()
                    if "bed" in text:
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bedrooms = int(digits) if digits else None
                    elif "bath" in text:
                        digits = "".join(ch for ch in text if ch.isdigit())
                        bathrooms = int(digits) if digits else None
                    elif "garage" in text:
                        digits = "".join(ch for ch in text if ch.isdigit())
                        garages = int(digits) if digits else None

                # Location is usually in the title, e.g. "Apartment for sale in Gresswold"
                location = None
                if title and " in " in title:
                    location = title.split(" in ", 1)[-1].strip()

                img_tag = card.select_one(".results__item-image-container img")
                image_url = None
                if img_tag:
                    image_url = self._make_absolute_url(
                        self.search_url,
                        img_tag.get("src") or img_tag.get("data-src"),
                    )

                listing = RawListing(
                    external_id=external_id or href or "",
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
                self.logger.warning("Failed to parse Pam Golding card: %s", exc)
                continue

        self.logger.info("Pam Golding parsed %d listings", len(listings))
        return listings
