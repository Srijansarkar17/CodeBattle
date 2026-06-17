"""
Health Check Endpoints.

Used by Docker health checks and monitoring tools to verify the API is alive.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.redis import redis_manager

router = APIRouter()


@router.get("/", summary="Basic health check")
async def health_check():
    """
    Returns 200 OK if the API process is running.
    Does NOT check DB or Redis — use /full for that.
    """
    return {"status": "ok", "service": "CodeBattle API"}


@router.get("/full", summary="Full system health check")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """
    Checks:
    - API is up
    - PostgreSQL is reachable and responding
    - Redis is reachable and responding

    Returns a status object with component-level health.
    """
    results = {
        "api": "ok",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as e:
        results["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        await redis_manager.client.ping()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = f"error: {str(e)}"

    # Overall status: ok only if all components are healthy
    overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"

    return {"status": overall, "components": results}
