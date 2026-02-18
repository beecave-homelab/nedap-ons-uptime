from __future__ import annotations

import asyncio
import logging
import ssl
import time
import urllib.parse
from datetime import datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nedap_ons_uptime.db.models import Check, ErrorType, Target
from nedap_ons_uptime.db.session import get_database

logger = logging.getLogger(__name__)


async def probe_target(
    url: str, timeout_s: int, verify_tls: bool = True
) -> tuple[bool, int | None, int | None, str, str | None]:
    start = time.monotonic()
    error_type = ErrorType.UNKNOWN
    error_message = None
    http_status = None

    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname

        if not host:
            raise ValueError("Invalid URL: no hostname")

        http_status = None
        async with httpx.AsyncClient(
            timeout=timeout_s, verify=verify_tls, follow_redirects=True
        ) as client:
            response = await client.get(url)
            http_status = response.status_code

        latency_ms = int((time.monotonic() - start) * 1000)
        is_up = response.is_success
        error_type = ErrorType.UNKNOWN if is_up else ErrorType.HTTP
        error_message = None if is_up else f"HTTP {http_status}"
        return is_up, latency_ms, http_status, error_type, error_message

    except ssl.SSLCertVerificationError as e:
        error_type = ErrorType.TLS
        error_message = str(e)[:500]
    except ssl.SSLError as e:
        error_type = ErrorType.TLS
        error_message = str(e)[:500]
    except httpx.ConnectTimeout as e:
        error_type = ErrorType.TIMEOUT
        error_message = str(e)[:500]
    except httpx.TimeoutException as e:
        error_type = ErrorType.TIMEOUT
        error_message = str(e)[:500]
    except httpx.ConnectError as e:
        error_type = ErrorType.CONNECT
        error_message = str(e)[:500]
    except httpx.HTTPError as e:
        error_type = ErrorType.HTTP
        error_message = str(e)[:500]
    except Exception as e:
        error_message = str(e)[:500]

    latency_ms = int((time.monotonic() - start) * 1000) if start else None
    return False, latency_ms, http_status, error_type, error_message


async def check_target(session: AsyncSession, target: Target) -> None:
    up, latency_ms, http_status, error_type, error_message = await probe_target(
        target.url, target.timeout_s, verify_tls=target.verify_tls
    )

    check = Check(
        target_id=target.id,
        checked_at=datetime.utcnow(),
        up=up,
        latency_ms=latency_ms,
        http_status=http_status,
        error_type=error_type,
        error_message=error_message,
    )
    session.add(check)


async def load_targets(session: AsyncSession) -> list[Target]:
    result = await session.execute(select(Target).where(Target.enabled.is_(True)))
    return list(result.scalars().all())


async def load_due_targets(session: AsyncSession) -> list[Target]:
    now = datetime.utcnow()
    subq = (
        select(Check.target_id, func.max(Check.checked_at).label("last_checked"))
        .group_by(Check.target_id)
        .subquery()
    )
    result = await session.execute(
        select(Target, subq.c.last_checked)
        .outerjoin(subq, Target.id == subq.c.target_id)
        .where(Target.enabled.is_(True))
    )
    rows = result.all()

    due_targets: list[Target] = []
    for target, last_checked in rows:
        if last_checked is None:
            due_targets.append(target)
            continue

        elapsed_s = (now - last_checked).total_seconds()
        if elapsed_s >= target.interval_s:
            due_targets.append(target)

    return due_targets


async def run_checks(concurrency: int = 20) -> None:
    db = get_database()
    async with db.session() as session:
        targets = await load_due_targets(session)

    if not targets:
        return

    semaphore = asyncio.Semaphore(concurrency)

    async def check_with_semaphore(target: Target) -> None:
        async with semaphore:
            db = get_database()
            async with db.session() as session:
                try:
                    await check_target(session, target)
                except Exception:
                    logger.exception("Failed to check target", extra={"target_id": str(target.id)})

    await asyncio.gather(*[check_with_semaphore(t) for t in targets])


async def worker_loop(interval_s: int = 60, concurrency: int = 20) -> None:
    while True:
        await run_checks(concurrency)
        await asyncio.sleep(interval_s)
