@echo off
REM ============================================================================
REM  build_validate_exe.bat
REM  Builds the standalone, validate-only wildtag app: dist\wildtag_validate.exe
REM  This is the single file you send a volunteer ONCE. After that they only
REM  receive small image-only zips (prepared from the Distribute tab).
REM
REM  IMPORTANT: pause Dropbox syncing before running this, or you may hit
REM  "the process cannot access the file" errors mid-build.
REM ============================================================================
cd /d "%~dp0"

REM Pick a Python to build with: prefer the light validate_env, else wildtag_env
set "PYEXE="
if exist "validate_env\python.exe"          set "PYEXE=validate_env\python.exe"
if not defined PYEXE if exist "wildtag_env\python.exe" set "PYEXE=wildtag_env\python.exe"

if not defined PYEXE (
    echo.
    echo ERROR: could not find validate_env\python.exe or wildtag_env\python.exe
    echo Build one first ^(setup_validate_env.bat^) and try again.
    echo.
    pause
    exit /b 1
)

echo Using %PYEXE%
echo Installing / updating PyInstaller...
"%PYEXE%" -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: could not install PyInstaller.
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
