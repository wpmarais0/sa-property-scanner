"""Database engine, session management, and declarative base."""

from collections.abc import AsyncGenerator

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger

logger = get_logger(__name__)

Base = declarative_base()


def make_async_url(url: str) -> str:
    """Convert a standard DB URL into an async driver URL."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async_engine = create_async_engine(
    make_async_url(settings.database_url),
    echo=False,
    poolclass=NullPool if "sqlite" in settings.database_url else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create all tables (dev convenience). Prefer Alembic in production."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised.")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
