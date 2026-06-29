# Ship-Scraper - Dokumentation

**Version:** 1.0.0
**Erstellt:** 2026-03-22
**Projekt:** Schiffs-Bilderkennung fuer Ronny (via Bernhard)

---

## Inhaltsverzeichnis

1. [Ueberblick](#1-ueberblick)
2. [Installation](#2-installation)
3. [Starten der App](#3-starten-der-app)
4. [Features](#4-features)
5. [Frontend - Tabs](#5-frontend---tabs)
6. [API-Referenz](#6-api-referenz)
7. [ML-Modell](#7-ml-modell)
8. [Synthetische Daten / Augmentation](#8-synthetische-daten--augmentation)
9. [Training](#9-training)
10. [Datenbank-Schema](#10-datenbank-schema)
11. [Projektstruktur](#11-projektstruktur)
12. [VPN-Integration](#12-vpn-integration)
13. [Troubleshooting](#13-troubleshooting)
14. [Weiterentwicklung](#14-weiterentwicklung)

---

## 1. Ueberblick

Ship-Scraper ist eine Web-Applikation zum:

- **Herunterladen** von Schiffsbildern von Webseiten (ShipSpotting, VesselFinder, etc.)
- **Klassifizieren** von Schiffsbildern mittels KI (Vision Transformer)
- **Trainieren** eigener Modelle auf benutzerdefinierte Schiffstypen
- **Erzeugen** synthetischer Trainingsdaten durch Bild-Augmentation
- **Verwalten** aller Daten in einer SQLite-Datenbank

### Tech-Stack

| Komponente | Technologie |
|-----------|-------------|
| Backend | Python / Flask |
| Frontend | Vanilla HTML/CSS/JS |
| Datenbank | SQLite |
| ML-Modell | ViT (Vision Transformer) via HuggingFace Transformers |
| Augmentation | torchvision.transforms |
| VPN | NordVPN CLI |

---

## 2. Installation

### Voraussetzungen

- Python 3.8 oder hoeher
- pip (Python Package Manager)
- Git (optional, fuer Versionskontrolle)
- NordVPN CLI (optional, fuer VPN-Features)

### One-Click Setup

**Linux / macOS:**
```bash
git clone https://github.com/<username>/ship-scraper.git
cd ship-scraper
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
git clone https://github.com/<username>/ship-scraper.git
cd ship-scraper
setup.bat
```

### Manuelles Setup

```bash
# Virtuelle Umgebung erstellen
python -m venv venv

# Aktivieren
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate.bat       # Windows

# Dependencies installieren
pip install -r requirements.txt

# Datenbank initialisieren (automatisch beim ersten Start)
python run.py
```

### Was das Setup macht

1. Python-Version pruefen
2. Virtuelle Umgebung erstellen (`venv/`)
3. Alle Python-Pakete installieren
4. Verzeichnisse anlegen (`downloads/`, `uploads/`, `augmented/`)
5. SQLite-Datenbank initialisieren
6. ML-Modell von HuggingFace herunterladen (~350 MB)

---

## 3. Starten der App

```bash
# Virtuelle Umgebung aktivieren (falls nicht aktiv)
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate.bat       # Windows

# App starten
python run.py
```

Die App laeuft dann auf: **http://localhost:3025**

---

## 4. Features

### Scraping
- URL eingeben und Webseite analysieren
- Kategorien/Ordner automatisch erkennen
- Rate-Limiting mit konfigurierbaren Delays (1-5 Sekunden)
- VPN-Pflicht pro Job aktivierbar
- Fortschrittsanzeige in Echtzeit
- Jobs pausieren/fortsetzen/loeschen

### KI-Erkennung
- Bild hochladen per Drag & Drop oder Dateiauswahl
- Klassifizierung mit Top-5 Ergebnissen und Wahrscheinlichkeiten
- 10 Schiffstypen erkennbar (99.6% Genauigkeit)
- Nachtraegliche Klassifizierung bestehender Bilder

### Training
- Fine-Tuning auf eigene Daten
- Konfigurierbare Hyperparameter (Epochen, Batch Size, Learning Rate)
- Automatische Train/Validation Split (80/20)
- Trainings-Fortschritt in Echtzeit

### Synthetische Daten
- 6 verschiedene Augmentationen waehlbar
- Konfigurierbare Anzahl pro Quellbild (1-20)
- Ausgabe in separatem Verzeichnis

### VPN-Integration
- NordVPN direkt aus der App steuern
- Laenderwahl (DE, NL, CH, US, UK, FR, SE)
- IP-Rotation auf Knopfdruck
- Status-Anzeige in der Header-Leiste

---

## 5. Frontend - Tabs

### Tab 1: Dashboard
- Statistik-Uebersicht (Jobs, Downloads, Klassifizierungen)
- Schiffstypen-Verteilung als Balkendiagramm
- Letzte Aktivitaeten
- Quick-Action Buttons

### Tab 2: Scraper
- VPN-Steuerung (Verbinden, Trennen, IP wechseln)
- Neuen Scraping-Job erstellen
- URL aus Dropdown waehlen oder manuell eingeben
- Website analysieren und Kategorien anzeigen
- Alle Jobs mit Status und Fortschritt

### Tab 3: Schiffe
- Bildergalerie aller heruntergeladenen Schiffe
- Filter nach Schiffstyp
- Textsuche (Name, IMO-Nummer)
- Detailansicht mit allen Metadaten
- KI-Klassifizierung aus Detailansicht starten

### Tab 4: KI-Erkennung
- Bild-Upload per Drag & Drop
- Klassifizierungs-Ergebnis mit farbigen Balken
- Letzte Klassifizierungen (Historie)
- Modell-Info (Architektur, Labels, Genauigkeit)

### Tab 5: Training
- Fine-Tuning mit eigenen Daten starten
- Hyperparameter konfigurieren
- Synthetische Daten erzeugen (Augmentation)
- Verfuegbare Datasets anzeigen

### Tab 6: Einstellungen
- Vordefinierte URLs verwalten
- App-Info (Version, Port, Modell)
- Datenbank zuruecksetzen

---

## 6. API-Referenz

### VPN

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/vpn/status` | GET | VPN-Status pruefen |
| `/api/vpn/connect` | POST | VPN verbinden (`{country: "Germany"}`) |
| `/api/vpn/disconnect` | POST | VPN trennen |
| `/api/vpn/rotate` | POST | IP wechseln |

### Scraping & Jobs

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/analyze` | POST | URL analysieren (`{url: "..."}`) |
| `/api/jobs` | GET | Alle Jobs auflisten |
| `/api/jobs` | POST | Neuen Job erstellen |
| `/api/jobs/:id` | GET | Job-Details |
| `/api/jobs/:id/start` | POST | Job starten |
| `/api/jobs/:id/pause` | POST | Job pausieren |
| `/api/jobs/:id/delete` | DELETE | Job loeschen |

### Schiffe

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/ships` | GET | Schiffe auflisten (Paginierung, Filter) |
| `/api/ships/:id` | GET | Schiff-Details |
| `/api/ships/stats` | GET | Schiffs-Statistiken |

### ML / Klassifizierung

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/classify` | POST | Bild hochladen und klassifizieren (multipart) |
| `/api/classify/ship/:id` | POST | Bestehendes Schiff klassifizieren |
| `/api/model/info` | GET | Modell-Informationen |
| `/api/classifications` | GET | Klassifizierungs-Historie |

### Training

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/training/start` | POST | Training starten |
| `/api/training/status` | GET | Training-Status |
| `/api/training/datasets` | GET | Verfuegbare Datasets |

### Augmentation

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/augment` | POST | Augmentation starten |
| `/api/augment/status` | GET | Augmentation-Status |

### Sonstiges

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/stats` | GET | Allgemeine Statistiken |
| `/api/urls` | GET/POST | Vordefinierte URLs |
| `/api/urls/:id` | DELETE | URL loeschen |

---

## 7. ML-Modell

### Vortrainiertes Modell

- **Name:** dima806/10_ship_types_image_detection
- **Architektur:** ViT (Vision Transformer) - `google/vit-base-patch16-224-in21k`
- **Genauigkeit:** 99.6%
- **Input:** 224x224 px RGB-Bilder
- **Output:** 10 Schiffstypen mit Wahrscheinlichkeiten

### Erkannte Schiffstypen

| # | Schiffstyp | Beschreibung |
|---|-----------|-------------|
| 0 | Bulkers | Massengutfrachter |
| 1 | Recreational | Freizeitboote |
| 2 | Sailboat | Segelboote |
| 3 | DDG | Zerstoerer |
| 4 | Container Ship | Containerschiffe |
| 5 | Tug | Schlepper |
| 6 | Aircraft Carrier | Flugzeugtraeger |
| 7 | Cruise | Kreuzfahrtschiffe |
| 8 | Submarine | U-Boote |
| 9 | Car Carrier | Autotransporter |

### Modell-Dateien

```
models/ship_classifier/
    config.json              # Modell-Konfiguration
    model.safetensors        # Gewichte (~350 MB)
    preprocessor_config.json # Bild-Vorverarbeitung
    checkpoint-512/          # Trainings-Checkpoint
    checkpoint-1024/         # Trainings-Checkpoint
    checkpoint-2560/         # Trainings-Checkpoint
```

---

## 8. Synthetische Daten / Augmentation

Wenn nicht genuegend echte Bilder fuer einen Schiffstyp vorhanden sind,
koennen synthetische Trainingsdaten erzeugt werden.

### Verfuegbare Augmentationen

| Augmentation | Beschreibung |
|-------------|-------------|
| Horizontal Flip | Spiegelung an der vertikalen Achse |
| Rotation | Zufaellige Drehung um +-15 Grad |
| Color Jitter | Zufaellige Aenderung von Helligkeit, Kontrast, Saettigung |
| Random Crop | Zufaelliger Bildausschnitt (70-100% des Originals) |
| Gaussian Blur | Leichte Unschaerfe |
| Perspective | Zufaellige Perspektiv-Verzerrung |

### Empfehlung

- 5-10 Varianten pro Quellbild sind ein guter Richtwert
- Bei weniger als 100 Bildern pro Klasse: Augmentation nutzen
- Ziel: Mindestens 500 Bilder pro Klasse fuer gutes Training

### Ausgabe

Augmentierte Bilder werden in `augmented/aug_YYYYMMDD_HHMMSS/` gespeichert.

---

## 9. Training

### Voraussetzungen fuer Fine-Tuning

1. **Dataset-Struktur:**
```
mein_dataset/
    Bulkers/
        bild1.jpg
        bild2.jpg
        ...
    Container Ship/
        bild1.jpg
        ...
    Mein_Neuer_Typ/
        bild1.jpg
        ...
```

2. **Mindestens 10 Bilder** insgesamt (empfohlen: 500+ pro Klasse)
3. **Ausreichend RAM** (8 GB minimum, 16 GB empfohlen)

### Hyperparameter

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| Epochen | 5 | Anzahl Trainingsdurchlaeufe |
| Batch Size | 8 | Bilder pro Trainingsschritt |
| Learning Rate | 5e-5 | Lernrate (kleiner = vorsichtiger) |

### Training starten

1. Tab "Training" oeffnen
2. Dataset-Pfad eingeben
3. Hyperparameter anpassen (optional)
4. "Training starten" klicken
5. Fortschritt wird live angezeigt

Das trainierte Modell wird in `models/ship_classifier/finetune_DATUM/` gespeichert.

---

## 10. Datenbank-Schema

### Tabellen

**jobs** - Scraping-Auftraege
- id, url, name, status, total_items, downloaded, limit_count, delay_min/max, vpn_required, timestamps

**items** - Heruntergeladene Bilder/Schiffe
- id, job_id, source_url, image_url, local_path, ship_name, ship_type, imo_number, mmsi, metadata, status, timestamps

**categories** - Gefundene Kategorien auf Webseiten
- id, job_id, name, url, parent_id, item_count, selected

**vpn_log** - VPN-Verbindungs-Log
- id, action, country, ip_address, timestamp, success

**predefined_urls** - Vordefinierte URLs fuer Dropdown
- id, url, name

**classifications** - KI-Klassifizierungen
- id, item_id, image_path, predicted_type, confidence, all_predictions, model_name

**augmentation_log** - Augmentations-Protokoll
- id, source_dir, output_dir, num_source_images, num_generated, transforms_config

---

## 11. Projektstruktur

```
ship-scraper/
    run.py                  # FastAPI-Start (Uvicorn)
    backend/                # FastAPI-Backend (Router, Services, Modelle)
    ml_engine.py            # ML-Logik (Klassifizierung, Training, Augmentation)
    requirements.txt        # Python Dependencies
    setup.sh                # One-Click Setup (Linux/Mac)
    setup.bat               # One-Click Setup (Windows)
    .gitignore              # Git Ignore Rules
    DOKUMENTATION.md        # Diese Datei
    KONZEPT.md              # Projekt-Konzept & Recherche
    README.md               # Kurzuebersicht
    templates/
        index.html          # Frontend (Single-Page App)
    static/                 # Statische Assets
    models/
        ship_classifier/    # ViT-Modell + Checkpoints
    downloads/              # Heruntergeladene Bilder (nach Job-ID)
    uploads/                # Hochgeladene Bilder (Klassifizierung)
    augmented/              # Synthetische Bilder
    .agent-coord/           # Agent-Koordination
    schiffs-scraper.db      # SQLite-Datenbank
```

---

## 12. VPN-Integration

### NordVPN CLI installieren

**Linux:**
```bash
sh <(curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh)
nordvpn login
```

**Windows:**
NordVPN Desktop App installieren - CLI ist integriert.

### Ohne VPN nutzen

Die App funktioniert auch ohne VPN. Einfach die Checkbox "VPN erforderlich"
beim Erstellen eines Jobs deaktivieren.

**Warnung:** Ohne VPN koennen Webseiten die IP sperren bei zu vielen Anfragen.

---

## 13. Troubleshooting

### "Model not loaded"
```bash
pip install torch transformers Pillow safetensors
```
Oder: Setup-Script erneut ausfuehren.

### "Port 3025 already in use"
```bash
# Prozess finden und beenden
lsof -i :3025           # Linux/Mac
netstat -ano | findstr 3025  # Windows
```

### "torch not found" / CUDA Fehler
Fuer CPU-only Installation:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Datenbank zuruecksetzen
1. App stoppen
2. `schiffs-scraper.db` loeschen
3. App neu starten (DB wird automatisch erstellt)

### VPN verbindet nicht
1. NordVPN CLI installiert?
2. Eingeloggt? (`nordvpn login`)
3. Firewall-Regeln pruefen

---

## 14. Weiterentwicklung

### Moegliche Features

- **Batch-Klassifizierung:** Alle heruntergeladenen Bilder auf einmal klassifizieren
- **Export:** Daten als CSV/JSON exportieren
- **Erweiterte Suche:** Volltextsuche ueber alle Metadaten
- **Benutzerverwaltung:** Login/Authentifizierung
- **Scheduler:** Automatische Scraping-Jobs zu festgelegten Zeiten
- **Weitere Schiffstypen:** Custom-Labels durch Fine-Tuning
- **ONNX-Export:** Modell fuer schnellere Inference optimieren
- **Docker:** Containerisierung fuer einfaches Deployment
- **API-Keys:** Zugriffskontrolle fuer die REST-API
- **Webhook-Benachrichtigungen:** Bei Job-Abschluss benachrichtigen

### Eigene Schiffstypen hinzufuegen

1. Bilder sammeln (Scraper oder manuell)
2. In Ordnerstruktur organisieren (ein Ordner pro Typ)
3. Optional: Augmentation nutzen fuer mehr Trainingsdaten
4. Fine-Tuning starten
5. Neues Modell wird automatisch gespeichert
