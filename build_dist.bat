@echo off
:: build_dist.bat
:: Builds the wildtag.ai distribution zip.
:: Run from wildtag.ai\ folder.

cd /d "%~dp0"

echo ============================================
echo  wildtag.ai - Build distribution package
echo ============================================
echo.

set DIST=wildtag_dist
set ZIP=wildtag_beta3.zip

:: Model-free by default: the app downloads the chosen model on first use.
:: Set BUNDLE_MODELS=1 to also copy the pre-downloaded models\ into the dist.
set BUNDLE_MODELS=0

:: ── 1. Clear and recreate dist folder ────────────────────────────
echo Clearing %DIST%\...
if exist "%DIST%" (
    rmdir /s /q "%DIST%" 2>nul
    :: Retry a few times — Dropbox (or antivirus) can briefly lock a file
    :: mid-sync right after a bulk delete like this. Give it a moment
    :: rather than silently building on top of a half-cleared folder.
    for /l %%i in (1,1,5) do (
        if exist "%DIST%" (
            timeout /t 2 /nobreak >nul
            rmdir /s /q "%DIST%" 2>nul
        )
    )
)
if exist "%DIST%" (
    echo.
    echo ERROR: could not fully clear %DIST%\ — a file is still locked
    echo ^(likely Dropbox sync or antivirus^). Pause Dropbox syncing and
    echo close any programs that might have a file open in %DIST%\,
    echo then run this again. Refusing to build on top of a half-cleared
    echo folder, that would produce an inconsistent zip.
    echo.
    pause
    exit /b 1
)
mkdir "%DIST%"

:: ── 2. Core app files ─────────────────────────────────────────────
echo Copying app files...
copy /y wildtag.py              "%DIST%\wildtag.py"              >nul
copy /y wildtag.ico             "%DIST%\wildtag.ico"             >nul
copy /y wildtag.bat             "%DIST%\wildtag.bat"             >nul
copy /y README.txt              "%DIST%\README.txt"              >nul
copy /y deployment_template.csv "%DIST%\deployment_template.csv" >nul
if exist wildtag_manual.pdf     copy /y wildtag_manual.pdf  "%DIST%\wildtag_manual.pdf" >nul
if exist setup_gpu.bat          copy /y setup_gpu.bat        "%DIST%\setup_gpu.bat"      >nul
if exist fix_shebangs.py        copy /y fix_shebangs.py      "%DIST%\fix_shebangs.py"    >nul
if exist fix_shebangs.bat       copy /y fix_shebangs.bat     "%DIST%\fix_shebangs.bat"   >nul
if exist setup_map.bat          copy /y setup_map.bat        "%DIST%\setup_map.bat"      >nul
if exist setup_validate_env.bat copy /y setup_validate_env.bat "%DIST%\setup_validate_env.bat" >nul

:: ── 3. wt_models ─────────────────────────────────────────────────
echo Copying wt_models...
xcopy /e /i /y /q wt_models "%DIST%\wt_models" >nul

:: ── 4. Models (model-free by default) ────────────────────────────
if "%BUNDLE_MODELS%"=="1" (
    echo Copying models ^(this may take a while^)...
    xcopy /e /i /y /q models "%DIST%\models" >nul
) else (
    echo Model-free build: skipping models\ ^(users download on first use^).
)

:: ── 5. wildtag_env ───────────────────────────────────────────────
echo Copying wildtag_env (this may take a while)...
xcopy /e /i /y /q wildtag_env "%DIST%\wildtag_env" >nul

:: ── 6. validate_env ──────────────────────────────────────────────
if exist validate_env (
    echo Copying validate_env...
    xcopy /e /i /y /q validate_env "%DIST%\validate_env" >nul
)

:: ── 7. Report dist folder size ───────────────────────────────────
echo.
echo Contents of %DIST%\:
dir /s /-c "%DIST%" | findstr "File(s)"
echo.

:: ── 8. Zip using 7-zip if available, else PowerShell ─────────────
echo Creating %ZIP%...
if exist "%ZIP%" del "%ZIP%"

where 7z >nul 2>&1
if %errorlevel% == 0 (
    echo Using 7-Zip ^(fast^)...
    7z a -tzip -mx=1 -mmt=on "%ZIP%" ".\%DIST%\*"
) else (
    where "C:\Program Files\7-Zip\7z.exe" >nul 2>&1
    if exist "C:\Program Files\7-Zip\7z.exe" (
        echo Using 7-Zip ^(fast^)...
        "C:\Program Files\7-Zip\7z.exe" a -tzip -mx=1 -mmt=on "%ZIP%" ".\%DIST%\*"
    ) else (
        echo 7-Zip not found - using PowerShell ^(slow for large files^)...
        echo Tip: Install 7-Zip from https://7-zip.org for much faster zipping.
        powershell -Command "Compress-Archive -Path '%DIST%\*' -DestinationPath '%ZIP%' -Force"
    )
)

if exist "%ZIP%" (
    echo.
    for %%A in ("%ZIP%") do echo Done^^! %ZIP% ^(%%~zA bytes^)
    echo.
    echo Upload %ZIP% to Google Drive and update the sharing link.
) else (
    echo ERROR: Zip failed.
)

echo.
pause
