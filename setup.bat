@echo off
REM ============================================================
REM Ship Recognition Platform - Setup (Windows)
REM ============================================================

echo ========================================
echo   Ship Recognition Platform - Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nicht gefunden! Bitte Python 3.11+ installieren.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python gefunden.

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js nicht gefunden. Frontend-Build wird uebersprungen.
    echo Download: https://nodejs.org
    set NO_NODE=1
)

REM Create virtual environment
if not exist "venv" (
    echo Erstelle virtuelle Umgebung...
    python -m venv venv
)

REM Activate venv
echo Aktiviere virtuelle Umgebung...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installiere Python-Abhaengigkeiten...
pip install --upgrade pip -q
pip install -e ".[dev]" -q

REM Create directories
echo Erstelle Verzeichnisse...
if not exist "downloads" mkdir downloads
if not exist "uploads" mkdir uploads
if not exist "augmented" mkdir augmented
if not exist "models\ship_classifier" mkdir models\ship_classifier
if not exist "data" mkdir data
if not exist "logs" mkdir logs

REM Create .env if not exists
if not exist ".env" (
    echo Erstelle .env...
    copy .env.example .env >nul
)

REM Initialize database
echo.
echo Initialisiere Datenbank...
if exist "schiffs-scraper.db" (
    python scripts\migrate_v1.py 2>nul
)
python -m alembic upgrade head 2>nul || python -c "from backend.database import Base, engine, init_db; import backend.models; init_db(); print('Datenbank erstellt.')"

REM Build Frontend
if not defined NO_NODE (
    echo.
    echo Installiere Frontend-Abhaengigkeiten...
    cd frontend
    call npm ci 2>nul || call npm install
    echo Baue Frontend...
    call npm run build
    cd ..
    echo Frontend gebaut.
)

REM Download ML model
if not exist "models\ship_classifier\model.safetensors" (
    echo.
    echo Lade ML-Modell herunter...
    python -c "from transformers import ViTForImageClassification, ViTImageProcessor; p = ViTImageProcessor.from_pretrained('dima806/10_ship_types_image_detection'); m = ViTForImageClassification.from_pretrained('dima806/10_ship_types_image_detection'); p.save_pretrained('models/ship_classifier'); m.save_pretrained('models/ship_classifier'); print('Modell gespeichert.')" 2>nul || echo Modell-Download uebersprungen.
)

echo.
echo ========================================
echo   Setup abgeschlossen!
echo ========================================
echo.
echo   Starten mit:
echo     venv\Scripts\activate.bat
echo     python run.py
echo.
echo   Dann oeffnen: http://localhost:3025
echo   API-Docs:     http://localhost:3025/docs
echo ========================================
echo.
pause
