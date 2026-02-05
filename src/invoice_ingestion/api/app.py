"""FastAPI application factory."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import Settings
from ..storage.database import init_db, close_db
from .routes import extraction, review, health, webhook


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        init_db(settings.database_url.get_secret_value())
        yield
        # Shutdown
        await close_db()

    app = FastAPI(
        title="Invoice Ingestion API",
        description="Energy invoice extraction pipeline API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store settings in app state
    app.state.settings = settings

    # Register routes
    app.include_router(health.router, tags=["health"])
    app.include_router(extraction.router, prefix="/extractions", tags=["extractions"])
    app.include_router(review.router, prefix="/review", tags=["review"])
    app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])

    return app
