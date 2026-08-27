"""Telegram Bot API notifier."""

import telegram
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger
from sa_property_scanner.schemas import NotificationPayload

from .base import Notifier

logger = get_logger(__name__)


class TelegramNotifier(Notifier):
    """Sends notifications via Telegram Bot API."""

    name = "telegram"

    def __init__(self) -> None:
        self.bot = telegram.Bot(token=settings.telegram_bot_token)  # type: ignore[arg-type]
        self.chat_id: str | int = settings.telegram_chat_id or ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(telegram.error.NetworkError),
        reraise=True,
    )
    async def send(self, payload: NotificationPayload) -> bool:
        """Send a markdown-formatted message to the configured chat."""
        text = self._format_message(payload)
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=telegram.constants.ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
            logger.info("Telegram alert sent for %s", payload.listing.external_id)
            return True
        except telegram.error.TelegramError as exc:
            logger.error("Telegram send failed: %s", exc)
            return False

    def _format_message(self, payload: NotificationPayload) -> str:
        """Format a notification payload as a markdown message."""
        listing = payload.listing
        event_emoji = {
            "new_listing": "🆕",
            "price_drop": "🔥",
            "price_increase": "📈",
        }.get(payload.event_type, "📢")

        lines = [
            f"{event_emoji} *{listing.title or 'Property Alert'}*",
            "",
            f"💰 Price: {listing.price_text or (f'R {listing.price:,.0f}' if listing.price else 'Price on request')}",
        ]

        if listing.bedrooms:
            lines.append(f"🛏 Bedrooms: {listing.bedrooms}")
        if listing.bathrooms:
            lines.append(f"🛁 Bathrooms: {listing.bathrooms}")
        if listing.garages:
            lines.append(f"🚗 Garages: {listing.garages}")
        if listing.property_type:
            lines.append(f"🏠 Type: {listing.property_type.title()}")
        if listing.size_sqm:
            lines.append(f"📐 Size: {listing.size_sqm} m²")

        lines.append(f"📍 Location: {listing.location or 'N/A'}")
        lines.append(f"🔗 [View Listing]({listing.url})")

        if payload.amenity_notes:
            lines.append("")
            lines.append("📝 *Notes:*")
            for note in payload.amenity_notes:
                lines.append(f"• {note}")

        lines.append("")
        lines.append(f"_Source: {listing.source}_")

        return "\n".join(lines)
