# Ship-Scraper

Web-App zum Download, Klassifizierung und Training von Schiffsbildern.

## Features

- **Scraping:** Schiffsbilder von Webseiten herunterladen (ShipSpotting, VesselFinder, etc.)
- **KI-Erkennung:** Bild hochladen und Schiffstyp mit Wahrscheinlichkeit erkennen (99.6% Genauigkeit)
- **Training:** Eigenes Modell auf benutzerdefinierte Schiffstypen trainieren (Fine-Tuning)
- **Synthetische Daten:** Bild-Augmentation zum Erzeugen zusaetzlicher Trainingsdaten
- **VPN-Integration:** NordVPN direkt aus der App steuern
- **Dashboard:** Statistiken, Schiffstypen-Verteilung, Quick Actions

## Quick Start

### Linux / macOS
```bash
git clone https://github.com/<username>/ship-scraper.git
cd ship-scraper
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python app.py
```

### Windows
```cmd
git clone https://github.com/<username>/ship-scraper.git
cd ship-scraper
setup.bat
venv\Scripts\activate.bat
python app.py
```

Dann oeffnen: **http://localhost:3025**

## Tabs

| Tab | Beschreibung |
|-----|-------------|
| Dashboard | Statistiken, Schiffstypen-Verteilung, Quick Actions |
| Scraper | VPN-Steuerung, Scraping-Jobs erstellen und verwalten |
| Schiffe | Bildergalerie mit Filter, Suche und Detailansicht |
| KI-Erkennung | Bild hochladen und klassifizieren lassen |
| Training | Fine-Tuning starten, synthetische Daten erzeugen |
| Einstellungen | URLs verwalten, App-Info |

## Tech-Stack

- **Backend:** Python / Flask
- **Frontend:** Vanilla HTML/CSS/JS
- **Datenbank:** SQLite
- **ML:** ViT (Vision Transformer) via HuggingFace
- **Port:** 3025

## Dokumentation

Siehe [DOKUMENTATION.md](DOKUMENTATION.md) fuer die vollstaendige Dokumentation.

## Projekt-Kontext

Teil des "Schiffs-Bilderkennung fuer Ronny" Projekts.
Siehe [KONZEPT.md](KONZEPT.md) fuer Details zur ML-Architektur.
