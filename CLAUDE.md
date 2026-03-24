# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ship Recognition Platform — modular web application for downloading, classifying, and training AI models on ship images. Scrapes maritime websites (ShipSpotting, VesselFinder, MarineTraffic, FleetMon), classifies using a ViT model, supports fine-tuning and augmentation. Documentation and UI are in German.

## Commands

```bash
# One-click install (creates venv, installs everything)
bash install.sh

# Or manual install
pip install -e ".[dev]"

# Run the backend (serves on http://localhost:3025)
python run.py

# Run tests
pytest

# Frontend dev server (with HMR, proxies to backend)
cd frontend && npm run dev

# Build frontend for production
cd frontend && npm run build

# Run Alembic migrations
python -m alembic upgrade head

# Docker
docker compose up --build

# API docs: http://localhost:3025/docs
```

## Architecture

**Backend (FastAPI)** — `backend/`:
- `main.py` — App entry, lifespan, CORS, static mounts, router registration
- `config.py` — pydantic-settings (reads `.env`)
- `database.py` — SQLAlchemy engine, session, Base
- `models/` — 14 ORM models: 7 legacy (Job, Item, Category, VPNLog, PredefinedURL, Classification, AugmentationLog) + 7 normalized (Ship, ShipAlias, Image, ImageAnnotation, ScrapeSource, ScrapeJob, MLModel, TrainingRun, InferenceLog, SyntheticJob)
- `schemas/` — Pydantic request/response schemas (9 modules)
- `routers/` — 10 routers: vpn, scrape, ships, classify, training, augmentation, stats, settings, models, ship_entities
- `services/` — vpn_service, scrape_service, ml_service (wraps ml_engine.py)
- `migrations/` — Alembic (001_initial_v1, 002_normalize)

**ML Engine** — `ml_engine.py` (preserved from v1, wrapped by `backend/services/ml_service.py`):
- Lazy-loaded ViT from HuggingFace (`dima806/10_ship_types_image_detection`)
- classify_image(), start_training(), augment_images()

**Frontend** — `frontend/` (React + TypeScript + Vite + Tailwind):
- 6 pages: Dashboard, Scraper, Ships, Classify, Training, Settings
- TanStack Query for server state, Zustand for UI state
- Builds to `frontend-dist/`, served by FastAPI

**Database** — SQLite, 17 tables, Alembic migrations:
- Legacy v1 tables: jobs, items, categories, vpn_log, predefined_urls, classifications, augmentation_log
- Normalized v2 tables: ships, ship_aliases, images, image_annotations, scrape_sources, scrape_jobs, ml_models, training_runs, inference_logs, synthetic_jobs

## Key Patterns

- **Service layer** separates business logic from route handlers
- **Background threads** for scraping, training, augmentation, batch classification
- **Lazy ML model loading** — loads on first classification request
- **VPN integration** — NordVPN CLI; configurable via `VPN_ENABLED` in `.env`
- **SQLAlchemy `metadata_`** — Item model uses `metadata_` (mapped to column `metadata`) to avoid reserved name
- **Dual API** — v1 endpoints for backward compat, v2 (`/api/v2/ships`) for normalized entities
- **Static file mounts** — `/downloads/` and `/uploads/` served by FastAPI

## API Endpoints (35+ routes)

Swagger docs at `/docs`. Key groups:
- VPN: `/api/vpn/{status,connect,disconnect,rotate}`
- Scraper: `/api/analyze`, `/api/jobs/*`
- Ships v1: `/api/ships/*` (legacy)
- Ships v2: `/api/v2/ships/*` (normalized CRUD)
- Classification: `/api/classify`, `/api/classify/batch`, `/api/model/info`, `/api/classifications`
- Models: `/api/models` (registry, activate)
- Training: `/api/training/*`
- Augmentation: `/api/augment/*`
- Stats: `/api/stats`
- Settings: `/api/urls`

## Configuration

`backend/config.py` via pydantic-settings. Override with `.env` (see `.env.example`).
Key: `PORT`, `DATABASE_URL`, `VPN_ENABLED`, `MODEL_DIR`, `DOWNLOAD_DIR`, `DEBUG`.
