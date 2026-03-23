"""Documentation endpoint — serves plan, changelog, and project docs."""

import os
import subprocess
from pathlib import Path

from fastapi import APIRouter

from backend.config import BASE_DIR

router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.get("/changelog")
def get_changelog():
    """Get git-based changelog."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s|%b", "--reverse"],
            capture_output=True, text=True, timeout=5,
            cwd=str(BASE_DIR),
        )
        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) >= 3:
                entries.append({
                    "hash": parts[0][:8],
                    "date": parts[1][:10],
                    "message": parts[2],
                    "details": parts[3].strip() if len(parts) > 3 else "",
                })
        return {"changelog": entries}
    except Exception:
        return {"changelog": []}


@router.get("/plan")
def get_plan():
    """Get the implementation plan / requirements document."""
    return {
        "title": "Ship Recognition Platform — Implementierungsplan",
        "phases": [
            {
                "id": 0,
                "name": "Foundation",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "Git-Repository initialisiert (master + develop Branch)",
                    "Projektstruktur: backend/, frontend/, tests/, docs/",
                    "Konfigurationssystem (pydantic-settings, .env)",
                    "pyproject.toml mit allen Abhängigkeiten",
                    "run.py als Einstiegspunkt",
                ],
            },
            {
                "id": 1,
                "name": "Backend-Migration (Flask → FastAPI)",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "SQLAlchemy ORM-Modelle für alle 7 Bestandstabellen",
                    "Pydantic Request/Response-Schemas (9 Module)",
                    "Service Layer: VPN, Scraper, ML (wraps ml_engine.py)",
                    "8 FastAPI-Router mit 26 Endpoints",
                    "Strukturiertes Logging (structlog)",
                    "Alembic-Migrationssystem",
                    "Statische Dateien: /downloads/, /uploads/",
                    "Altes Frontend (index.html) weiterhin via FastAPI serviert",
                ],
            },
            {
                "id": 2,
                "name": "Tests & Cleanup",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "41 API-Integrationstests (pytest + TestClient)",
                    "15 Service-Unit-Tests (Mock VPN, Scraper, ML)",
                    "56 Tests gesamt, alle bestanden",
                    "Datenbank-Migrationsskript (scripts/migrate_v1.py)",
                    "Legacy-Code archiviert (legacy/)",
                ],
            },
            {
                "id": 3,
                "name": "Frontend-Rewrite (React + TypeScript)",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "Vite + React + TypeScript + Tailwind CSS",
                    "Typisierter API-Client (Axios)",
                    "TanStack Query Hooks für alle Datenzugriffe",
                    "Zustand Store für UI-State",
                    "Dark Theme passend zum Original",
                    "6 Tabs: Dashboard, Scraper, Schiffe, KI-Erkennung, Training, Einstellungen",
                    "URL-basiertes Routing (/Dashboard, /Schiffe, etc.)",
                    "Build → frontend-dist/, serviert via FastAPI",
                ],
            },
            {
                "id": 4,
                "name": "Datenbank-Normalisierung + Neue Features",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "10 neue normalisierte Tabellen (ships, images, ml_models, etc.)",
                    "Alembic-Migration mit Datenmigration aus Bestand",
                    "Modell-Registry: Registrieren, Aktivieren, Versionieren",
                    "Batch-Klassifikation aller unklassifizierten Bilder",
                    "Ship Entity CRUD (/api/v2/ships)",
                    "17 Tabellen gesamt (7 Legacy + 10 normalisiert)",
                ],
            },
            {
                "id": 5,
                "name": "Infrastruktur & DevOps",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "Multi-Stage Dockerfile (Node Build + Python Runtime)",
                    "docker-compose.yml mit Volume-Mounts",
                    "GitHub Actions CI (Lint, Test, Frontend Build)",
                    "Setup-Scripts aktualisiert (setup.sh / setup.bat)",
                    "README.md, docs/API.md, docs/DATABASE.md",
                ],
            },
            {
                "id": 6,
                "name": "Erweiterte Features",
                "status": "done",
                "date": "2026-03-22",
                "items": [
                    "Agent API Layer: Context, Capabilities, Action Registry, Self-Improvement",
                    "Dataset Manager: Übersicht, Split-Zuweisung, Browsing, Synthetik-Tracking",
                    "Ähnlichkeitssuche via ViT-Embeddings + Cosine Similarity",
                    "Explainability: Grad-CAM Saliency Heatmaps",
                    "Human-in-the-Loop Review Queue: Approve/Reject/Correct",
                    "API-Key-Authentifizierung für Agent-Endpoints",
                ],
            },
        ],
        "requirements": {
            "backend": "Python 3.11+ / FastAPI / SQLAlchemy / Alembic / Pydantic / Uvicorn",
            "frontend": "React / TypeScript / Vite / Tailwind CSS / TanStack Query / Zustand",
            "database": "SQLite (17 Tabellen, Alembic-Migrationen)",
            "ml": "PyTorch / torchvision / HuggingFace Transformers / ViT",
            "devops": "Docker / GitHub Actions / pytest / ruff",
        },
        "stats": {
            "files": 130,
            "lines_of_code": 15500,
            "api_routes": 60,
            "database_tables": 17,
            "tests": 56,
            "frontend_pages": 7,
        },
    }
