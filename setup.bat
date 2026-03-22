@echo off
REM ============================================================
REM Ship-Scraper - One-Click Setup (Windows)
REM ============================================================

echo ========================================
echo   Ship-Scraper Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nicht gefunden! Bitte Python 3.8+ installieren.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python gefunden.

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
echo Installiere Abhaengigkeiten...
pip install --upgrade pip
pip install -r requirements.txt

REM Create directories
echo.
echo Erstelle Verzeichnisse...
if not exist "downloads" mkdir downloads
if not exist "uploads" mkdir uploads
if not exist "augmented" mkdir augmented
if not exist "models\ship_classifier" mkdir models\ship_classifier

REM Initialize database
echo.
echo Initialisiere Datenbank...
python -c "import sqlite3; conn = sqlite3.connect('schiffs-scraper.db'); f = open('schema.sql','r'); conn.executescript(f.read()); f.close(); conn.commit(); conn.close(); print('Datenbank erstellt.')"

REM Check if model exists
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
echo     python app.py
echo.
echo   Dann oeffnen: http://localhost:3025
echo ========================================
echo.
pause
