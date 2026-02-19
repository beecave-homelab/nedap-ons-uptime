"""FastAPI application factory and background lifecycle tasks."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from nedap_ons_uptime.api import router as api_router
from nedap_ons_uptime.config import get_settings
from nedap_ons_uptime.db.session import Database, set_database

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and tear down shared app resources."""
    settings = get_settings()
    db = Database(settings.database_url)
    set_database(db)

    await db.init()

    worker = asyncio.create_task(worker_task(settings.concurrency))
    retention_task = asyncio.create_task(retention_task_loop(settings.retention_days))

    yield

    worker.cancel()
    retention_task.cancel()
    with suppress(asyncio.CancelledError):
        await worker
    with suppress(asyncio.CancelledError):
        await retention_task
    await db.close()


async def worker_task(concurrency: int) -> None:
    """Run the continuous target-check worker loop."""
    from .monitoring import worker_loop

    await worker_loop(concurrency=concurrency)


async def retention_task_loop(retention_days: int) -> None:
    """Periodically delete old checks according to retention policy."""
    from sqlalchemy import delete

    from .db.models import Check
    from .db.session import get_database as get_db

    async def cleanup_old_checks() -> None:
        db = get_db()
        async with db.session() as session:
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            await session.execute(delete(Check).where(Check.checked_at < cutoff))

    while True:
        await cleanup_old_checks()
        await asyncio.sleep(6 * 3600)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Nedap ONS Uptime", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=False,
    )

    app.include_router(api_router, prefix="/api")

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Return a simple health status."""
        return {"status": "ok"}

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the single-page frontend."""
        return FileResponse(STATIC_DIR / "index.html")

    return app
