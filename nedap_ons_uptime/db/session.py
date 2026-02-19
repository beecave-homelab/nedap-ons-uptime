"""Async database session and lifecycle helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nedap_ons_uptime.db.models import Base


class Database:
    """Database wrapper exposing engine and managed sessions."""

    def __init__(self, database_url: str) -> None:
        """Create an async SQLAlchemy engine and session factory."""
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init(self) -> None:
        """Create all configured tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Dispose the underlying SQLAlchemy engine."""
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a transactional async session with commit/rollback handling."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


_db: Database | None = None


def get_database() -> Database:
    """Return the globally configured database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def set_database(database: Database) -> None:
    """Set the global database instance."""
    global _db
    _db = database


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a managed async session."""
    db = get_database()
    async with db.session() as session:
        yield session
