"""FastAPI application factory."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from flat_research.api.rate_limit import limiter, rate_limit_handler
from flat_research.api.routes_auth import router as auth_router
from flat_research.api.routes_criteria import router as criteria_router
from flat_research.api.routes_listings import router as listings_router
from flat_research.api.routes_telegram import router as telegram_router
from flat_research.api.routes_user import router as user_router

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="FlatBot", version="0.2.0")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth_router)
    app.include_router(criteria_router)
    app.include_router(listings_router)
    app.include_router(user_router)
    app.include_router(telegram_router)

    # Serve React build in production (if static/ dir exists)
    if STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve React SPA — all non-API routes return index.html."""
            file_path = STATIC_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")

    return app
