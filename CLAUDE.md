# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ship-Scraper is a Flask web application for downloading, classifying, and training AI models on ship images. It scrapes ship images from maritime websites (ShipSpotting, VesselFinder, MarineTraffic, FleetMon), classifies them using a Vision Transformer model, and supports fine-tuning and data augmentation. Documentation and UI are in German.

## Commands

```bash
# Setup (first time)
./setup.sh            # Linux/macOS
setup.bat             # Windows

# Activate virtual environment
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate.bat       # Windows

# Run the app (serves on http://localhost:3025)
python app.py

# Install dependencies
pip install -r requirements.txt
```

There are no automated tests. Manual testing is done via the web UI or API calls (e.g., `curl http://localhost:3025/api/stats`).

## Architecture

**Two-file backend:**
- `app.py` — Flask server with all API routes, database access, VPN management, and background job orchestration
- `ml_engine.py` — ML operations: model loading (lazy, on first use), classification, fine-tuning, and image augmentation

**Frontend:** `templates/index.html` — Single-page app (embedded CSS/JS) with 6 tabs: Dashboard, Scraper, Ships, AI Classification, Training, Settings

**Database:** SQLite (`schiffs-scraper.db`), schema defined in `schema.sql`. 8 tables: `jobs`, `items`, `categories`, `vpn_log`, `predefined_urls`, `classifications`, `augmentation_log`, `training_log`. Auto-created from schema on first run.

**ML Model:** HuggingFace `dima806/10_ship_types_image_detection` (ViT, ~350 MB). Cached locally in `models/ship_classifier/`. Downloaded automatically if missing. Classifies 10 ship types.

## Key Patterns

- **Background threads** for long-running operations (scraping, training, augmentation) — status polled via `/api/*/status` endpoints
- **Global state variables** in `app.py` track active job status (e.g., `current_job`, `training_status`)
- **Lazy model loading** — ViT model loads on first classification request, not at startup
- **VPN integration** — NordVPN CLI; app works without it but warns about IP blocking
- **No authentication** — designed for local/private use only
- **CORS enabled** globally via `flask-cors`

## API Structure

All endpoints under `/api/`:
- `/api/vpn/*` — VPN connect/disconnect/rotate/status
- `/api/analyze`, `/api/jobs/*` — Website analysis and scraping job management
- `/api/ships/*` — Downloaded image listing, filtering, stats
- `/api/classify/*`, `/api/model/info`, `/api/classifications` — Image classification
- `/api/training/*` — Fine-tuning control and status
- `/api/augment/*` — Data augmentation
- `/api/urls/*`, `/api/stats` — Settings and statistics

## File Storage

- `downloads/` — Scraped images organized by job ID
- `uploads/` — User-uploaded images for classification
- `augmented/` — Synthetic augmented images
- `models/ship_classifier/` — ViT model weights and fine-tuned checkpoints

All of these directories plus the `.db` file are gitignored.
