"""Test the configuration module."""

from nedap_ons_uptime.config import get_settings


def test_app_timezone_defaults_to_amsterdam(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/uptime")
    monkeypatch.delenv("APP_TIMEZONE", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_timezone == "Europe/Amsterdam"


def test_app_timezone_can_be_overridden_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/uptime")
    monkeypatch.setenv("APP_TIMEZONE", "UTC")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_timezone == "UTC"


def test_auth_enabled_defaults_to_true(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/uptime")
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.auth_enabled is True


def test_auth_enabled_can_be_disabled_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/uptime")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.auth_enabled is False
