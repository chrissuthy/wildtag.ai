@echo off
REM ============================================================================
REM  build_validate_exe.bat
REM  Builds the standalone, validate-only wildtag app: dist\wildtag_validate.exe
REM  This is the single file you send a volunteer ONCE. After that they only
REM  receive small image-only zips (prepared from the Distribute tab).
REM
REM  IMPORTANT: pause Dropbox syncing before running this, or you may hit
REM  "the process cannot access the file" errors mid-build.
REM
REM  We build with an environment that has pip. validate_env is a stripped
REM  runtime with NO pip, so it cannot build; wildtag_env is used instead.
REM  The spec excludes the heavy ML libraries, so the exe stays small no
REM  matter which env builds it.
REM ============================================================================
cd /d "%~dp0"

REM Put the conda env's DLLs on PATH so PyInstaller can resolve and bundle the
REM runtime libraries conda keeps in Library\bin (tcl/tk, sqlite, freetype,
REM jpeg, ssl, etc.). Without this the exe builds but crashes at startup on a
REM missing DLL.
set "PATH=%~dp0wildtag_env\Library\bin;%~dp0wildtag_env\DLLs;%~dp0wildtag_env;%PATH%"

REM Pick a Python that actually has pip. Prefer wildtag_env; fall back to
REM validate_env only if it somehow has pip too.
set "PYEXE="
if exist "wildtag_env\python.exe" (
    wildtag_env\python.exe -m pip --version >nul 2>&1 && set "PYEXE=wildtag_env\python.exe"
)
if not defined PYEXE if exist "validate_env\python.exe" (
    validate_env\python.exe -m pip --version >nul 2>&1 && set "PYEXE=validate_env\python.exe"
)

if not defined PYEXE (
    echo.
    echo ERROR: could not find a Python with pip.
    echo   - wildtag_env\python.exe is needed ^(it has pip^).
    echo   - validate_env is a minimal runtime with no pip and cannot build.
    echo If wildtag_env is missing, build it first, then re-run this.
    echo.
    pause
    exit /b 1
)

echo Using %PYEXE%
echo Installing / updating PyInstaller...
"%PYEXE%" -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: could not install PyInstaller. See the pip messages above.
    echo ^(If it mentions SSL or a proxy, you may be behind a VPN blocking PyPI.^)
    pause
    exit /b 1
)

echo.
echo Building wildtag_validate.exe ...
"%PYEXE%" -m PyInstaller --noconfirm --clean wildtag_validate.spec
if errorlevel 1 (
    echo.
    echo BUILD FAILED. See the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo  Done. Your validator is:  dist\wildtag_validate.exe
echo  Send that one file to each volunteer. They keep it and reuse it for every
echo  image-only package you send from the Distribute tab.
echo ============================================================================
pause
