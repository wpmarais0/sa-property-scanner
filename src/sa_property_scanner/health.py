"""Health monitoring via external heartbeat ping."""

import httpx
import requests

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger

logger = get_logger(__name__)


async def send_heartbeat() -> None:
    """Ping the configured healthchecks.io (or compatible) URL."""
    if not settings.healthchecks_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.healthchecks_url)
            response.raise_for_status()
        logger.debug("Healthcheck ping sent.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Healthcheck ping failed: %s", exc)


def send_heartbeat_sync() -> None:
    """Synchronous wrapper for healthcheck ping."""
    if not settings.healthchecks_url:
        return
    try:
        requests.get(settings.healthchecks_url, timeout=10)
        logger.debug("Healthcheck ping sent.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Healthcheck ping failed: %s", exc)
