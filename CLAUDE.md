# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ship Recognition Platform — a modular web application for downloading, classifying, and training AI models on ship images. Scrapes maritime websites (ShipSpotting, VesselFinder, MarineTraffic, FleetMon), classifies images using a Vision Transformer model, and supports fine-tuning and data augmentation. Documentation and UI are in German.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the backend (serves on http://localhost:3025)
python run.py

# Run tests
pytest

# API docs available at http://localhost:3025/docs (Swagger UI)

# Legacy Flask app (still works but being replaced)
python app.py
```

## Architecture

**Backend (FastAPI)** — `backend/` directory:
- `backend/main.py` — FastAPI app entry point, lifespan, CORS, static mounts
- `backend/config.py` — pydantic-settings configuration (reads from `.env`)
- `backend/database.py` — SQLAlchemy engine, session, Base class
- `backend/models/` — ORM models (Job, Item, Category, VPNLog, PredefinedURL, Classification, AugmentationLog)
- `backend/schemas/` — Pydantic request/response schemas
- `backend/routers/` — 8 FastAPI routers (vpn, scrape, ships, classify, training, augmentation, stats, settings)
- `backend/services/` — Business logic layer (vpn_service, scrape_service, ml_service)

**ML Engine** — `ml_engine.py` (preserved from v1, wrapped by `backend/services/ml_service.py`):
- Lazy-loaded ViT model from HuggingFace (`dima806/10_ship_types_image_detection`)
- classify_image(), start_training(), augment_images()

**Frontend** — `templates/index.html` (legacy SPA, to be replaced by React in `frontend/`):
- 6 tabs: Dashboard, Scraper, Ships, AI Classification, Training, Settings
- Dark theme, vanilla JS, polling for async operations

**Database** — SQLite via SQLAlchemy ORM (`schiffs-scraper.db`):
- 7 tables: jobs, items, categories, vpn_log, predefined_urls, classifications, augmentation_log
- Alembic configured for migrations (`alembic.ini`, `backend/migrations/`)

## Key Patterns

- **Service layer** separates business logic from route handlers
- **Background threads** for scraping, training, augmentation (status polled via API)
- **Lazy ML model loading** — loads on first classification request
- **VPN integration** — NordVPN CLI; configurable via `VPN_ENABLED` in `.env`
- **SQLAlchemy `metadata_`** — Item model uses `metadata_` (mapped to DB column `metadata`) to avoid SQLAlchemy reserved attribute name conflict
- **Static file mounts** — `/downloads/` and `/uploads/` served directly by FastAPI

## API Endpoints (26 routes)

All endpoints under `/api/`. Swagger docs at `/docs`.
- VPN: `GET/POST /api/vpn/{status,connect,disconnect,rotate}`
- Scraper: `POST /api/analyze`, `GET/POST /api/jobs`, `GET/POST/DELETE /api/jobs/{id}/*`
- Ships: `GET /api/ships`, `GET /api/ships/{id}`, `GET /api/ships/stats`
- Classification: `POST /api/classify`, `POST /api/classify/ship/{id}`, `GET /api/model/info`, `GET /api/classifications`
- Training: `GET/POST /api/training/{status,start,datasets}`
- Augmentation: `POST /api/augment`, `GET /api/augment/status`
- Stats: `GET /api/stats`
- Settings: `GET/POST/DELETE /api/urls`

## File Storage

- `downloads/` — Scraped images organized by job ID
- `uploads/` — User-uploaded images for classification
- `augmented/` — Synthetic augmented images
- `models/ship_classifier/` — ViT model weights and checkpoints
- `data/` — Training data directory (raw, processed, train, val, test, synthetic)
- `logs/` — Application logs

All data directories plus `.db` files are gitignored.

## Configuration

Settings in `backend/config.py` via pydantic-settings. Override with `.env` file (see `.env.example`).
Key settings: `PORT`, `DATABASE_URL`, `VPN_ENABLED`, `MODEL_DIR`, `DOWNLOAD_DIR`.
