"""Source adapter registry."""

from typing import Type

from sa_property_scanner.config import settings
from sa_property_scanner.logger import get_logger

from .base import SourceAdapter
from .pam_golding import PamGoldingSource
from .private_property import PrivatePropertySource
from .property24 import Property24Source
from .seeff import SeeffSource
from .sothebys import SothebysSource

logger = get_logger(__name__)

REGISTRY: dict[str, Type[SourceAdapter]] = {
    Property24Source.name: Property24Source,
    PrivatePropertySource.name: PrivatePropertySource,
    PamGoldingSource.name: PamGoldingSource,
    SeeffSource.name: SeeffSource,
    SothebysSource.name: SothebysSource,
}


def get_enabled_sources() -> list[SourceAdapter]:
    """Instantiate all enabled and configured source adapters."""
    instances: list[SourceAdapter] = []
    for name, cls in REGISTRY.items():
        if not settings.is_source_enabled(name):
            logger.debug("Source %s is disabled.", name)
            continue
        url = settings.get_source_url(name)
        if not url:
            logger.warning("Source %s is enabled but has no URL configured.", name)
            continue
        instances.append(cls(search_url=url))
        logger.info("Source %s enabled → %s", name, url)
    return instances
