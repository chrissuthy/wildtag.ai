@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==============================================================
echo   wildtag - repair validation folders
echo ==============================================================
echo.
echo This checks every validation folder in:
echo   %~dp0
echo and removes leftover entries for images that are not there.
echo Your images and any work you have already done are kept.
echo.

rem --- Make sure the helper script is next to this file ---
if not exist "%~dp0fix_manifests.py" (
    echo PROBLEM: "fix_manifests.py" is missing.
    echo Both files must be saved into the SAME folder as this one.
    echo.
    pause
    exit /b 1
)

rem --- Find the Python that came bundled inside a validation folder ---
set "PY="
for /d %%D in ("*") do (
    if not defined PY if exist "%%~fD\validate_env\python.exe" set "PY=%%~fD\validate_env\python.exe"
    if not defined PY if exist "%%~fD\validate_env\Scripts\python.exe" set "PY=%%~fD\validate_env\Scripts\python.exe"
)

rem --- Fall back to a system Python only if one happens to be installed ---
if not defined PY (
    where py     >nul 2>nul && set "PY=py"
)
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)

if not defined PY (
    echo PROBLEM: could not find Python.
    echo.
    echo This file must sit in the folder that CONTAINS your
    echo ...validation folders ^(the ones you unzipped^), because it
    echo borrows the Python that came inside them.
    echo.
    echo Right now it is in:
    echo   %~dp0
    echo.
    echo Move this file ^(and fix_manifests.py^) up one level so they sit
    echo alongside the fox_001_validation, etc. folders, then try again.
    echo.
    pause
    exit /b 1
)

echo Using Python: !PY!
echo.
"!PY!" "%~dp0fix_manifests.py" "%~dp0"

echo.
pause
endlocal
