#!/usr/bin/env python3
"""Send a live test embed using the actual Discord notifier."""
import asyncio
import os
import sys

# Set up environment
os.environ["PYTHONPATH"] = "src"
sys.path.insert(0, "src")

from sa_property_scanner.notifications.discord import DiscordNotifier
from sa_property_scanner.schemas import ListingRead, NotificationPayload

async def main():
    notifier = DiscordNotifier()

    # Create a realistic listing
    dummy = ListingRead(
        id=1,
        source="seeff",
        external_id="TEST123",
        url="https://www.seeff.com/results/residential/for-sale",
        title="3 Bedroom House in Somerset West",
        price=1_450_000,
        price_text="R 1,450,000",
        location="Somerset West, Western Cape",
        bedrooms=3,
        bathrooms=2,
        garages=1,
        property_type="house",
        size_sqm=250,
        image_url="https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
        agent_name="Seeff Property Group",
        first_seen_at="2024-01-01T00:00:00",
        last_seen_at="2024-01-01T00:00:00",
    )

    payload = NotificationPayload(
        event_type="new_listing",
        listing=dummy,
        message="Live test notification",
        amenity_notes=["🐕 Pet friendly mention", "🌳 Own yard/stand mention"],
    )

    print("Sending live Discord embed test...")
    success = await notifier.send(payload)
    if success:
        print("✅ Embed sent! Check your Discord channel.")
    else:
        print("❌ Failed to send embed.")

if __name__ == "__main__":
    asyncio.run(main())
