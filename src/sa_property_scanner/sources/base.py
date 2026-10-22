"""Abstract base class for all property source adapters."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger
from sa_property_scanner.schemas import RawListing

logger = get_logger(__name__)


class SourceAdapter(ABC):
    """Base class that every source must implement."""

    name: str = "base"
    mode: str = "static"  # "static" or "playwright"

    def __init__(self, search_url: str) -> None:
        self.search_url = search_url
        self.logger = get_logger(f"sources.{self.name}")

    @abstractmethod
    def fetch(self, url: str) -> str | dict[str, Any]:
        """Fetch raw data from the given URL. Returns HTML string or parsed JSON."""
        ...

    @abstractmethod
    def parse(self, data: str | dict[str, Any]) -> list[RawListing]:
        """Parse raw data into a list of validated RawListing objects."""
        ...

    def verify_price(self, url: str, html: str | None = None) -> int | None:
        """Fetch a listing's detail page and return the verified price.

        The default implementation attempts several generic extraction strategies
        on the detail page HTML:

        1. Schema.org ``Offer`` / ``price`` JSON-LD.
        2. OpenGraph / meta price tags.
        3. Any element whose class contains "price" and parses to a number.

        Sources with reliable site-specific selectors should override this
        method. Returns ``None`` if no price could be determined.

        Args:
            url: The listing detail page URL.
            html: Optional pre-fetched detail page HTML. If omitted, the source
                should fetch the page itself.
        """
        try:
            if html is None:
                html = self.fetch(url)
            if not isinstance(html, str):
                return None
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.debug("Could not fetch detail page for verification %s: %s", url, exc)
            return None

        # 1. Schema.org JSON-LD (Offer / Product / Residence)
        for script in soup.find_all("script", type="application/ld+json"):
            if not script or not script.string:
                continue
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            candidates: list[dict[str, Any]] = []
            if isinstance(data, list):
                candidates = data
            elif isinstance(data, dict):
                candidates = [data]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("@type", "")
                types = item_type if isinstance(item_type, list) else [item_type]
                if any(t in ("Offer", "Product", "Residence", "SingleFamilyResidence") for t in types):
                    offer = item.get("offers") or item
                    if isinstance(offer, dict):
                        for key in ("price", "Price"):
                            if key in offer:
                                price = self._extract_price(str(offer[key]))
                                if price is not None:
                                    return price

        # 2. OpenGraph / Twitter / meta price tags
        for meta in soup.find_all("meta"):
            prop = str(meta.get("property", "")).lower()
            name = str(meta.get("name", "")).lower()
            content = meta.get("content")
            if content and ("price" in prop or "price" in name or prop in ("og:price:amount",)):
                price = self._extract_price(str(content))
                if price is not None:
                    return price

        # 3. Generic DOM element with "price" in its class
        for candidate in soup.find_all(class_=lambda c: c and "price" in c.lower()):
            text = str(candidate.get_text(strip=True))
            price = self._extract_price(text)
            if price is not None:
                return price

        return None

    def _http_get(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Polite HTTP GET with retries, user-agent rotation, and configurable delay."""
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "en-ZA,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if headers:
            default_headers.update(headers)

        @retry(
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((requests.RequestException, httpx.HTTPError)),
            reraise=True,
        )
        def _request() -> str:
            self.logger.debug("GET %s", url)
            resp = requests.get(url, headers=default_headers, timeout=30)
            resp.raise_for_status()
            return resp.text

        return _request()

    def _extract_price(self, text: str | None) -> int | None:
        """Extract a price integer from a price string.

        Handles common South African formats such as ``R 1 300 000``,
        ``R1,300,000`` and shorthand like ``R 1.3 million`` / ``R 1.3m``.
        """
        if not text:
            return None

        normalized = text.replace("R", "").replace("\xa0", " ").strip().lower()

        # Leading shorthand: "1.3 million", "13m", "850k".
        leading_shorthand = re.match(
            r"(\d+(?:[.,]\d+)?)\s*(m|million|k|thousand)\b",
            normalized,
        )
        if leading_shorthand:
            amount = float(leading_shorthand.group(1).replace(",", "."))
            multiplier = (
                1_000_000 if leading_shorthand.group(2) in ("m", "million") else 1_000
            )
            return int(amount * multiplier)

        # Explicit full price: first contiguous run of digits (with spaces/commas
        # as thousands separators). Stop at the first non-digit/non-separator.
        explicit_match = re.match(r"[\d\s,]+", normalized)
        if explicit_match:
            raw = explicit_match.group(0).replace(" ", "").replace(",", "")
            digits = "".join(ch for ch in raw if ch.isdigit())
            price = int(digits) if digits else None
            if price is not None and price >= 1_000:
                return price

        # Fall back to shorthand anywhere in the string.
        fallback_shorthand = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(m|million|k|thousand)\b",
            normalized,
        )
        if fallback_shorthand:
            amount = float(fallback_shorthand.group(1).replace(",", "."))
            multiplier = (
                1_000_000 if fallback_shorthand.group(2) in ("m", "million") else 1_000
            )
            return int(amount * multiplier)

        # Last resort: any digits at all.
        digits = "".join(ch for ch in normalized if ch.isdigit())
        return int(digits) if digits else None

    def _make_absolute_url(self, base_url: str, href: object) -> str | None:
        """Convert a potentially relative URL to absolute."""
        if not href:
            return None
        href_str = str(href).strip()
        if href_str.startswith("http"):
            return href_str
        from urllib.parse import urljoin

        return urljoin(base_url, href_str)

    @staticmethod
    def _bs_text(value: object) -> str:
        """Safely convert a BeautifulSoup value to a stripped string."""
        return str(value).strip() if value else ""

    @staticmethod
    def _bs_attr(tag: object, attr: str) -> str | None:
        """Safely extract a string attribute from a BeautifulSoup tag."""
        if tag is None:
            return None
        val = getattr(tag, "get", lambda x: None)(attr)
        if val is None:
            return None
        return str(val).strip() or None

    def build_page_url(self, base_url: str, page: int) -> str:
        """Build a paginated URL. Override for sources with non-standard pagination."""
        if page <= 1:
            return base_url
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page)]
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
