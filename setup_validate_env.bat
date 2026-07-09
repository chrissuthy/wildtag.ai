@echo off
:: setup_validate_env.bat
:: Creates a minimal validate_env for volunteer zips using Python embeddable.
:: Run this once on the wildtag.ai machine to build the volunteer Python env.
:: Output: validate_env\ (~40MB, includes Tcl/Tk for tkinter) — included in every volunteer zip.

cd /d "%~dp0"

echo ============================================
echo  wildtag.ai - Building volunteer Python env
echo ============================================
echo.

if exist "validate_env" (
    echo validate_env already exists. Delete it first to rebuild.
    pause
    exit /b 0
)

:: Download Python 3.11 embeddable
echo Downloading Python 3.11 embeddable...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile 'python_embed.zip'"

if not exist "python_embed.zip" (
    echo ERROR: Download failed. Check your internet connection.
    pause
    exit /b 1
)

:: Extract
echo Extracting...
mkdir validate_env
powershell -Command "Expand-Archive -Path 'python_embed.zip' -DestinationPath 'validate_env' -Force"
del python_embed.zip

:: Enable pip in embeddable Python by uncommenting import site in pth file,
:: and add Lib to the search path so the tkinter package (copied in below)
:: can actually be found
echo Enabling pip...
powershell -Command "(Get-Content 'validate_env\python311._pth') -replace '#import site','import site' | Set-Content 'validate_env\python311._pth'"
powershell -Command "Add-Content 'validate_env\python311._pth' 'Lib'"

:: Download get-pip.py
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'validate_env\get-pip.py'"
validate_env\python.exe validate_env\get-pip.py --no-warn-script-location --no-compile
del /q "validate_env\get-pip.py"

:: Install only Pillow (tkinter itself is added separately below, the
:: embeddable package does not include Tcl/Tk at all)
echo Installing Pillow...
validate_env\python.exe -m pip install Pillow --no-warn-script-location --quiet --no-compile

:: ── Add Tcl/Tk (tkinter) ─────────────────────────────────────────
:: The embeddable package deliberately leaves out Tcl/Tk. Pull the exact
:: same version's official tcltk.msi component (matches the embeddable
:: zip above, so _tkinter.pyd is built against the same Python build)
:: and copy the pieces into validate_env by hand.
echo.
echo Adding Tcl/Tk (tkinter)...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/amd64/tcltk.msi' -OutFile 'tcltk.msi'"

if not exist "tcltk.msi" (
    echo ERROR: tcltk.msi download failed. validate_env will not have tkinter.
    pause
    exit /b 1
)

:: An "administrative install" just copies the msi's files out, it does
:: not register or install anything on this machine
msiexec /a tcltk.msi /qn TARGETDIR="%CD%\tcltk_extract"

if exist "tcltk_extract\Lib\tkinter" (
    xcopy /e /i /y /q "tcltk_extract\Lib\tkinter" "validate_env\Lib\tkinter" >nul
) else (
    echo WARNING: tkinter package not found in tcltk.msi extraction.
)

if exist "tcltk_extract\tcl" (
    xcopy /e /i /y /q "tcltk_extract\tcl" "validate_env\tcl" >nul
    :: tzdata is the full IANA timezone database, several hundred small
    :: files. Only used by Tcl's own "clock" command with timezone
    :: conversions, which wildtag.py never calls. Removing it cuts the
    :: file count a lot and speeds up extraction, with no functional loss.
    if exist "validate_env\tcl\tcl8.6\tzdata" rmdir /s /q "validate_env\tcl\tcl8.6\tzdata"
) else (
    echo WARNING: tcl library folder not found in tcltk.msi extraction.
)

for /r "tcltk_extract" %%F in (_tkinter.pyd tcl86t.dll tk86t.dll zlib1.dll) do (
    if exist "%%F" copy /y "%%F" "validate_env\" >nul
)

rmdir /s /q tcltk_extract 2>nul
timeout /t 2 /nobreak >nul
if exist "tcltk_extract" rmdir /s /q tcltk_extract 2>nul
del tcltk.msi 2>nul

:: pip, setuptools, wheel, and packaging were only needed to install
:: Pillow just now. The volunteer never runs pip again, and each of these
:: bundles its own vendored copies of a dozen-plus other packages, so
:: together they're likely the single biggest contributor to file count,
:: bigger than tzdata. Remove them entirely.
echo Removing build-time-only packages (pip, setuptools, wheel)...
for %%P in (pip setuptools wheel packaging) do (
    if exist "validate_env\Lib\site-packages\%%P" rmdir /s /q "validate_env\Lib\site-packages\%%P"
)
for /d %%D in ("validate_env\Lib\site-packages\pip-*.dist-info" "validate_env\Lib\site-packages\setuptools-*.dist-info" "validate_env\Lib\site-packages\wheel-*.dist-info" "validate_env\Lib\site-packages\packaging-*.dist-info") do (
    if exist "%%D" rmdir /s /q "%%D"
)
del /q "validate_env\Scripts\pip*" 2>nul
del /q "validate_env\Scripts\wheel*" 2>nul

:: Catch-all: remove any __pycache__ folders left behind anywhere in
:: validate_env. Python regenerates these lazily and near-instantly on
:: first run, they add file count for zero benefit in a shipped zip.
for /d /r "validate_env" %%D in (__pycache__) do (
    if exist "%%D" rmdir /s /q "%%D"
)

echo.
echo Done. validate_env is ready.
set TCL_LIBRARY=%CD%\validate_env\tcl\tcl8.6
set TK_LIBRARY=%CD%\validate_env\tcl\tk8.6
validate_env\python.exe -c "from PIL import Image; import tkinter; print('OK - Pillow and tkinter working')"
echo.
pause
