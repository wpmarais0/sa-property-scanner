#!/usr/bin/env python3
"""Check database stats."""
import asyncio
from sqlalchemy import select, func
from sa_property_scanner.database import AsyncSessionLocal
from sa_property_scanner.models import Listing, ScanLog

async def stats():
    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(Listing))
        sources = await session.execute(select(Listing.source, func.count()).group_by(Listing.source))
        logs = await session.execute(select(ScanLog).order_by(ScanLog.id.desc()).limit(4))
        print(f"Total listings in DB: {total}")
        print("\nBy source:")
        for src, cnt in sources:
            print(f"  {src}: {cnt}")
        print("\nLast scans:")
        for log in logs.scalars():
            filtered = log.listings_found - log.new_listings - log.price_changes
            print(f"  {log.source}: found={log.listings_found}, new={log.new_listings}, filtered={filtered}, ok={log.success}")

asyncio.run(stats())
