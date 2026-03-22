# Ship Recognition Platform

Modulare Plattform zur Erkennung, Klassifizierung und Verwaltung von Schiffsbildern.

## Features

- **Scraping:** Schiffsbilder von Webseiten herunterladen (ShipSpotting, VesselFinder, MarineTraffic, FleetMon)
- **KI-Erkennung:** Bild hochladen und Schiffstyp erkennen (ViT-Modell, 99.6% Genauigkeit)
- **Modell-Registry:** Mehrere Modelle registrieren, verwalten und aktivieren
- **Training:** Fine-Tuning auf benutzerdefinierte Schiffstypen
- **Batch-Klassifikation:** Alle Bilder automatisch klassifizieren
- **Synthetische Daten:** Bild-Augmentation zum Erzeugen zusaetzlicher Trainingsdaten
- **VPN-Integration:** NordVPN direkt aus der App steuern
- **Dashboard:** Statistiken, Schiffstypen-Verteilung, Quick Actions

## Quick Start

### Voraussetzungen

- Python 3.11+
- Node.js 20+ (fuer Frontend-Build)

### Linux / macOS
```bash
git clone <repo-url>
cd ship-scraper
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python run.py
```

### Windows
```cmd
git clone <repo-url>
cd ship-scraper
setup.bat
venv\Scripts\activate.bat
python run.py
```

### Docker
```bash
docker compose up --build
```

Dann oeffnen: **http://localhost:3025**

API-Dokumentation: **http://localhost:3025/docs**

## Architektur

| Komponente | Technologie |
|-----------|------------|
| Backend | Python / FastAPI / SQLAlchemy |
| Frontend | React / TypeScript / Vite / Tailwind CSS |
| Datenbank | SQLite (17 Tabellen, Alembic-Migrationen) |
| ML | ViT (Vision Transformer) via HuggingFace |
| Port | 3025 |

## Projektstruktur

```
ship-scraper/
  backend/          # FastAPI Backend
    routers/        # API-Endpunkte (10 Router)
    models/         # SQLAlchemy ORM-Modelle
    schemas/        # Pydantic Request/Response-Schemas
    services/       # Business-Logik
    migrations/     # Alembic Datenbankmigrationen
  frontend/         # React + TypeScript SPA
    src/pages/      # 6 Tab-Seiten
    src/hooks/      # TanStack Query Hooks
    src/api/        # Typisierter API-Client
  tests/            # pytest Testsuite (56 Tests)
  ml_engine.py      # ML-Klassifikation, Training, Augmentation
  run.py            # Server-Startskript
```

## Tabs

| Tab | Beschreibung |
|-----|-------------|
| Dashboard | Statistiken, Schiffstypen-Verteilung, Quick Actions |
| Scraper | VPN-Steuerung, Scraping-Jobs erstellen und verwalten |
| Schiffe | Bildergalerie mit Filter, Suche und Detailansicht |
| KI-Erkennung | Bild hochladen und klassifizieren, Batch-Modus |
| Training | Fine-Tuning, Augmentation, Dataset-Browser |
| Einstellungen | URLs verwalten, App-Info, Modell-Details |

## Entwicklung

```bash
# Backend starten (mit Hot-Reload)
DEBUG=true python run.py

# Frontend Dev-Server (mit HMR)
cd frontend && npm run dev

# Tests ausfuehren
pytest tests/ -v

# Lint
ruff check backend/ tests/
```

## Dokumentation

- [DOKUMENTATION.md](DOKUMENTATION.md) — Vollstaendige technische Dokumentation
- [KONZEPT.md](KONZEPT.md) — ML-Architektur und Designentscheidungen
- [docs/API.md](docs/API.md) — API-Endpunkte
- [docs/DATABASE.md](docs/DATABASE.md) — Datenbankstruktur
