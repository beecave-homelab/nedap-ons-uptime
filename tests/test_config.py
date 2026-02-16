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
