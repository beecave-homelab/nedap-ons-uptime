"""Test the api schemas."""

from datetime import UTC, datetime
from uuid import uuid4

from nedap_ons_uptime.api.routes import StatusResponse


def test_status_response_allows_nulls_for_unchecked_target() -> None:
    """Status response should accept null values before first check."""
    target_id = uuid4()
    model = StatusResponse(
        target_id=target_id,
        name="Example",
        url="https://example.com",
        up=None,
        last_checked=None,
        latency_ms=None,
        http_status=None,
        error_type=None,
        error_message=None,
    )

    assert model.up is None
    assert model.last_checked is None


def test_status_response_allows_checked_target_values() -> None:
    """Status response should accept populated values after checks."""
    target_id = uuid4()
    now = datetime.now(UTC)
    model = StatusResponse(
        target_id=target_id,
        name="Example",
        url="https://example.com",
        up=True,
        last_checked=now,
        latency_ms=35,
        http_status=200,
        error_type="unknown",
        error_message=None,
    )

    assert model.up is True
    assert model.last_checked == now
