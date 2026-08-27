"""Notification gateway."""

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger

from .base import Notifier
from .discord import DiscordNotifier
from .telegram import TelegramNotifier

logger = get_logger(__name__)


def get_notifiers() -> list[Notifier]:
    """Instantiate all configured notifiers."""
    notifiers: list[Notifier] = []

    if settings.telegram_bot_token and settings.telegram_chat_id:
        notifiers.append(TelegramNotifier())
        logger.info("Telegram notifier enabled.")
    else:
        logger.debug("Telegram notifier not configured.")

    if settings.discord_webhook_url:
        notifiers.append(DiscordNotifier())
        logger.info("Discord notifier enabled.")
    else:
        logger.debug("Discord notifier not configured.")

    if not notifiers:
        logger.warning("No notifiers are configured — alerts will be silently dropped!")

    return notifiers
