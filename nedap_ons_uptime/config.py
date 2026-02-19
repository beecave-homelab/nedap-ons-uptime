"""Application configuration loading."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    concurrency: int = 20
    retention_days: int = 35
    app_timezone: str = "Europe/Amsterdam"
    auth_enabled: bool = Field(default=True, validation_alias="AUTH_ENABLED")
    auth_username: str = Field(default="admin", validation_alias="AUTH_USERNAME")
    auth_password: str = Field(default="change-me", validation_alias="AUTH_PASSWORD")
    session_secret_key: str = "change-me-session-secret"
    session_max_age: int = 86400


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
