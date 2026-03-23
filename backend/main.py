"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import Base, engine, init_db
from backend.utils.logging import setup_logging

# Import all models so they're registered with Base
import backend.models  # noqa: F401

import structlog

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging(debug=settings.DEBUG)
    log.info("starting_app", port=settings.PORT, env=settings.APP_ENV)

    # Ensure directories exist
    settings.ensure_directories()

    # Create tables and seed default data
    init_db()
    _seed_default_urls()

    yield

    log.info("shutting_down")


app = FastAPI(
    title="Ship Recognition API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from backend.routers import advanced, agent, augmentation, classify, datasets, docs, models, scrape
from backend.routers import settings as settings_router
from backend.routers import ship_entities, ships, stats, training, vpn

app.include_router(vpn.router)
app.include_router(scrape.router)
app.include_router(ships.router)
app.include_router(classify.router)
app.include_router(training.router)
app.include_router(augmentation.router)
app.include_router(stats.router)
app.include_router(settings_router.router)
app.include_router(models.router)
app.include_router(ship_entities.router)
app.include_router(agent.router)
app.include_router(datasets.router)
app.include_router(advanced.router)
app.include_router(docs.router)


# --- Static file mounts ---
# Serve downloaded and uploaded images
if os.path.isdir(settings.DOWNLOAD_DIR):
    app.mount("/downloads", StaticFiles(directory=settings.DOWNLOAD_DIR), name="downloads")
if os.path.isdir(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# --- Frontend serving ---
# Serve React build if available, otherwise fall back to old template
_frontend_dist = Path(settings.DOWNLOAD_DIR).parent / "frontend-dist"
_old_template = Path(settings.DOWNLOAD_DIR).parent / "templates" / "index.html"


@app.get("/")
async def index():
    """Serve the frontend."""
    if (_frontend_dist / "index.html").exists():
        return FileResponse(str(_frontend_dist / "index.html"))
    elif _old_template.exists():
        return FileResponse(str(_old_template))
    return JSONResponse({"message": "Ship Recognition API", "docs": "/docs"})


# Serve frontend assets if React build exists
if _frontend_dist.exists() and (_frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")


# --- Error handlers ---
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # For non-API routes, serve the SPA index (client-side routing)
    if not request.url.path.startswith("/api/"):
        if (_frontend_dist / "index.html").exists():
            return FileResponse(str(_frontend_dist / "index.html"))
    return JSONResponse(status_code=404, content={"error": "Not found"})


def _seed_default_urls():
    """Insert default predefined URLs if they don't exist."""
    from backend.database import SessionLocal
    from backend.models.settings import PredefinedURL

    db = SessionLocal()
    try:
        defaults = [
            ("https://www.shipspotting.com/", "ShipSpotting"),
            ("https://www.vesselfinder.com/", "VesselFinder"),
            ("https://www.marinetraffic.com/", "MarineTraffic"),
            ("https://www.fleetmon.com/", "FleetMon"),
        ]
        for url, name in defaults:
            exists = db.query(PredefinedURL).filter(PredefinedURL.url == url).first()
            if not exists:
                db.add(PredefinedURL(url=url, name=name))
        db.commit()
    finally:
        db.close()
