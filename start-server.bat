@echo off
cd /d "%~dp0"
echo Ship Recognition Server wird gestartet...

REM Use clean-path venv (avoids Anaconda + OneDrive # path issues with torch)
if exist "C:\Projects\ship-venv\Scripts\python.exe" (
    echo Nutze C:\Projects\ship-venv...
    start /B C:\Projects\ship-venv\Scripts\pythonw.exe run.py >nul 2>&1
    if errorlevel 1 start /B C:\Projects\ship-venv\Scripts\python.exe run.py >nul 2>&1
) else if exist "venv\Scripts\python.exe" (
    echo Nutze venv...
    start /B venv\Scripts\pythonw.exe run.py >nul 2>&1
    if errorlevel 1 start /B venv\Scripts\python.exe run.py >nul 2>&1
) else (
    start /B pythonw run.py >nul 2>&1
    if errorlevel 1 start /B python run.py >nul 2>&1
)

echo Server laeuft im Hintergrund auf http://localhost:3025
timeout /t 2 >nul
