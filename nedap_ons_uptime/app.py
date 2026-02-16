import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import get_settings
from .db.session import Database, set_database

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    from .monitoring import worker_loop

    await worker_loop(concurrency=concurrency)


async def retention_task_loop(retention_days: int) -> None:
    from .db.session import get_database as get_db
    from .db.models import Check
    from sqlalchemy import delete

    async def cleanup_old_checks() -> None:
        db = get_db()
        async with db.session() as session:
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            await session.execute(delete(Check).where(Check.checked_at < cutoff))

    while True:
        await cleanup_old_checks()
        await asyncio.sleep(6 * 3600)


def create_app() -> FastAPI:
    app = FastAPI(title="Nedap ONS Uptime", lifespan=lifespan)
    app.include_router(api_router, prefix="/api")

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app
