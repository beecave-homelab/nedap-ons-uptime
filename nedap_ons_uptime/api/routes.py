from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import Check, Target
from ..db.session import get_session

router = APIRouter()


class TargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    enabled: bool = True
    interval_s: int = Field(default=60, ge=10, le=3600)
    timeout_s: int = Field(default=10, ge=1, le=30)
    verify_tls: bool = True


class TargetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    url: HttpUrl | None = None
    enabled: bool | None = None
    interval_s: int | None = Field(None, ge=10, le=3600)
    timeout_s: int | None = Field(None, ge=1, le=30)
    verify_tls: bool | None = None


class TargetResponse(BaseModel):
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
    target_id: UUID
    name: str
    uptime_percentage: float
    total_checks: int
    up_checks: int
    down_checks: int


class ConfigResponse(BaseModel):
    app_timezone: str


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    settings = get_settings()
    return ConfigResponse(app_timezone=settings.app_timezone)


@router.get("/targets", response_model=list[TargetResponse])
async def list_targets(session: AsyncSession = Depends(get_session)) -> list[Target]:
    result = await session.execute(select(Target))
    return list(result.scalars().all())


@router.post("/targets", response_model=TargetResponse, status_code=201)
async def create_target(
    target_data: TargetCreate, session: AsyncSession = Depends(get_session)
) -> Target:
    target = Target(**target_data.model_dump(mode="json"))
    session.add(target)
    await session.flush()
    await session.refresh(target)
    return target


@router.get("/targets/{target_id}", response_model=TargetResponse)
async def get_target(target_id: str, session: AsyncSession = Depends(get_session)) -> Target:
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.patch("/targets/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: str, target_update: TargetUpdate, session: AsyncSession = Depends(get_session)
) -> Target:
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
async def delete_target(target_id: str, session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    await session.delete(target)


@router.get("/status", response_model=list[StatusResponse])
async def get_status(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
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
    for target in targets:
        check = checks.get(target.id)
        if check:
            status.append(
                {
                    "target_id": str(target.id),
                    "name": target.name,
                    "url": target.url,
                    "up": check.up,
                    "last_checked": check.checked_at,
                    "latency_ms": check.latency_ms,
                    "http_status": check.http_status,
                    "error_type": check.error_type,
                    "error_message": check.error_message,
                }
            )
        else:
            status.append(
                {
                    "target_id": str(target.id),
                    "name": target.name,
                    "url": target.url,
                    "up": None,
                    "last_checked": None,
                    "latency_ms": None,
                    "http_status": None,
                    "error_type": None,
                    "error_message": None,
                }
            )

    return status


@router.get("/targets/{target_id}/history", response_model=list[CheckResponse])
async def get_target_history(
    target_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
) -> list[Check]:
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


@router.get("/targets/{target_id}/uptime", response_model=UptimeResponse)
async def get_target_uptime(
    target_id: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
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
