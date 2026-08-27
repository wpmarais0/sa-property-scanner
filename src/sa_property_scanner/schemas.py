"""Pydantic schemas for data validation and transfer."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RawListing(BaseModel):
    """A listing as extracted directly from a source (before DB persistence)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    title: str | None = Field(default=None)
    price: int | None = Field(default=None)
    price_text: str | None = Field(default=None)
    location: str | None = Field(default=None)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    garages: int | None = Field(default=None, ge=0)
    property_type: str | None = Field(default=None)
    size_sqm: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None)
    description: str | None = Field(default=None)
    agent_name: str | None = Field(default=None)

    @field_validator("price_text", mode="before")
    @classmethod
    def stringify_price_text(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v).strip()

    @model_validator(mode="after")
    def require_price_or_text(self) -> "RawListing":
        if self.price is None and self.price_text is None:
            raise ValueError("Either price or price_text must be provided")
        return self


class ListingRead(BaseModel):
    """Schema for reading a listing from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    url: str
    title: str | None
    price: int | None
    price_text: str | None
    location: str | None
    bedrooms: int | None
    bathrooms: int | None
    garages: int | None
    property_type: str | None
    size_sqm: int | None
    image_url: str | None
    agent_name: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class PriceChangeEvent(BaseModel):
    """Emitted when a listing's price changes."""

    listing: ListingRead
    old_price: int | None
    new_price: int | None
    old_price_text: str | None
    new_price_text: str | None


class NotificationPayload(BaseModel):
    """Unified payload sent to any notifier."""

    event_type: str  # "new_listing" | "price_drop" | "price_increase"
    listing: ListingRead
    old_price: int | None = None
    message: str
    amenity_notes: list[str] = []
