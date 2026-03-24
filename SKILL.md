# SKILL.md — Schnellstart-Referenz

## One-Click Installation (empfohlen)

```bash
bash install.sh
```

Erstellt automatisch eine Python-venv, installiert alle Dependencies (Backend + Frontend + ML-Modell + Playwright), und ist danach startbereit.

Optionen:
- `USE_CPU=0 bash install.sh` — GPU/CUDA statt CPU-only PyTorch
- Voraussetzungen: Python >= 3.11, Node.js >= 18

## Server starten (Port 3025)

```bash
# venv aktivieren
source .venv/bin/activate        # Linux/macOS
source .venv/Scripts/activate    # Windows (Git Bash)

# Server starten
python run.py

# Oder im Hintergrund:
nohup python run.py > /dev/null 2>&1 &
```

- Web-GUI: http://localhost:3025
- API-Docs: http://localhost:3025/docs
- Pruefen ob Server laeuft: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3025/`

## Server stoppen

```bash
# Linux/macOS
kill $(lsof -t -i:3025)

# Windows
taskkill.exe /F /IM python.exe
```

## Docker (Alternative)

```bash
docker compose up --build -d
```

Hinweis: Docker Desktop muss installiert sein.

## Hinweise

- Docker ist auf diesem System **nicht installiert** — App direkt mit `python run.py` starten
- `python run.py` startet Uvicorn auf `0.0.0.0:3025`
- Frontend wird als statische Dateien aus `frontend-dist/` von FastAPI ausgeliefert
- Fuer Frontend-Entwicklung mit HMR: `cd frontend && npm run dev`
- SQLite-Datenbank: `schiffs-scraper.db`
- Port konfigurierbar via `.env` → `PORT=3025`
