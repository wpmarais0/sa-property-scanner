"""Core scraper orchestrator."""

from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sa_property_scanner.config import settings
from sa_property_scanner.database import AsyncSessionLocal
from sa_property_scanner.logger import get_logger
from sa_property_scanner.models import Listing, PriceHistory, ScanLog
from sa_property_scanner.notifications import get_notifiers
from sa_property_scanner.schemas import ListingRead, NotificationPayload, RawListing
from sa_property_scanner.sources import get_enabled_sources
from sa_property_scanner.sources.base import SourceAdapter

logger = get_logger(__name__)


class ScraperOrchestrator:
    """Runs the full scan pipeline for all enabled sources."""

    def __init__(self) -> None:
        self.notifiers = get_notifiers()
        self._notified_ids: set[str] = set()

    def _detect_amenities(self, raw: RawListing) -> list[str]:
        """Detect soft amenity mentions in title/description."""
        notes: list[str] = []
        text = " ".join(filter(None, [raw.title, raw.description, raw.location])).lower()

        if settings.pet_friendly and any(kw in text for kw in ("pet", "pets", "dog", "dogs", "cat", "cats")):
            notes.append("🐕 Pet friendly mention")
        if settings.own_yard and any(kw in text for kw in ("yard", "garden", "stand", "erf", "plot")):
            notes.append("🌳 Own yard/stand mention")
        if settings.fibre_internet and any(kw in text for kw in ("fibre", "fiber", "wifi", "wi-fi")):
            notes.append("🌐 Fibre/WiFi mention")

        return notes

    def _is_vacant_land(self, raw: RawListing) -> bool:
        """Return True if the listing appears to be vacant land."""
        if raw.property_type is not None:
            return raw.property_type.lower() in {"vacant land", "land", "plot", "stand", "erf"}
        # Fallback heuristic: title/description mentions land/erf/plot but not house/home
        text = " ".join(filter(None, [raw.title, raw.description])).lower()
        land_terms = ("vacant land", "vacant stand", "empty stand", "erf for sale", "plot for sale")
        residential_terms = ("house", "townhouse", "apartment", "flat", "duplex")
        has_land_term = any(term in text for term in land_terms)
        has_residential_term = any(term in text for term in residential_terms)
        return has_land_term and not has_residential_term

    def _passes_filter(self, raw: RawListing) -> bool:
        """Check if a listing matches the configured filter criteria."""
        # Location filter - Western Cape only
        if settings.western_cape_only:
            from sa_property_scanner.western_cape_towns import is_western_cape_location

            if not is_western_cape_location(raw.location):
                return False

        # Excluded location filter
        if settings.excluded_locations and raw.location:
            location_lower = raw.location.lower()
            if any(excluded in location_lower for excluded in settings.excluded_locations):
                return False

        # Price filter - property-type-specific ranges take precedence
        has_price_config = any(
            [
                settings.min_price is not None,
                settings.max_price is not None,
                settings.house_min_price is not None,
                settings.house_max_price is not None,
                settings.vacant_land_min_price is not None,
                settings.vacant_land_max_price is not None,
            ]
        )
        if has_price_config:
            if raw.price is None:
                # Reject POA / auction / unparseable-price listings so we never
                # send notifications with a price we cannot verify.
                return False

            if self._is_vacant_land(raw):
                min_p = settings.vacant_land_min_price if settings.vacant_land_min_price is not None else settings.min_price
                max_p = settings.vacant_land_max_price if settings.vacant_land_max_price is not None else settings.max_price
            else:
                min_p = settings.house_min_price if settings.house_min_price is not None else settings.min_price
                max_p = settings.house_max_price if settings.house_max_price is not None else settings.max_price

            if min_p is not None and raw.price < min_p:
                return False
            if max_p is not None and raw.price > max_p:
                return False

        # Bedroom filter
        if settings.bedrooms_min is not None and raw.bedrooms is not None and raw.bedrooms < settings.bedrooms_min:
            return False
        if settings.bedrooms_max is not None and raw.bedrooms is not None and raw.bedrooms > settings.bedrooms_max:
            return False

        # Bathroom filter
        if settings.bathrooms_min is not None and raw.bathrooms is not None and raw.bathrooms < settings.bathrooms_min:
            return False
        if settings.bathrooms_max is not None and raw.bathrooms is not None and raw.bathrooms > settings.bathrooms_max:
            return False

        # Garage filter
        if settings.garage_min is not None and raw.garages is not None and raw.garages < settings.garage_min:
            return False

        # Property type filter
        return not (
            settings.property_types is not None
            and raw.property_type is not None
            and raw.property_type.lower() not in settings.property_types
        )

    async def _verify_and_update_price(
        self, session: AsyncSession, source: SourceAdapter, raw: RawListing
    ) -> int | None:
        """Verify a new listing's price on its detail page and update the DB.

        Returns the verified price if it could be determined, otherwise ``None``.
        The DB record is updated in place when a different price is found.
        """
        try:
            if source.mode == "playwright":
                html = await source.fetch(raw.url)  # type: ignore[misc]
            else:
                html = source.fetch(raw.url)
        except Exception as exc:
            logger.warning("Could not verify price for %s %s: %s", source.name, raw.external_id, exc)
            return None

        verified_price = source.verify_price(raw.url, html)
        if verified_price is None or verified_price == raw.price:
            return verified_price

        # Update the just-created DB record with the verified price.
        result = await session.execute(
            select(Listing).where(
                and_(Listing.source == source.name, Listing.external_id == raw.external_id)
            )
        )
        listing = result.scalar_one_or_none()
        if listing is not None:
            listing.price = verified_price
            listing.price_text = f"R {verified_price:,.0f}".replace(",", " ")
            session.add(listing)
            await session.flush()
            logger.info(
                "Updated %s %s price from search %s to verified %s",
                source.name,
                raw.external_id,
                raw.price,
                verified_price,
            )
        return verified_price

    async def run(self) -> None:
        """Execute a complete scan across all enabled sources."""
        sources = get_enabled_sources()
        if not sources:
            logger.error("No sources are enabled or configured. Check your .env file.")
            return

        async with AsyncSessionLocal() as session:
            for source in sources:
                try:
                    await self._process_source(session, source)
                except Exception:
                    logger.exception("Unexpected error processing source %s", source.name)
                    continue
            await session.commit()

    async def _process_source(self, session: AsyncSession, source: SourceAdapter) -> None:
        """Fetch, parse, deduplicate, and notify for a single source."""
        log = ScanLog(source=source.name)
        session.add(log)
        await session.flush()

        all_raw_listings: list[RawListing] = []
        max_pages = settings.pagination_max_pages

        for page in range(1, max_pages + 1):
            page_url = source.build_page_url(source.search_url, page)
            try:
                logger.info("Fetching %s page %d ...", source.name, page)
                if source.mode == "playwright":
                    data = await source.fetch(page_url)  # type: ignore[misc]
                else:
                    data = source.fetch(page_url)
                page_listings = source.parse(data)
                if not page_listings:
                    logger.info("%s page %d returned no listings; stopping pagination.", source.name, page)
                    break
                all_raw_listings.extend(page_listings)
            except Exception as exc:
                log.success = False
                log.error_message = str(exc)
                log.finished_at = datetime.now(UTC)
                logger.exception("Source %s failed on page %d: %s", source.name, page, exc)
                return

        log.listings_found = len(all_raw_listings)

        new_count = price_change_count = filtered_count = 0
        for raw in all_raw_listings:
            try:
                if not self._passes_filter(raw):
                    filtered_count += 1
                    continue
                is_new, is_price_change = await self._upsert_listing(session, source.name, raw)
                if is_new:
                    new_count += 1
                    verified_price = await self._verify_and_update_price(session, source, raw)
                    if verified_price is not None and verified_price != raw.price:
                        raw.price = verified_price
                        raw.price_text = f"R {verified_price:,.0f}".replace(",", " ")
                        # Re-check filters with the verified price before notifying.
                        if not self._passes_filter(raw):
                            filtered_count += 1
                            logger.info(
                                "New listing %s verified price %d is outside filters; skipping notification.",
                                raw.external_id,
                                verified_price,
                            )
                            continue
                    await self._notify("new_listing", raw, source.name, session)
                elif is_price_change:
                    price_change_count += 1
                    await self._notify("price_drop", raw, source.name, session)
            except Exception as exc:
                logger.warning("Failed to process listing %s: %s", raw.external_id, exc)

        log.new_listings = new_count
        log.price_changes = price_change_count
        log.success = True
        log.finished_at = datetime.now(UTC)
        await session.commit()
        logger.info(
            "%s complete: %d found, %d filtered, %d new, %d price changes",
            source.name,
            log.listings_found,
            filtered_count,
            new_count,
            price_change_count,
        )

    async def _upsert_listing(self, session: AsyncSession, source_name: str, raw: RawListing) -> tuple[bool, bool]:
        """Insert or update a listing. Returns (is_new, is_price_change)."""
        result = await session.execute(
            select(Listing).where(and_(Listing.source == source_name, Listing.external_id == raw.external_id))
        )
        existing: Listing | None = result.scalar_one_or_none()

        if existing is None:
            listing = Listing(
                source=source_name,
                external_id=raw.external_id,
                url=raw.url,
                title=raw.title,
                price=raw.price,
                price_text=raw.price_text,
                location=raw.location,
                bedrooms=raw.bedrooms,
                bathrooms=raw.bathrooms,
                garages=raw.garages,
                property_type=raw.property_type,
                size_sqm=raw.size_sqm,
                image_url=raw.image_url,
                description=raw.description,
                agent_name=raw.agent_name,
                is_active=True,
            )
            session.add(listing)
            await session.flush()
            if raw.price is not None or raw.price_text is not None:
                session.add(
                    PriceHistory(
                        listing_id=listing.id,
                        price=raw.price,
                        price_text=raw.price_text,
                    )
                )
            return True, False

        existing.last_seen_at = datetime.now(UTC)
        existing.is_active = True
        existing.url = raw.url
        existing.title = raw.title or existing.title
        existing.location = raw.location or existing.location
        existing.image_url = raw.image_url or existing.image_url

        if raw.price is not None and existing.price != raw.price:
            session.add(
                PriceHistory(
                    listing_id=existing.id,
                    price=raw.price,
                    price_text=raw.price_text,
                )
            )
            logger.info(
                "Price change for %s: %s → %s",
                existing.external_id,
                existing.price,
                raw.price,
            )
            existing.price = raw.price
            existing.price_text = raw.price_text
            return False, True
        return False, False

    async def _notify(self, event_type: str, raw: RawListing, source_name: str, session: AsyncSession) -> None:
        """Dispatch notifications to all configured channels."""
        if not self.notifiers:
            return
        dedup_key = f"{event_type}:{source_name}:{raw.external_id}"
        if dedup_key in self._notified_ids:
            logger.debug("Skipping duplicate notification for %s", dedup_key)
            return
        self._notified_ids.add(dedup_key)
        result = await session.execute(
            select(Listing).where(and_(Listing.source == source_name, Listing.external_id == raw.external_id))
        )
        listing = result.scalar_one()
        notes = self._detect_amenities(raw)
        payload = NotificationPayload(
            event_type=event_type,
            listing=ListingRead.model_validate(listing),
            message=f"{event_type} from {source_name}",
            amenity_notes=notes,
        )
        for notifier in self.notifiers:
            try:
                await notifier.send(payload)
            except Exception as exc:
                logger.error("Notifier %s failed: %s", notifier.name, exc)


def run_scan() -> None:
    """Synchronous entrypoint for the scan orchestrator."""
    import asyncio

    orchestrator = ScraperOrchestrator()
    asyncio.run(orchestrator.run())
