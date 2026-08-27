"""Playwright stealth mixin for dynamic scraping targets."""

import json
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import stealth

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger

logger = get_logger(__name__)


class PlaywrightMixin:
    """Provides an async Playwright browser context with stealth patches."""

    async def _launch_browser(self) -> BrowserContext:
        """Launch a headless Chromium browser with stealth enabled."""
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-ZA",
            timezone_id="Africa/Johannesburg",
        )
        return context

    async def _stealth_page(self, context: BrowserContext) -> Page:
        """Create a new page and apply stealth patches."""
        page = await context.new_page()
        await stealth(page)
        return page

    async def _intercept_api_response(
        self, page: Page, url_pattern: str
    ) -> dict[str, Any] | None:
        """Navigate to the search URL and intercept a matching API response."""
        intercepted_data: dict[str, Any] | None = None

        async def handle_route(route, request):
            nonlocal intercepted_data
            response = await route.fetch()
            body = await response.text()
            try:
                intercepted_data = json.loads(body)
            except json.JSONDecodeError:
                pass
            await route.fulfill(response=response)

        await page.route(url_pattern, handle_route)
        await page.goto(self.search_url, wait_until="networkidle", timeout=settings.playwright_timeout)  # type: ignore[attr-defined]
        await page.wait_for_timeout(2000)
        return intercepted_data

    async def _close_browser(self, context: BrowserContext) -> None:
        """Gracefully close browser and playwright."""
        await context.close()
        await self._playwright.stop()
