@echo off
:: fix_shebangs.bat
:: Repairs wildtag_env and validate_env after the wildtag.ai folder has
:: been moved, copied, or extracted to a new location.
cd /d "%~dp0"
echo ============================================
echo  wildtag.ai - Fix environment shebangs
echo ============================================
echo.
if not exist "wildtag_env\python.exe" (
    echo ERROR: wildtag_env not found in this folder.
    pause
    exit /b 1
)
wildtag_env\python.exe fix_shebangs.py
echo.
pause
