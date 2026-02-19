"""Authentication and URL-masking helpers."""

from __future__ import annotations

import hmac
from urllib.parse import urlsplit, urlunsplit

from fastapi import Depends, HTTPException, Request, status

from nedap_ons_uptime.config import Settings, get_settings

AUTH_SESSION_KEY = "authenticated"


def is_auth_enabled(settings: Settings | None = None) -> bool:
    """Return whether authentication is enabled."""
    app_settings = settings or get_settings()
    return app_settings.auth_enabled


def is_authenticated(request: Request) -> bool:
    """Return whether the current request is authenticated."""
    if not is_auth_enabled():
        return True
    return bool(request.session.get(AUTH_SESSION_KEY, False))


def verify_credentials(
    username: str,
    password: str,
    settings: Settings | None = None,
) -> bool:
    """Validate username and password against configured credentials."""
    app_settings = settings or get_settings()
    return hmac.compare_digest(username, app_settings.auth_username) and hmac.compare_digest(
        password, app_settings.auth_password
    )


def set_authenticated(request: Request) -> None:
    """Mark request session as authenticated."""
    request.session[AUTH_SESSION_KEY] = True


def clear_authenticated(request: Request) -> None:
    """Clear authentication marker from request session."""
    request.session.pop(AUTH_SESSION_KEY, None)


def require_authenticated_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce authentication when auth is enabled."""
    if not settings.auth_enabled:
        return
    if not bool(request.session.get(AUTH_SESSION_KEY, False)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


def mask_url(url: str) -> str:
    """Mask URL host and path for unauthenticated responses."""
    parsed = urlsplit(url)
    host = parsed.netloc

    if not host:
        return "***"

    masked_host = host[0] + "***" if len(host) > 1 else "*"
    masked = parsed._replace(netloc=masked_host, path="/***", query="", fragment="")
    return urlunsplit(masked)
