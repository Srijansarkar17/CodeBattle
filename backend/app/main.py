"""
CodeBattle Backend - Main FastAPI Application Entry Point

This is the root of the FastAPI application. It:
- Creates the app instance
- Registers all routers
- Sets up CORS middleware
- Initializes database and Redis on startup
- Handles graceful shutdown
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import redis_manager
from app.api.v1 import router as api_v1_router
from app.websockets.manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    - On startup: connects to DB, Redis
    - On shutdown: cleanly closes all connections
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    print("🚀 Starting CodeBattle backend...")
    await init_db()                     # Create tables if they don't exist
    await redis_manager.connect()       # Open Redis connection pool
    print("✅ CodeBattle backend is ready!")

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("🛑 Shutting down CodeBattle backend...")
    await redis_manager.disconnect()    # Close Redis connections
    print("✅ Shutdown complete.")


def create_application() -> FastAPI:
    """Factory function that creates and configures the FastAPI app."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Real-time 1v1 coding battle platform API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # CORS: Allow the Next.js frontend to communicate with the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_application()
