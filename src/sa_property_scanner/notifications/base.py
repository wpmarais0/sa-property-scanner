"""Abstract base notifier."""

from abc import ABC, abstractmethod

from sa_property_scanner.schemas import NotificationPayload


class Notifier(ABC):
    """Base class for all notification channels."""

    name: str = "base"

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send a notification. Returns True on success."""
        ...

    def _format_message(self, payload: NotificationPayload) -> str:
        """Build a human-readable markdown message."""
        listing = payload.listing

        if listing.price is not None:
            price_display = f"R {listing.price:,.0f}"
        elif listing.price_text:
            price_display = listing.price_text
        else:
            price_display = "Price on request"

        lines = [
            f"🚨 *{payload.event_type.replace('_', ' ').title()}*",
            "",
            f"*{listing.title or 'Property'}*",
            f"💰 Price: {price_display}",
        ]
        if listing.location:
            lines.append(f"📍 {listing.location}")
        if listing.bedrooms:
            lines.append(f"🛏 {listing.bedrooms} bed")
        if listing.bathrooms:
            lines.append(f"🛁 {listing.bathrooms} bath")
        lines.append(f"🔗 [View Listing]({listing.url})")
        return "\n".join(lines)
