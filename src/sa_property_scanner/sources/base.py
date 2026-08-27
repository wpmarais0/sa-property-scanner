"""Abstract base class for all property source adapters."""

from abc import ABC, abstractmethod
from typing import Any

import httpx
import requests
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

    def _http_get(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Polite HTTP GET with retries, user-agent rotation, and configurable delay."""
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
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
        """Extract the first integer sequence from a price string (handles R, spaces, commas)."""
        if not text:
            return None
        cleaned = (
            text.replace("R", "")
            .replace(" ", "")
            .replace(",", "")
            .replace("\xa0", "")
            .strip()
        )
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        return int(digits) if digits else None

    def _make_absolute_url(self, base_url: str, href: str | None) -> str | None:
        """Convert a potentially relative URL to absolute."""
        if not href:
            return None
        if href.startswith("http"):
            return href
        from urllib.parse import urljoin

        return urljoin(base_url, href)

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
