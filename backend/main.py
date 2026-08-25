# backend/main.py
"""
FastAPI Application Entry Point for CodeLens AI.

Run with:
    uvicorn backend.main:app --reload
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import api_v1_router
from backend.core.config import settings
from backend.core.errors import register_exception_handlers
from backend.schemas.health import HealthResponse


def create_app() -> FastAPI:
    """Application factory for CodeLens AI FastAPI service."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI Code Understanding Engine — REST API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS Middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register Exception Handlers
    register_exception_handlers(app)

    # Health Endpoint
    @app.get(
        "/health",
        summary="Application health check",
        status_code=status.HTTP_200_OK,
        response_model=HealthResponse,
        tags=["Health"],
    )
    async def health_check() -> HealthResponse:
        """Process/application health check endpoint."""
        return HealthResponse(status="ok")

    # API v1 Router Registration
    app.include_router(
        api_v1_router,
        prefix=settings.API_V1_STR,
    )

    return app


# Expose module-level app object for uvicorn
app = create_app()

__all__ = ["app", "create_app"]
