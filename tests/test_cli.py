"""Test the cli module."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nedap_ons_uptime import cli


class _DummyServer:
    def __init__(self, _config: object) -> None:
        pass

    async def serve(self) -> None:
        return None


def test_serve_preserves_environment_for_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve should pass existing env vars to migration subprocess."""
    captured: dict[str, object] = {}

    monkeypatch.setenv("TEST_SENTINEL", "present")
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            app_host="127.0.0.1",
            app_port=8000,
        ),
    )
    monkeypatch.setattr(cli, "create_app", lambda: object())
    monkeypatch.setattr(cli, "Config", lambda **kwargs: kwargs)
    monkeypatch.setattr(cli, "Server", _DummyServer)

    def _fake_run(cmd: list[str], env: dict[str, str] | None = None) -> SimpleNamespace:
        captured["cmd"] = cmd
        captured["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", _fake_run)

    cli.serve()

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["TEST_SENTINEL"] == "present"
    assert env["DATABASE_URL"] == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_migrate_preserves_environment_for_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Migrate should pass existing env vars to migration subprocess."""
    captured: dict[str, object] = {}

    monkeypatch.setenv("TEST_SENTINEL", "present")
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://u:p@localhost:5432/db"),
    )

    def _fake_run(cmd: list[str], env: dict[str, str] | None = None) -> SimpleNamespace:
        captured["cmd"] = cmd
        captured["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", _fake_run)

    cli.migrate()

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["TEST_SENTINEL"] == "present"
    assert env["DATABASE_URL"] == "postgresql+asyncpg://u:p@localhost:5432/db"
