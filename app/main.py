"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.api.routes import router
from app.config import settings
from app.security.rate_limit import limiter

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("health_campaign_ai")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "AI assistant that turns natural-language questions (FR/EN) into "
            "safe, read-only SQL over the Health Campaign Manager database, "
            "with analytics, charts and trend interpretation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Serve frontend static files (built React app)
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/vite.svg", tags=["system"])
        def vite_svg():
            svg = frontend_dist / "vite.svg"
            if svg.exists():
                return FileResponse(svg, media_type="image/svg+xml")
            return JSONResponse(status_code=404, content={"detail": "not found"})

        @app.get("/", tags=["system"])
        def root():
            index = frontend_dist / "index.html"
            if index.exists():
                return FileResponse(index)
            return {
                "name": settings.app_name,
                "version": __version__,
                "docs": "/docs",
                "endpoints": ["/ai/query", "/ai/schema", "/health", "/auth/login"],
            }
    else:
        @app.get("/", tags=["system"])
        def root():
            return {
                "name": settings.app_name,
                "version": __version__,
                "docs": "/docs",
                "endpoints": ["/ai/query", "/ai/schema", "/health", "/auth/login"],
            }

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    @app.on_event("startup")
    def _startup():
        logger.info("Starting %s v%s", settings.app_name, __version__)
        # Warm the schema cache (non-fatal if DB is not ready yet).
        try:
            from app.database.schema_reader import discover_schema

            discover_schema(refresh=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Schema warm-up skipped: %s", exc)

    return app


app = create_app()
