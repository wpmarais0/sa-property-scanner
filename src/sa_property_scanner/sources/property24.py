"""Property24 source adapter.

Property24 is a Next.js SPA. We use Playwright to render the page and
extract listings either from __NEXT_DATA__ JSON or directly from the
server-rendered HTML tiles.
"""

import json
from typing import Any

from bs4 import BeautifulSoup

from sa_property_scanner.schemas import RawListing

from .base import SourceAdapter
from .playwright_mixin import PlaywrightMixin


class Property24Source(SourceAdapter, PlaywrightMixin):
    """Adapter for property24.com (Playwright + HTML/JSON parsing)."""

    name = "property24"
    mode = "playwright"

    def build_page_url(self, base_url: str, page: int) -> str:
        """Property24 uses /pN path suffix for pagination."""
        if page <= 1:
            return base_url
        # Remove any existing /pN suffix first
        import re

        clean = re.sub(r"/p\d+$", "", base_url.rstrip("/"))
        return f"{clean}/p{page}"

    async def fetch(self, url: str) -> str:  # type: ignore[override]
        """Navigate to the search page and return rendered HTML."""
        context = await self._launch_browser()
        try:
            page = await self._stealth_page(context)
            await page.goto(url, wait_until="networkidle", timeout=self._playwright_timeout())
            await page.wait_for_timeout(2000)
            html = await page.content()
            return html
        finally:
            await self._close_browser(context)

    def _playwright_timeout(self) -> int:
        from sa_property_scanner.config import settings

        return settings.playwright_timeout

    def parse(self, html: str) -> list[RawListing]:  # type: ignore[override]
        """Parse listings from HTML, trying JSON first then direct HTML."""
        soup = BeautifulSoup(html, "html.parser")
        next_script = soup.find("script", id="__NEXT_DATA__")
        if next_script and next_script.string:
            try:
                data = json.loads(next_script.string)
                items = (
                    data.get("props", {}).get("pageProps", {}).get("listings", [])
                    or data.get("props", {}).get("pageProps", {}).get("searchResults", {}).get("listings", [])
                    or []
                )
                if items:
                    return self._parse_json_items(items)
            except json.JSONDecodeError:
                pass
        return self._parse_html_tiles(soup)

    def _parse_json_items(self, items: list[dict[str, Any]]) -> list[RawListing]:
        """Parse listings from JSON data."""
        listings: list[RawListing] = []
        for item in items:
            try:
                listing_id = str(item.get("listingId") or item.get("id") or item.get("ListingId"))
                if not listing_id:
                    continue
                price_raw = item.get("price") or item.get("Price") or item.get("displayPrice")
                price = self._extract_price(str(price_raw)) if price_raw else None
                listings.append(
                    RawListing(
                        external_id=listing_id,
                        url=self._make_absolute_url(
                            "https://www.property24.com",
                            item.get("url") or item.get("friendlyUrl") or f"/property/{listing_id}",
                        )
                        or f"https://www.property24.com/property/{listing_id}",
                        title=item.get("title") or item.get("heading"),
                        price=price,
                        price_text=str(price_raw) if price_raw else None,
                        location=item.get("location") or item.get("suburb") or item.get("address"),
                        bedrooms=item.get("bedrooms") or item.get("Bedrooms"),
                        bathrooms=item.get("bathrooms") or item.get("Bathrooms"),
                        property_type=item.get("propertyType") or item.get("category"),
                        size_sqm=item.get("erfSize") or item.get("floorSize"),
                        image_url=item.get("imageUrl") or item.get("thumbnail"),
                        description=item.get("description") or item.get("teaser"),
                        agent_name=item.get("agentName") or item.get("agencyName"),
                    )
                )
            except Exception as exc:
                self.logger.warning("Failed to parse Property24 JSON item: %s", exc)
        self.logger.info("Property24 parsed %d listings from JSON", len(listings))
        return listings

    def _parse_html_tiles(self, soup: BeautifulSoup) -> list[RawListing]:
        """Parse listings from server-rendered HTML tiles."""
        listings: list[RawListing] = []
        tiles = soup.find_all("div", class_="p24_tileContainer")

        for tile in tiles:
            try:
                listing_id = str(tile.get("data-listing-number", "")).lstrip("P")
                if not listing_id:
                    continue

                link_tag = tile.select_one('a[href^="/for-sale/"]')
                href = str(link_tag.get("href")) if link_tag else None
                url_abs = self._make_absolute_url("https://www.property24.com", href)

                price_tag = tile.select_one(".p24_price")
                price_text = None
                if price_tag:
                    price_text = price_tag.get_text(separator="\n", strip=True).split("\n")[0]
                price = self._extract_price(price_text)

                desc_tag = tile.select_one(".p24_description")
                title = None
                location = None
                if desc_tag:
                    title = desc_tag.get_text(strip=True)
                    loc_tag = desc_tag.select_one(".p24_location")
                    if loc_tag:
                        location = loc_tag.get_text(strip=True)

                bedrooms = bathrooms = None
                for feat in tile.select(".p24_featureDetails"):
                    feat_title = str(feat.get("title", "")).lower()
                    count_span = feat.select_one("span")
                    count = int(count_span.get_text(strip=True)) if count_span else None
                    if "bedroom" in feat_title:
                        bedrooms = count
                    elif "bathroom" in feat_title:
                        bathrooms = count

                img_tag = tile.select_one("img.js_P24_listingImage")
                image_url = str(img_tag.get("src")) if img_tag else None

                listings.append(
                    RawListing(
                        external_id=listing_id,
                        url=url_abs or href or "",
                        title=title,
                        price=price,
                        price_text=price_text,
                        location=location,
                        bedrooms=bedrooms,
                        bathrooms=bathrooms,
                        image_url=image_url,
                    )
                )
            except Exception as exc:
                self.logger.warning("Failed to parse Property24 HTML tile: %s", exc)

        self.logger.info("Property24 parsed %d listings from HTML", len(listings))
        return listings
