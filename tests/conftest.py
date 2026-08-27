"""Pytest fixtures."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sa_property_scanner.database import Base
from sa_property_scanner.models import Listing

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Provide an async in-memory database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_local = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_local() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def sample_listing():
    """Return a sample Listing ORM object."""
    return Listing(
        source="pam_golding",
        external_id="pg-12345",
        url="https://pamgolding.co.za/property/12345",
        title="3 Bedroom House in Knysna",
        price=2_500_000,
        price_text="R 2 500 000",
        location="Knysna, Western Cape",
        bedrooms=3,
        bathrooms=2,
        property_type="house",
        is_active=True,
    )
