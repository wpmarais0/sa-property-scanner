"""Tests for infrastructure modules: database, health, and CLI."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy.ext.asyncio import AsyncSession

from sa_property_scanner.cli import main
from sa_property_scanner.database import get_session, init_db, make_async_url
from sa_property_scanner.health import send_heartbeat, send_heartbeat_sync

# ---------------------------------------------------------------------------
# database.py
# ---------------------------------------------------------------------------


def test_make_async_url_sqlite():
    """SQLite URL should be converted to async aiosqlite driver."""
    assert make_async_url("sqlite:///./properties.db") == "sqlite+aiosqlite:///./properties.db"


def test_make_async_url_postgresql():
    """PostgreSQL URL should be converted to async asyncpg driver."""
    assert (
        make_async_url("postgresql://scanner:scanner@localhost:5432/properties")
        == "postgresql+asyncpg://scanner:scanner@localhost:5432/properties"
    )


def test_make_async_url_other():
    """Unknown driver URLs should pass through unchanged."""
    assert make_async_url("mysql+pymysql://user:pass@localhost/db") == "mysql+pymysql://user:pass@localhost/db"


@pytest.mark.asyncio
async def test_init_db():
    """init_db should create all tables in an async engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    with patch("sa_property_scanner.database.async_engine", engine):
        await init_db()

    async with engine.begin() as conn:
        from sqlalchemy import inspect

        def _check_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()

        tables = await conn.run_sync(_check_tables)

    assert "listings" in tables
    assert "price_history" in tables
    assert "scan_logs" in tables
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_session():
    """get_session should yield an async session."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    with patch("sa_property_scanner.database.AsyncSessionLocal", async_session_local):
        async for session in get_session():
            assert isinstance(session, AsyncSession)
            break
    await engine.dispose()


# ---------------------------------------------------------------------------
# health.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_heartbeat_skips_when_no_url():
    """No URL configured → heartbeat should be a no-op."""
    with patch("sa_property_scanner.health.settings") as mock_settings:
        mock_settings.healthchecks_url = None
        await send_heartbeat()  # should not raise


@pytest.mark.asyncio
async def test_send_heartbeat_success():
    """Successful heartbeat should call the configured URL."""
    with patch("sa_property_scanner.health.settings") as mock_settings:
        mock_settings.healthchecks_url = "https://hc-ping.com/test-uuid"
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
        with patch("sa_property_scanner.health.httpx.AsyncClient", return_value=mock_client):
            await send_heartbeat()
        mock_client.get.assert_called_once_with("https://hc-ping.com/test-uuid")


def test_send_heartbeat_sync_skips_when_no_url():
    """No URL configured → sync heartbeat should be a no-op."""
    with patch("sa_property_scanner.health.settings") as mock_settings:
        mock_settings.healthchecks_url = None
        send_heartbeat_sync()  # should not raise


def test_send_heartbeat_sync_success():
    """Successful sync heartbeat should call requests.get."""
    with patch("sa_property_scanner.health.settings") as mock_settings:
        mock_settings.healthchecks_url = "https://hc-ping.com/sync-uuid"
        with patch("sa_property_scanner.health.requests.get") as mock_get:
            send_heartbeat_sync()
        mock_get.assert_called_once_with("https://hc-ping.com/sync-uuid", timeout=10)


# ---------------------------------------------------------------------------
# cli.py
# ---------------------------------------------------------------------------


def test_scan_command():
    """CLI scan command should run the scraper orchestrator and send heartbeat."""
    runner = CliRunner()
    with (
        patch("sa_property_scanner.cli.run_scan") as mock_run_scan,
        patch("sa_property_scanner.cli.send_heartbeat_sync") as mock_heartbeat,
    ):
        result = runner.invoke(main, ["scan"])
    assert result.exit_code == 0
    mock_run_scan.assert_called_once()
    mock_heartbeat.assert_called_once()


def test_init_db_command():
    """CLI init-db command should create all tables."""
    runner = CliRunner()
    with patch("sa_property_scanner.cli.init_db", new_callable=AsyncMock) as mock_init_db:
        result = runner.invoke(main, ["init-db"])
    assert result.exit_code == 0
    mock_init_db.assert_awaited_once()


def test_migrate_command():
    """CLI migrate command should invoke alembic upgrade head."""
    runner = CliRunner()
    with patch("sa_property_scanner.cli.subprocess.run") as mock_run:
        result = runner.invoke(main, ["migrate"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(["alembic", "upgrade", "head"], check=True)
