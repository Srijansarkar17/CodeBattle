"""
API v1 Router — aggregates all sub-routers.

Every new feature module gets its own router and is included here.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.health import router as health_router
from app.api.v1.matchmaking import router as matchmaking_router
from app.websockets.endpoint import router as ws_router

router = APIRouter()

# ── Mount sub-routers ─────────────────────────────────────────────────────────
router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(matchmaking_router, prefix="/matchmaking", tags=["Matchmaking"])

# WebSocket endpoint (no prefix, handled at /api/v1/ws/...)
router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
