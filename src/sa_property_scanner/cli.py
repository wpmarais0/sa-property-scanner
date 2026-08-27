"""Command-line interface."""

import asyncio

import click

from sa_property_scanner.config import settings
from sa_property_scanner.database import init_db
from sa_property_scanner.health import send_heartbeat_sync
from sa_property_scanner.logger import get_logger
from sa_property_scanner.scraper import run_scan

logger = get_logger(__name__)


@click.group()
def main() -> None:
    """SA Property Scanner CLI."""
    pass


@main.command()
def init_db_cmd() -> None:
    """Initialise the database (create all tables)."""
    logger.info("Initialising database at %s", settings.database_url)
    asyncio.run(init_db())
    logger.info("Done.")


@main.command()
def migrate() -> None:
    """Run Alembic database migrations."""
    import subprocess

    logger.info("Running Alembic migrations...")
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    logger.info("Migrations complete.")


@main.command()
def scan() -> None:
    """Run a single scan across all enabled sources."""
    logger.info("Starting property scan...")
    run_scan()
    send_heartbeat_sync()
    logger.info("Scan complete.")


if __name__ == "__main__":
    main()
