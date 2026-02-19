"""Test the monitoring module."""

from __future__ import annotations

from types import TracebackType

import pytest

from nedap_ons_uptime.db.models import ErrorType
from nedap_ons_uptime.monitoring import probe_target


class _DummyResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300


class _DummyClient:
    def __init__(self, status_code: int) -> None:
        self._status_code = status_code

    async def __aenter__(self) -> _DummyClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False

    async def get(self, _url: str) -> _DummyResponse:
        return _DummyResponse(self._status_code)


@pytest.mark.asyncio
async def test_probe_target_marks_http_error_as_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """probe_target should mark non-2xx responses as down."""
    monkeypatch.setattr(
        "nedap_ons_uptime.monitoring.httpx.AsyncClient",
        lambda **_kwargs: _DummyClient(500),
    )

    up, latency_ms, http_status, error_type, error_message = await probe_target(
        "https://example.com", timeout_s=5
    )

    assert up is False
    assert latency_ms is not None
    assert http_status == 500
    assert error_type == ErrorType.HTTP
    assert error_message == "HTTP 500"


@pytest.mark.asyncio
async def test_probe_target_marks_2xx_as_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """probe_target should mark 2xx responses as up."""
    monkeypatch.setattr(
        "nedap_ons_uptime.monitoring.httpx.AsyncClient",
        lambda **_kwargs: _DummyClient(204),
    )

    up, latency_ms, http_status, error_type, error_message = await probe_target(
        "https://example.com", timeout_s=5
    )

    assert up is True
    assert latency_ms is not None
    assert http_status == 204
    assert error_type == ErrorType.UNKNOWN
    assert error_message is None
