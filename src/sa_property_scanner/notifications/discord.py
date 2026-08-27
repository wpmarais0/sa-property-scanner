"""Discord webhook notifier with rich embeds."""

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger
from sa_property_scanner.schemas import NotificationPayload

from .base import Notifier

logger = get_logger(__name__)


class DiscordNotifier(Notifier):
    """Sends rich embed notifications via Discord webhook."""

    name = "discord"

    def __init__(self) -> None:
        self.webhook_url = settings.discord_webhook_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def send(self, payload: NotificationPayload) -> bool:
        """Send a rich embed to the configured Discord channel."""
        listing = payload.listing

        # Determine embed color based on event type
        color_map = {
            "new_listing": "00ff00",      # Green
            "price_drop": "ff6600",       # Orange
            "price_increase": "ff0000",   # Red
        }
        color = color_map.get(payload.event_type, "0099ff")  # Default blue

        # Build the embed
        embed = DiscordEmbed(
            title=listing.title or "Property Alert",
            description=f"[{listing.location or 'View Location'}]({listing.url})",
            color=color,
            url=listing.url,
        )

        # Add image if available
        if listing.image_url:
            embed.set_image(url=listing.image_url)

        # Add thumbnail (source icon could go here)
        embed.set_footer(text=f"Source: {listing.source}")
        embed.set_timestamp()

        # Add price field
        price_display = listing.price_text or (
            f"R {listing.price:,.0f}" if listing.price else "Price on request"
        )
        embed.add_embed_field(name="💰 Price", value=price_display, inline=True)

        # Add bedrooms if available
        if listing.bedrooms:
            embed.add_embed_field(name="🛏 Bedrooms", value=str(listing.bedrooms), inline=True)

        # Add bathrooms if available
        if listing.bathrooms:
            embed.add_embed_field(name="🛁 Bathrooms", value=str(listing.bathrooms), inline=True)

        # Add property type if available
        if listing.property_type:
            embed.add_embed_field(
                name="🏠 Type", value=listing.property_type.title(), inline=True
            )

        # Add size if available
        if listing.size_sqm:
            embed.add_embed_field(
                name="📐 Size", value=f"{listing.size_sqm} m²", inline=True
            )

        # Add garages if available
        if listing.garages:
            embed.add_embed_field(
                name="🚗 Garages", value=str(listing.garages), inline=True
            )

        # Add soft amenity notes if detected
        if payload.amenity_notes:
            embed.add_embed_field(
                name="📝 Notes",
                value="\n".join(payload.amenity_notes),
                inline=False,
            )

        # Add agent if available
        if listing.agent_name:
            embed.add_embed_field(
                name="🏢 Agent", value=listing.agent_name, inline=False
            )

        # Event type label
        event_labels = {
            "new_listing": "🆕 New Listing",
            "price_drop": "🔥 Price Drop",
            "price_increase": "📈 Price Increase",
        }
        event_label = event_labels.get(payload.event_type, "📢 Property Alert")

        try:
            webhook = AsyncDiscordWebhook(url=self.webhook_url)
            webhook.add_embed(embed)
            webhook.set_content(event_label)
            await webhook.execute()
            logger.info("Discord alert sent for %s", listing.external_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Discord send failed: %s", exc)
            return False
