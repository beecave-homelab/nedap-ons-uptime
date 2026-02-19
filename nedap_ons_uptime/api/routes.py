"""API routes and request/response schemas for uptime resources."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nedap_ons_uptime.auth import (
    clear_authenticated,
    is_authenticated,
    mask_url,
    require_authenticated_user,
    set_authenticated,
    verify_credentials,
)
from nedap_ons_uptime.config import get_settings
from nedap_ons_uptime.db.models import Check, Target
from nedap_ons_uptime.db.session import get_session

router = APIRouter()


class TargetCreate(BaseModel):
    """Payload for creating a monitored target."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    enabled: bool = True
    interval_s: int = Field(default=60, ge=10, le=3600)
    timeout_s: int = Field(default=10, ge=1, le=30)
    verify_tls: bool = True


class TargetUpdate(BaseModel):
    """Payload for partially updating a monitored target."""

    name: str | None = Field(None, min_length=1, max_length=255)
    url: HttpUrl | None = None
    enabled: bool | None = None
    interval_s: int | None = Field(None, ge=10, le=3600)
    timeout_s: int | None = Field(None, ge=1, le=30)
    verify_tls: bool | None = None


class TargetResponse(BaseModel):
    """Serialized target resource."""

    id: UUID
    name: str
    url: str
    enabled: bool
    interval_s: int
    timeout_s: int
    verify_tls: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckResponse(BaseModel):
    """Serialized check result."""

    id: UUID
    target_id: UUID
    checked_at: datetime
    up: bool
    latency_ms: int | None
    http_status: int | None
    error_type: str
    error_message: str | None

    model_config = {"from_attributes": True}


class StatusResponse(BaseModel):
    """Latest check status for a target."""

    target_id: UUID
    name: str
    url: str
    up: bool | None
    last_checked: datetime | None
    latency_ms: int | None
    http_status: int | None
    error_type: str | None
    error_message: str | None


class UptimeResponse(BaseModel):
    """Aggregated uptime statistics for a target."""

    target_id: UUID
    name: str
    uptime_percentage: float
    total_checks: int
    up_checks: int
    down_checks: int


class ConfigResponse(BaseModel):
    """Public runtime configuration exposed to clients."""

    app_timezone: str


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str
    password: str


class AuthStateResponse(BaseModel):
    """Authentication state response payload."""

    authenticated: bool
    auth_enabled: bool


def _serialize_target(target: Target, expose_url: bool) -> TargetResponse:
    return TargetResponse(
        id=target.id,
        name=target.name,
        url=target.url if expose_url else mask_url(target.url),
        enabled=target.enabled,
        interval_s=target.interval_s,
        timeout_s=target.timeout_s,
        verify_tls=target.verify_tls,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


def _serialize_status_row(target: Target, check: Check | None, expose_url: bool) -> dict[str, Any]:
    if check:
        return {
            "target_id": str(target.id),
            "name": target.name,
            "url": target.url if expose_url else mask_url(target.url),
            "up": check.up,
            "last_checked": check.checked_at,
            "latency_ms": check.latency_ms,
            "http_status": check.http_status,
            "error_type": check.error_type,
            "error_message": check.error_message,
        }

    return {
        "target_id": str(target.id),
        "name": target.name,
        "url": target.url if expose_url else mask_url(target.url),
        "up": None,
        "last_checked": None,
        "latency_ms": None,
        "http_status": None,
        "error_type": None,
        "error_message": None,
    }


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return frontend configuration values."""
    settings = get_settings()
    return ConfigResponse(app_timezone=settings.app_timezone)


@router.get("/auth/me", response_model=AuthStateResponse)
async def auth_me(request: Request) -> AuthStateResponse:
    """Return authentication state for the current request."""
    settings = get_settings()
    return AuthStateResponse(
        authenticated=is_authenticated(request),
        auth_enabled=settings.auth_enabled,
    )


@router.post("/auth/login", response_model=AuthStateResponse)
async def auth_login(payload: LoginRequest, request: Request) -> AuthStateResponse:
    """Authenticate a user session."""
    settings = get_settings()

    if not settings.auth_enabled:
        return AuthStateResponse(authenticated=True, auth_enabled=False)

    if not verify_credentials(payload.username, payload.password, settings=settings):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    set_authenticated(request)
    return AuthStateResponse(authenticated=True, auth_enabled=True)


@router.post("/auth/logout", response_model=AuthStateResponse)
async def auth_logout(request: Request) -> AuthStateResponse:
    """Log out the current user session."""
    settings = get_settings()
    clear_authenticated(request)
    return AuthStateResponse(authenticated=False, auth_enabled=settings.auth_enabled)


@router.get("/targets", response_model=list[TargetResponse])
async def list_targets(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[TargetResponse]:
    """List all configured targets."""
    result = await session.execute(select(Target))
    expose_url = is_authenticated(request)
    return [_serialize_target(target, expose_url=expose_url) for target in result.scalars().all()]


@router.post("/targets", response_model=TargetResponse, status_code=201)
async def create_target(
    target_data: TargetCreate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_authenticated_user),
) -> Target:
    """Create a new monitored target."""
    target = Target(**target_data.model_dump(mode="json"))
    session.add(target)
    await session.flush()
    await session.refresh(target)
    return target


@router.get("/targets/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TargetResponse:
    """Fetch a target by ID."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return _serialize_target(target, expose_url=is_authenticated(request))


@router.patch("/targets/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: str,
    target_update: TargetUpdate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_authenticated_user),
) -> Target:
    """Update an existing target by ID."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    update_data = target_update.model_dump(exclude_unset=True, mode="json")
    for field, value in update_data.items():
        setattr(target, field, value)

    await session.flush()
    await session.refresh(target)
    return target


@router.delete("/targets/{target_id}", status_code=204)
async def delete_target(
    target_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_authenticated_user),
) -> None:
    """Delete a target by ID."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    await session.delete(target)


