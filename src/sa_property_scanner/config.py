"""Application configuration via Pydantic Settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    # Database
    database_url: str = Field(default="sqlite:///./properties.db")

    # Notifications
    telegram_bot_token: str | None = Field(default=None)
    telegram_chat_id: str | None = Field(default=None)
    discord_webhook_url: str | None = Field(default=None)

    # Source toggles & URLs
    property24_enabled: bool = Field(default=False)
    property24_search_url: str | None = Field(default=None)

    private_property_enabled: bool = Field(default=False)
    private_property_search_url: str | None = Field(default=None)

    pam_golding_enabled: bool = Field(default=True)
    pam_golding_search_url: str | None = Field(default=None)

    seeff_enabled: bool = Field(default=True)
    seeff_search_url: str | None = Field(default=None)

    sothebys_enabled: bool = Field(default=True)
    sothebys_search_url: str | None = Field(default=None)

    # Filtering
    min_price: int | None = Field(default=None)
    max_price: int | None = Field(default=None)
    bedrooms_min: int | None = Field(default=None)
    bedrooms_max: int | None = Field(default=None)
    bathrooms_min: int | None = Field(default=None)
    bathrooms_max: int | None = Field(default=None)
    garage_min: int | None = Field(default=None)
    pet_friendly: bool = Field(default=False)
    own_yard: bool = Field(default=False)
    fibre_internet: bool = Field(default=False)
    property_types: list[str] | None = Field(default=None)

    # Pagination
    pagination_max_pages: int = Field(default=1)

    # Behaviour
    sleep_between_requests: int = Field(default=2)
    playwright_headless: bool = Field(default=True)
    playwright_timeout: int = Field(default=30_000)
    max_retries: int = Field(default=3)

    # Monitoring
    healthchecks_url: str | None = Field(default=None)

    @field_validator("property_types", mode="before")
    @classmethod
    def split_property_types(cls, v: str | None) -> list[str] | None:
        if v is None:
            return None
        return [t.strip().lower() for t in v.split(",")]

    def is_source_enabled(self, name: str) -> bool:
        """Check if a source is enabled by name."""
        mapping = {
            "property24": self.property24_enabled,
            "private_property": self.private_property_enabled,
            "pam_golding": self.pam_golding_enabled,
            "seeff": self.seeff_enabled,
            "sothebys": self.sothebys_enabled,
        }
        return mapping.get(name, False)

    def get_source_url(self, name: str) -> str | None:
        """Get the search URL for a source by name."""
        mapping = {
            "property24": self.property24_search_url,
            "private_property": self.private_property_search_url,
            "pam_golding": self.pam_golding_search_url,
            "seeff": self.seeff_search_url,
            "sothebys": self.sothebys_search_url,
        }
        return mapping.get(name)


settings = Settings()
