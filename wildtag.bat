@echo off
:: wildtag.ai launcher
cd /d "%~dp0"

if not exist "wildtag_env\python.exe" (
    echo ERROR: wildtag_env not found.
    pause
    exit /b 1
)

if not exist "wildtag.py" (
    echo ERROR: wildtag.py not found.
    pause
    exit /b 1
)

:: Point kagglehub at our bundled SpeciesNet weights — no internet needed
set KAGGLEHUB_CACHE=%~dp0models\speciesnet-global\kagglehub_cache

echo Starting wildtag.ai...
wildtag_env\python.exe wildtag.py
