@echo off
:: build_validate_env.bat
:: Creates a minimal Python environment for validation-only use.
:: Run this once from the wildtag.ai\ dev folder.
:: Requires internet connection to download packages.

cd /d "%~dp0"

echo ============================================
echo  wildtag.ai - Build Validation Environment
echo ============================================
echo.

:: Check Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on PATH.
    echo Please install Python 3.11 from https://python.org
    pause
    exit /b 1
)

python --version

:: Create the venv
echo.
echo Creating validate_env...
python -m venv validate_env
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

:: Install only what validation needs
echo.
echo Installing dependencies...
validate_env\Scripts\pip install --upgrade pip --quiet
validate_env\Scripts\pip install Pillow --quiet

echo.
echo Done. validate_env is ready.
echo.
echo Next steps:
echo   1. Run package_validate.bat to create a distribution zip
echo.
pause
