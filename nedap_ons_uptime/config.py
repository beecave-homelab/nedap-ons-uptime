from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    concurrency: int = 20
    retention_days: int = 35
    app_timezone: str = "Europe/Amsterdam"


@lru_cache
def get_settings() -> Settings:
    return Settings()
