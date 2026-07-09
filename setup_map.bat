@echo off
:: setup_map.bat
:: Installs tkinterweb for in-app map rendering.
:: Run once if the Map tab shows an error.

cd /d "%~dp0"

if not exist "wildtag_env\Scripts\pip.exe" (
    echo ERROR: wildtag_env not found.
    pause
    exit /b 1
)

echo Installing map renderer...
wildtag_env\Scripts\pip install tkinterweb --quiet

echo.
echo Done. Restart wildtag.ai to use the Map tab.
pause
