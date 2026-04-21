@echo off
REM ============================================================
REM  Git safety-net setup for BearSmart
REM  Double-click to:
REM    1. Clean up any broken .git folder
REM    2. Initialize a fresh git repo
REM    3. Commit everything as "baseline"
REM  After this runs once, Victor can roll back anything with:
REM    git reset --hard HEAD
REM ============================================================

cd /d "%~dp0"

echo.
echo === BearSmart git safety-net setup ===
echo Folder: %cd%
echo.

REM --- Check git is installed ---
where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: git is not installed.
    echo Download it from https://git-scm.com/download/win
    echo Then re-run this script.
    pause
    exit /b 1
)

REM --- Remove any broken .git folder from sandbox attempt ---
if exist ".git" (
    echo Removing previous .git folder...
    rmdir /s /q .git
)

REM --- Init + baseline commit ---
echo Initializing git repo...
git init -b main
git config user.email "victor@bearsmart.local"
git config user.name "Victor"

echo Staging files...
git add .

echo Creating baseline commit...
git commit -m "baseline: pre-Horizon 0 state"

echo.
echo === Done ===
echo If Claude ever breaks something, run this in PowerShell:
echo     git reset --hard HEAD
echo.
pause
