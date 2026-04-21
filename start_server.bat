@echo off
REM ============================================================
REM  BearSmart / Revox API - local dev server launcher (Windows)
REM  Double-click this file to start the server at
REM     http://127.0.0.1:8000
REM  Press Ctrl+C in this window to stop it.
REM ============================================================

cd /d "%~dp0"

echo.
echo === BearSmart local server ===
echo Folder: %cd%
echo.

REM --- First-time setup: create venv if missing ---
if not exist ".venv\Scripts\activate.bat" (
    echo [setup] Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: could not create virtual environment.
        echo Make sure Python is installed and on PATH.
        echo Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM --- Activate venv ---
call ".venv\Scripts\activate.bat"

REM --- Install / update dependencies ---
echo [setup] Installing dependencies (this is fast after the first run)...
python -m pip install --upgrade pip >nul
if exist "requirements-dev.txt" (
    pip install -r requirements-dev.txt
) else (
    pip install -r requirements.txt
)

REM --- Start server ---
echo.
echo === Starting server ===
echo Open in your browser:  http://127.0.0.1:8000/docs
echo Press Ctrl+C here to stop.
echo.
uvicorn app.main:app --reload

pause
