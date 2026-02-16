from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


class Database:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


_db: Database | None = None


def get_database() -> Database:
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def set_database(database: Database) -> None:
    global _db
    _db = database


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    db = get_database()
    async with db.session() as session:
        yield session
