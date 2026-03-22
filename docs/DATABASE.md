# Datenbankstruktur

SQLite-Datenbank (`schiffs-scraper.db`) mit Alembic-Migrationen.

## Tabellenuebersicht

### Legacy-Tabellen (v1)

| Tabelle | Beschreibung |
|---------|-------------|
| `jobs` | Scraping-Jobs (URL, Status, Fortschritt) |
| `items` | Heruntergeladene Bilder/Schiffe (kombiniert) |
| `categories` | Website-Kategorien |
| `vpn_log` | VPN-Verbindungsprotokoll |
| `predefined_urls` | Vordefinierte Quell-URLs |
| `classifications` | KI-Klassifikationsergebnisse |
| `augmentation_log` | Augmentations-Protokoll |

### Normalisierte Tabellen (v2)

| Tabelle | Beschreibung |
|---------|-------------|
| `ships` | Schiffsentitaeten (Name, Typ, IMO, MMSI, etc.) |
| `ship_aliases` | Alternative Schiffsnamen |
| `images` | Einzelne Bilder (verknuepft mit Schiff) |
| `image_annotations` | Manuelle Korrekturen/Labels |
| `scrape_sources` | Quell-Websites mit Konfiguration |
| `scrape_jobs` | Normalisierte Scraping-Jobs |
| `ml_models` | Modell-Registry (Name, Version, Pfad, Metriken) |
| `training_runs` | Trainingslaeufe mit Konfiguration |
| `inference_logs` | Detaillierte Inferenz-Protokolle |
| `synthetic_jobs` | Synthetische Daten-Jobs |

## Schluesselbeziehungen

```
ships 1──N images
ships 1──N ship_aliases
images 1──N image_annotations
images 1──N inference_logs
ml_models 1──N training_runs
ml_models 1──N inference_logs
scrape_sources 1──N scrape_jobs
jobs 1──N items (legacy)
```

## Migrationen

Verwaltet mit Alembic (`backend/migrations/`):
- `001_initial_v1` — Basis-Schema (Legacy-Tabellen)
- `002_normalize` — Normalisierung + Datenmigration

Migrationen ausfuehren:
```bash
python -m alembic upgrade head
```
