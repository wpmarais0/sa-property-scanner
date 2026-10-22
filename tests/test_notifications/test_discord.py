"""Tests for the Discord notifier."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sa_property_scanner.notifications.base import Notifier
from sa_property_scanner.notifications.discord import DiscordNotifier
from sa_property_scanner.schemas import ListingRead, NotificationPayload


def _make_payload(price: int | None, price_text: str | None) -> NotificationPayload:
    listing = ListingRead(
        id=1,
        source="test_source",
        external_id="abc123",
        url="https://example.com/listing",
        title="Test Property",
        price=price,
        price_text=price_text,
        location="Cape Town",
        bedrooms=3,
        bathrooms=2,
        garages=1,
        property_type="house",
        size_sqm=200,
        image_url="https://example.com/image.jpg",
        agent_name="Test Agent",
        first_seen_at=datetime.now(),
        last_seen_at=datetime.now(),
    )
    return NotificationPayload(
        event_type="new_listing",
        listing=listing,
        message="test",
    )


@pytest.mark.asyncio
async def test_discord_prefers_numeric_price_over_price_text():
    """When both price and price_text are present, the numeric price is displayed."""
    notifier = DiscordNotifier()
    payload = _make_payload(price=13_000_000, price_text="R 1.3 million")

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "sa_property_scanner.notifications.discord.AsyncDiscordWebhook",
        return_value=MagicMock(execute=AsyncMock(return_value=mock_response)),
    ) as mock_webhook_class:
        success = await notifier.send(payload)

    assert success is True
    mock_webhook = mock_webhook_class.return_value
    assert mock_webhook.add_embed.called
    embed = mock_webhook.add_embed.call_args[0][0]

    price_field = next(
        (field for field in embed.fields if field.get("name") == "💰 Price"),
        None,
    )
    assert price_field is not None
    assert price_field["value"] == "R 13,000,000"


@pytest.mark.asyncio
async def test_discord_falls_back_to_price_text():
    """When numeric price is unavailable, price_text is used."""
    notifier = DiscordNotifier()
    payload = _make_payload(price=None, price_text="POA")

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch(
        "sa_property_scanner.notifications.discord.AsyncDiscordWebhook",
        return_value=MagicMock(execute=AsyncMock(return_value=mock_response)),
    ) as mock_webhook_class:
        success = await notifier.send(payload)

    assert success is True
    embed = mock_webhook_class.return_value.add_embed.call_args[0][0]
    price_field = next(
        (field for field in embed.fields if field.get("name") == "💰 Price"),
        None,
    )
    assert price_field is not None
    assert price_field["value"] == "POA"


def test_base_notifier_prefers_numeric_price():
    """The shared base formatter should also prefer the numeric price."""

    class DummyNotifier(Notifier):
        name = "dummy"

        async def send(self, payload: NotificationPayload) -> bool:
            return True

    notifier = DummyNotifier()
    message = notifier._format_message(_make_payload(price=13_000_000, price_text="R 1.3 million"))
    assert "R 13,000,000" in message
    assert "R 1.3 million" not in message
