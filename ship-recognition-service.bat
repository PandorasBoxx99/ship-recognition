@echo off
:: Ship Recognition Platform — Auto-Start Service
:: Startet den Server automatisch mit der korrekten venv.
:: Lege eine Verknuepfung in den Autostart-Ordner:
::   Win+R > shell:startup > Verknuepfung hierher kopieren

cd /d "C:\Projects\ship-scraper"

echo ============================================
echo  Ship Recognition Server startet...
echo ============================================

if exist "C:\Projects\ship-venv\Scripts\python.exe" (
    echo Nutze C:\Projects\ship-venv
    C:\Projects\ship-venv\Scripts\python.exe run.py
) else if exist "%~dp0venv\Scripts\python.exe" (
    echo Nutze lokale venv
    "%~dp0venv\Scripts\python.exe" run.py
) else (
    echo Nutze System-Python
    python run.py
)

echo Server beendet.
pause
