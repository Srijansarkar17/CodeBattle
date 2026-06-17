"""
Database Connection & Session Management.

Uses SQLAlchemy's async engine with asyncpg driver.
Provides:
- Async engine and session factory
- Base declarative class for all ORM models
- init_db() to create tables on startup
- get_db() dependency for FastAPI route injection
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# echo=True logs all SQL statements (useful for development)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,          # Verify connections before use
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,      # Keep objects accessible after commit
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Declarative base that all ORM models inherit from.
    SQLAlchemy uses this to track all table definitions.
    """
    pass


async def init_db() -> None:
    """
    Creates all tables defined in ORM models.
    Called once on application startup.
    In production, use Alembic migrations instead.
    """
    # Import all models so SQLAlchemy knows about them before creating tables
    from app.models import user, match, contest, submission, rating, problem  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database tables created/verified.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.
    Automatically closes the session when the request finishes.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
