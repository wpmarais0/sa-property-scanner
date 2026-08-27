#!/usr/bin/env python3
"""Quick test script to verify Discord webhook is working.

Usage:
    python test_webhook.py YOUR_WEBHOOK_URL
"""

import asyncio
import sys

from sa_property_scanner.notifications.discord import DiscordNotifier
from sa_property_scanner.schemas import ListingRead, NotificationPayload


async def main(webhook_url: str) -> None:
    """Send a test notification to the Discord webhook."""
    import os
    os.environ["DISCORD_WEBHOOK_URL"] = webhook_url

    notifier = DiscordNotifier()

    dummy_listing = ListingRead(
        id=99999,
        source="test",
        external_id="TEST123",
        url="https://www.sothebysrealty.co.za/results/residential/for-sale",
        title="3 Bedroom House in Testville",
        price=1_450_000,
        price_text="R 1,450,000",
        location="Testville, Western Cape",
        bedrooms=3,
        bathrooms=2,
        garages=1,
        property_type="house",
        first_seen_at="2024-01-01T00:00:00",
        last_seen_at="2024-01-01T00:00:00",
    )

    payload = NotificationPayload(
        event_type="new_listing",
        listing=dummy_listing,
        message="Test notification from property scanner",
        amenity_notes=[
            "🐕 Pet friendly mention",
            "🌳 Own yard/stand mention",
        ],
    )

    print(f"Sending test notification to Discord webhook...")
    success = await notifier.send(payload)
    if success:
        print("✅ Test notification sent successfully! Check your Discord channel.")
    else:
        print("❌ Failed to send test notification.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_webhook.py YOUR_WEBHOOK_URL")
        print("\nTo get a webhook URL:")
        print("  1. Open Discord → Server Settings → Integrations → Webhooks")
        print("  2. Click 'New Webhook' → Copy Webhook URL")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
