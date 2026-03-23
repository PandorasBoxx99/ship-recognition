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


@router.get("/models")
def get_model_documentation():
    """Detailed documentation about the active model and alternatives."""
    return {
        "active_model": {
            "name": "dima806/10_ship_types_image_detection",
            "short_name": "ViT Ship Classifier",
            "version": "1.0.0",
            "architecture": "Vision Transformer (ViT-Base, Patch16, 224px)",
            "base_model": "google/vit-base-patch16-224-in21k (ImageNet-21k pretrained)",
            "parameters": "85.8 Mio.",
            "accuracy": "99.61%",
            "f1_score": "0.9961 (gewichtet)",
            "test_samples": 4092,
            "training_dataset": "~6.000 Bilder (Kaggle Ship Types)",
            "input_size": "224x224 RGB",
            "license": "Apache 2.0",
            "huggingface_url": "https://huggingface.co/dima806/10_ship_types_image_detection",
            "kaggle_url": "https://www.kaggle.com/code/dima806/vessel-ship-type-detection",
            "classes": [
                {"name": "Bulkers", "precision": 0.9927, "recall": 1.0000, "description": "Frachtschiffe / Massengutfrachter"},
                {"name": "Container Ship", "precision": 1.0000, "recall": 0.9951, "description": "Containerschiffe"},
                {"name": "Cruise", "precision": 1.0000, "recall": 1.0000, "description": "Kreuzfahrtschiffe"},
                {"name": "Car Carrier", "precision": 0.9951, "recall": 0.9976, "description": "Autotransporter"},
                {"name": "Tug", "precision": 0.9951, "recall": 0.9927, "description": "Schlepper"},
                {"name": "Sailboat", "precision": 0.9975, "recall": 0.9853, "description": "Segelboote"},
                {"name": "Recreational", "precision": 0.9902, "recall": 0.9927, "description": "Freizeitboote"},
                {"name": "DDG", "precision": 0.9976, "recall": 1.0000, "description": "Zerstörer (Guided Missile Destroyer)"},
                {"name": "Aircraft Carrier", "precision": 1.0000, "recall": 0.9976, "description": "Flugzeugträger"},
                {"name": "Submarine", "precision": 0.9927, "recall": 1.0000, "description": "U-Boote"},
            ],
            "strengths": [
                "Sehr hohe Genauigkeit (99.6%)",
                "Schnelle Inferenz auf CPU",
                "Gut dokumentiert, Open Source (Apache 2.0)",
                "Leichtgewichtig (85.8M Parameter)",
            ],
            "limitations": [
                "Nur 10 Schiffstypen — keine Feinunterscheidung (z.B. Tankerarten)",
                "Kleines Trainingsdataset (~6.000 Bilder)",
                "Keine Erkennung mehrerer Schiffe im Bild (nur Klassifikation)",
                "Optimiert für Seitenansicht-Fotos, nicht Satellitenbilder",
            ],
        },
        "alternatives": [
            {
                "name": "EfficientNetV2B3 (InaTechShips)",
                "type": "CNN",
                "accuracy": "95.89%",
                "classes": 5,
                "dataset": "InaTechShips (2025)",
                "pros": "Leichtgewichtig, schnell, modernes Dataset",
                "cons": "Weniger Klassen, geringere Genauigkeit",
                "url": "https://www.sciencedirect.com/science/article/abs/pii/S0029801825005372",
            },
            {
                "name": "CNN + ViT Ensemble (DeepShip)",
                "type": "Ensemble (CNN + Transformer)",
                "accuracy": "98.32–99.50%",
                "classes": "variabel",
                "dataset": "DeepShip / ShipsEar",
                "pros": "State-of-the-art Genauigkeit, robust",
                "cons": "Komplexer, langsamer, nicht als einzelnes Modell verfügbar",
                "url": "https://www.sciencedirect.com/science/article/abs/pii/S1566253525006426",
            },
            {
                "name": "YOLOv8 Marine Vessel Detection",
                "type": "Object Detection",
                "accuracy": "mAP@50: 98.9%",
                "classes": "Detection (kein Typ)",
                "dataset": "Sentinel-2 Satellitenbilder",
                "pros": "Erkennt + lokalisiert Schiffe in Bildern, Echtzeit",
                "cons": "Keine Typklassifikation, nur Satellitenbilder",
                "url": "https://huggingface.co/mayrajeo/marine-vessel-detection-yolov8",
            },
            {
                "name": "ShipRSImageNet",
                "type": "Dataset + Benchmarks",
                "accuracy": "variabel",
                "classes": 50,
                "dataset": "3.435 Satellitenbilder, 50 Schiffsklassen",
                "pros": "Größte Klassenzahl (50), Satellitenbilder",
                "cons": "Kleines Dataset, keine ready-to-use Modelle",
                "url": "https://github.com/zzndream/ShipRSImageNet",
            },
            {
                "name": "ResNet-152 (Game of Deep Learning)",
                "type": "CNN",
                "accuracy": "90.56%",
                "classes": 5,
                "dataset": "Game of Deep Learning (8.932 Bilder)",
                "pros": "Großes Dataset, bewährte Architektur",
                "cons": "Geringere Genauigkeit, nur 5 Klassen",
                "url": "https://www.kaggle.com/datasets/arpitjain007/game-of-deep-learning-ship-datasets",
            },
            {
                "name": "MESTR (Multi-Task Enhanced Ship-Type Recognition)",
                "type": "Transformer (Multi-Task)",
                "accuracy": "+12% vs. Baseline",
                "classes": "variabel",
                "dataset": "Forschungsdataset",
                "pros": "Neuester Stand der Forschung, Multi-Task",
                "cons": "Nicht öffentlich verfügbar, Forschungsphase",
                "url": "https://www.tandfonline.com/doi/full/10.1080/10095020.2024.2331552",
            },
        ],
        "datasets": [
            {"name": "Game of Deep Learning", "images": 8932, "classes": 5, "types": "Cargo, Tanker, Military, Carrier, Cruise", "source": "Kaggle"},
            {"name": "ShipRSImageNet", "images": 3435, "classes": 50, "types": "50 Schiffsklassen (Satellit)", "source": "GitHub"},
            {"name": "InaTechShips", "images": "k.A.", "classes": 5, "types": "Indonesische Schiffe", "source": "Paper (2025)"},
            {"name": "DeepShip", "images": "k.A.", "classes": "variabel", "types": "Audio + Bild Kombination", "source": "Paper"},
        ],
    }
