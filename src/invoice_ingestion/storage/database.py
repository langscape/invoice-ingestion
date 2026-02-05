"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None


def init_db(database_url: str):
    """Initialise the async engine and session factory.

    Must be called once at application startup before any database access.
    """
    global _engine, _session_factory
    _engine = create_async_engine(database_url, pool_size=10, max_overflow=20)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """FastAPI-compatible dependency that yields an ``AsyncSession``."""
    async with _session_factory() as session:
        yield session


async def close_db():
    """Dispose of the engine connection pool.  Call at shutdown."""
    if _engine:
        await _engine.dispose()
