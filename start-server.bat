@echo off
cd /d "%~dp0"
echo Ship Recognition Server wird gestartet...
start /B pythonw run.py >nul 2>&1
if errorlevel 1 (
    start /B python run.py >nul 2>&1
)
echo Server laeuft im Hintergrund auf http://localhost:3025
timeout /t 2 >nul