@router.get("/status", response_model=list[StatusResponse])
async def get_status(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Return latest status information for all targets."""
    subq = (
        select(Check.target_id, func.max(Check.checked_at).label("last_checked"))
        .group_by(Check.target_id)
        .subquery()
    )

    latest_checks = select(Check).join(
        subq, (Check.target_id == subq.c.target_id) & (Check.checked_at == subq.c.last_checked)
    )

    result = await session.execute(latest_checks)
    checks = {c.target_id: c for c in result.scalars().all()}

    result = await session.execute(select(Target))
    targets = result.scalars().all()

    status = []
    expose_url = is_authenticated(request)
    for target in targets:
        check = checks.get(target.id)
        status.append(_serialize_status_row(target, check, expose_url=expose_url))

    return status


@router.get("/targets/{target_id}/history", response_model=list[CheckResponse])
async def get_target_history(
    target_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
) -> list[Check]:
    """Return historical checks for a specific target."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(Check)
        .where(Check.target_id == target_id)
        .where(Check.checked_at >= cutoff)
        .order_by(Check.checked_at.desc())
    )
    return list(result.scalars().all())


@router.get("/history", response_model=list[CheckResponse])
async def get_all_history(
    hours: int = Query(default=24, ge=1, le=720),
    target_id: str | None = Query(default=None),
    up: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[Check]:
    """Get check history across all targets with optional filters."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = select(Check).where(Check.checked_at >= cutoff)

    if target_id:
        query = query.where(Check.target_id == target_id)
    if up is not None:
        query = query.where(Check.up == up)

    query = query.order_by(Check.checked_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/targets/{target_id}/uptime", response_model=UptimeResponse)
async def get_target_uptime(
    target_id: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return aggregated uptime stats for a target."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(func.count(Check.id), func.sum(Check.up.cast("integer")))
        .where(Check.target_id == target_id)
        .where(Check.checked_at >= cutoff)
    )
    total, up_sum = result.first()

    total_checks = int(total) if total else 0
    up_checks = int(up_sum) if up_sum else 0
    down_checks = total_checks - up_checks
    uptime_percentage = (up_checks / total_checks * 100) if total_checks > 0 else 0

    return {
        "target_id": str(target.id),
        "name": target.name,
        "uptime_percentage": uptime_percentage,
        "total_checks": total_checks,
        "up_checks": up_checks,
        "down_checks": down_checks,
    }


class DailyUptimeResponse(BaseModel):
    """Daily uptime summary entry."""

    date: str
    uptime_percentage: float
    total_checks: int
    up_checks: int
    down_checks: int


@router.get("/targets/{target_id}/daily", response_model=list[DailyUptimeResponse])
async def get_target_daily_uptime(
    target_id: str,
    days: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Return daily uptime breakdown for the last N days."""
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all checks in the date range
    result = await session.execute(
        select(Check)
        .where(Check.target_id == target_id)
        .where(Check.checked_at >= cutoff)
        .order_by(Check.checked_at.asc())
    )
    checks = result.scalars().all()

    # Group by day
    daily_data: dict[str, dict] = {}
    for check in checks:
        day_key = check.checked_at.strftime("%Y-%m-%d")
        if day_key not in daily_data:
            daily_data[day_key] = {"total": 0, "up": 0}
        daily_data[day_key]["total"] += 1
        if check.up:
            daily_data[day_key]["up"] += 1

    # Build response with all days (fill in missing days with 100% uptime)
    response = []
    for i in range(days - 1, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_key = day.strftime("%Y-%m-%d")
        day_data = daily_data.get(day_key, {"total": 0, "up": 0})

        total = day_data["total"]
        up = day_data["up"]
        uptime_pct = (up / total * 100) if total > 0 else 100.0

        response.append(
            {
                "date": day_key,
                "uptime_percentage": round(uptime_pct, 2),
                "total_checks": total,
                "up_checks": up,
                "down_checks": total - up,
            }
        )

    return response
