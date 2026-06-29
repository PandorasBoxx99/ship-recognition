# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ship Recognition Platform — modular web application for downloading, classifying, and training AI models on ship images. Scrapes maritime websites (ShipSpotting, VesselFinder, MarineTraffic, FleetMon), classifies using a ViT model, supports fine-tuning and augmentation. Documentation and UI are in German.

## Requirements

Python >= 3.11, Node.js >= 18 (for frontend).

## Commands

```bash
# One-click install (creates venv, installs everything including frontend build)
bash install.sh

# Or manual install
pip install -e ".[dev]"              # core + test deps
pip install -e ".[dev,browser]"      # + Playwright for Cloudflare-protected sites
playwright install chromium          # required after installing [browser] extra

# Run the backend (serves on http://localhost:3025)
python run.py

# Run tests
pytest                                         # all tests
pytest tests/test_api/test_stats.py            # single file
pytest tests/test_api/test_stats.py -k test_fn # single test

# Lint
ruff check backend/ tests/          # Python lint (E, F, I, N, W, UP rules)
cd frontend && npx eslint .          # Frontend lint

# Frontend dev server (with HMR, proxies /api /downloads /uploads to backend)
cd frontend && npm run dev

# Build frontend for production (outputs to ../frontend-dist/)
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
- `database.py` — SQLAlchemy 2.0+ engine, session, Base (SQLite with FK pragmas enabled)
- `models/` — ORM models split across two eras (see Database below)
- `schemas/` — Pydantic request/response schemas
- `routers/` — vpn, scrape, ship_entities, classify, training, augmentation, stats, settings, models, advanced, agent, datasets, detection, docs (the legacy v1 `ships` router was removed; ships are served only via v2 `ship_entities`)
- `services/` — vpn_service, scrape_service, ml_service (wraps ml_engine.py), browser_scraper (Playwright), ship_sync_service
- `migrations/` — Alembic (001_initial_v1, 002_normalize)

**ML Engine** — `ml_engine.py` (root level, preserved from v1, wrapped by `backend/services/ml_service.py`):
- Lazy-loaded ViT from HuggingFace (`dima806/10_ship_types_image_detection`)
- 10 ship types: Bulkers, Recreational, Sailboat, DDG, Container Ship, Tug, Aircraft Carrier, Cruise, Submarine, Car Carrier
- Training and augmentation status tracked as **module-level globals** (`_training_status`, `_augment_status`) — not persisted to DB

**Frontend** — `frontend/` (React 19 + TypeScript + Vite + Tailwind):
- TanStack Query for server state, Zustand for UI state, axios HTTP client
- German route names: `/Schiffe`, `/Erkennung`, `/Training`, `/Einstellungen`, `/daten/scraper`
- Builds to `frontend-dist/`, served by FastAPI as SPA (404 → index.html for client-side routing)

**Database** — SQLite (`schiffs-scraper.db`), Alembic migrations:
- **v1 tables** (jobs/items = scrape queue / ingestion layer; rest legacy): jobs, items, categories, predefined_urls, classifications, augmentation_log
- **v2 tables** (normalized): ships, ship_aliases, images, image_annotations, scrape_sources, scrape_jobs, ml_models, training_runs, inference_logs, synthetic_jobs

## Key Patterns

- **Service layer** separates business logic from route handlers
- **Background threads** for scraping, training, augmentation, batch classification
- **Lazy ML model loading** — loads on first classification request, not at startup
- **VPN integration** — NordVPN SOCKS5 proxy (no CLI). `VPN_API_KEY` (access token) + `VPN_PROXY_COUNTRY` (NL/SE/US) in `.env`. Scraper `requests` traffic and headless-browser traffic (via a local SOCKS5 bridge, `services/socks_bridge.py`) are tunneled. See `services/vpn_service.py`.
- **SQLAlchemy `metadata_`** — Item model uses `metadata_` (mapped to column `metadata`) to avoid reserved name
- **Single read-truth for ships** — v2 `/api/v2/ships/*` (normalized ships/images) is the source of truth for ship data and stats; v1 jobs/items are the scrape queue that syncs into v2. (The old `/api/ships/*` was removed.)
- **Dual scraper backends** — BeautifulSoup + requests (standard), Playwright (Cloudflare bypass)
- **Static file mounts** — `/downloads/` and `/uploads/` served by FastAPI
- **CPU-only PyTorch** — install.sh uses `--index-url https://download.pytorch.org/whl/cpu` (~200MB vs full CUDA)

## Testing

Tests use an **in-memory SQLite** database (StaticPool). Key fixtures in `tests/conftest.py`:
- `test_engine` — session-scoped in-memory DB
- `db_session` — per-test session with rollback
- `seeded_db` — pre-populated with sample Jobs, Items, Classifications, PredefinedURLs
- `client` — FastAPI TestClient with seeded DB (overrides `get_db` dependency)
- `mock_ml` — patches `ml_service.classify_image` to avoid loading the real model
- `mock_vpn` — patches the NordVPN REST API (`requests.get`) so VPN calls return a connected status

## CI

GitHub Actions (`.github/workflows/ci.yml`): runs `ruff check backend/ tests/` on push to main/develop and PRs to main.

## Configuration

`backend/config.py` via pydantic-settings. Override with `.env` (see `.env.example`).
Key: `PORT`, `DATABASE_URL`, `VPN_ENABLED`, `MODEL_DIR`, `DOWNLOAD_DIR`, `DEBUG`, `CORS_ORIGINS`.
