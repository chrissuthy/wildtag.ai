@echo off
:: package_validate.bat
:: Packages the validation folder + lightweight app into a zip
:: for sending to collaborators.
:: Run from wildtag.ai\ dev folder after running a wildtag job.

cd /d "%~dp0"

echo ============================================
echo  wildtag.ai - Package Validation Bundle
echo ============================================
echo.

:: Check validate_env exists
if not exist "validate_env\Scripts\python.exe" (
    echo ERROR: validate_env not found.
    echo Please run build_validate_env.bat first.
    pause
    exit /b 1
)

:: Ask for the project folder to package
set /p PROJECT_FOLDER=Enter full path to project folder (containing validation\): 

:: Strip any surrounding quotes
set PROJECT_FOLDER=%PROJECT_FOLDER:"=%

echo DEBUG: Project folder is [%PROJECT_FOLDER%]
echo DEBUG: Checking for validation folder...
pause

if not exist "%PROJECT_FOLDER%\validation" (
    echo ERROR: No validation\ folder found in %PROJECT_FOLDER%
    echo Please run a wildtag job with "Prepare validation folder" enabled first.
    pause
    exit /b 1
)

:: Get project name from folder
for %%I in ("%PROJECT_FOLDER%") do set PROJECT_NAME=%%~nxI

:: Output zip name
set ZIP_NAME=wildtag_validate_%PROJECT_NAME%.zip
echo.
echo Packaging: %ZIP_NAME%

:: Build the bundle using Python
validate_env\Scripts\python.exe -c "
import shutil, zipfile, os, sys
from pathlib import Path

project  = Path(r'%PROJECT_FOLDER%')
val_dir  = project / 'validation'
out_zip  = Path(r'%ZIP_NAME%')
app_root = Path('.')

print('  Adding validate_env...')
with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

    # Add validate_env
    for f in Path('validate_env').rglob('*'):
        if f.is_file() and '__pycache__' not in str(f):
            zf.write(f, f'wildtag_validate/{f}')

    # Add app files
    for fname in ['wildtag.py', 'wildtag.ico', 'wildtag_manual.pdf', 'README.txt']:
        p = app_root / fname
        if p.exists():
            zf.write(p, f'wildtag_validate/{fname}')

    # Add validation folder
    print('  Adding validation images...')
    for f in val_dir.rglob('*'):
        if f.is_file():
            rel = f.relative_to(project)
            zf.write(f, f'wildtag_validate/{rel}')

    # Add a custom launcher that uses validate_env not wildtag_env
    launcher = '@echo off\ncd /d \"%%~dp0\"\nvalidate_env\\Scripts\\python.exe wildtag.py\n'
    zf.writestr('wildtag_validate/wildtag.bat', launcher)

print(f'  Done: {out_zip} ({out_zip.stat().st_size/1e6:.0f} MB)')
"

if errorlevel 1 (
    echo ERROR: Packaging failed.
    pause
    exit /b 1
)

echo.
echo Created: %ZIP_NAME%
echo Share this file with your collaborator.
echo They unzip it and double-click wildtag.bat to start validating.
echo.
pause
