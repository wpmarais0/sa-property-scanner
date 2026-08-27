"""Tests for the scraper orchestrator."""

import pytest
from sqlalchemy import select

from sa_property_scanner.models import Listing, PriceHistory
from sa_property_scanner.schemas import RawListing
from sa_property_scanner.scraper import ScraperOrchestrator


@pytest.mark.asyncio
async def test_upsert_new_listing(db_session):
    """A new RawListing should be inserted into the DB."""
    scraper = ScraperOrchestrator()
    raw = RawListing(
        external_id="test-001",
        url="https://example.com/1",
        title="Test House",
        price=1_000_000,
        price_text="R 1 000 000",
        location="George",
        bedrooms=2,
        bathrooms=1,
    )

    is_new, is_price_change = await scraper._upsert_listing(db_session, "test_source", raw)
    await db_session.commit()

    assert is_new is True
    assert is_price_change is False

    result = await db_session.execute(select(Listing).where(Listing.external_id == "test-001"))
    listing = result.scalar_one()
    assert listing.price == 1_000_000
    assert listing.location == "George"

    # PriceHistory should be created
    ph_result = await db_session.execute(select(PriceHistory))
    assert ph_result.scalar_one().price == 1_000_000


@pytest.mark.asyncio
async def test_upsert_existing_no_change(db_session, sample_listing):
    """An existing listing with the same price should not trigger notifications."""
    db_session.add(sample_listing)
    await db_session.commit()

    scraper = ScraperOrchestrator()
    raw = RawListing(
        external_id="pg-12345",
        url="https://pamgolding.co.za/property/12345",
        title="3 Bedroom House in Knysna",
        price=2_500_000,
        price_text="R 2 500 000",
        location="Knysna, Western Cape",
        bedrooms=3,
        bathrooms=2,
    )

    is_new, is_price_change = await scraper._upsert_listing(db_session, "pam_golding", raw)
    await db_session.commit()

    assert is_new is False
    assert is_price_change is False


@pytest.mark.asyncio
async def test_upsert_price_change(db_session, sample_listing):
    """A price decrease should be detected and logged."""
    db_session.add(sample_listing)
    await db_session.commit()

    scraper = ScraperOrchestrator()
    raw = RawListing(
        external_id="pg-12345",
        url="https://pamgolding.co.za/property/12345",
        title="3 Bedroom House in Knysna",
        price=2_200_000,
        price_text="R 2 200 000",
        location="Knysna, Western Cape",
        bedrooms=3,
        bathrooms=2,
    )

    is_new, is_price_change = await scraper._upsert_listing(db_session, "pam_golding", raw)
    await db_session.commit()

    assert is_new is False
    assert is_price_change is True

    # Two price history records
    result = await db_session.execute(select(PriceHistory).where(PriceHistory.listing_id == sample_listing.id))
    histories = result.scalars().all()
    assert len(histories) == 2
    assert histories[-1].price == 2_200_000
