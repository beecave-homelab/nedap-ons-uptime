"""Test the auth module."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from nedap_ons_uptime import auth
from nedap_ons_uptime.config import Settings


def _request_with_session(session_data: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "session": session_data or {},
    }
    return Request(scope)


def _settings(*, auth_enabled: bool = True) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost:5432/uptime",
        auth_enabled=auth_enabled,
        auth_username="admin",
        auth_password="secret",
    )


def test_verify_credentials_accepts_single_configured_user() -> None:
    settings = _settings()

    assert auth.verify_credentials("admin", "secret", settings=settings)
    assert not auth.verify_credentials("admin", "wrong", settings=settings)
    assert not auth.verify_credentials("wrong", "secret", settings=settings)


def test_require_authenticated_user_rejects_unauthorized_request() -> None:
    request = _request_with_session()

    with pytest.raises(HTTPException) as error:
        auth.require_authenticated_user(request, settings=_settings(auth_enabled=True))

    assert error.value.status_code == 401


def test_require_authenticated_user_allows_authenticated_session() -> None:
    request = _request_with_session({auth.AUTH_SESSION_KEY: True})

    auth.require_authenticated_user(request, settings=_settings(auth_enabled=True))


def test_require_authenticated_user_skips_when_auth_disabled() -> None:
    request = _request_with_session()

    auth.require_authenticated_user(request, settings=_settings(auth_enabled=False))


def test_mask_url_hides_host_and_path() -> None:
    assert auth.mask_url("https://example.com/health") == "https://e***/***"
