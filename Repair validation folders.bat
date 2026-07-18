@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ==============================================================
echo   wildtag - repair validation folders
echo ==============================================================
echo.
echo This checks every validation folder in:
echo   %ROOT%
echo and removes leftover entries for images that are not there.
echo Your images and any work you have already done are kept.
echo.

if not exist "%ROOT%fix_manifests.py" (
    echo PROBLEM: "fix_manifests.py" is missing.
    echo Save BOTH files into this same folder, then run again.
    echo.
    pause
    exit /b 1
)

rem Find a validation folder that carries the bundled Python.
set "SUB="
for /d %%D in ("*") do (
    if not defined SUB if exist "%%~fD\validate_env\python.exe" set "SUB=%%~fD"
    if not defined SUB if exist "%%~fD\validate_env\Scripts\python.exe" set "SUB=%%~fD"
)

if not defined SUB (
    echo PROBLEM: could not find the bundled Python.
    echo Put this file next to the ...validation folders and run again.
    echo.
    pause
    exit /b 1
)

echo Using the wildtag Python inside: !SUB!
echo Working, please wait...
echo.

rem Launch Python EXACTLY the way the wildtag app does: step into the folder
rem that owns validate_env and call it with a relative path. Launching it any
rem other way is what triggered "this app can't run on your PC".
set "PYENV=!SUB!\validate_env"
set "TCL_LIBRARY=!PYENV!\tcl\tcl8.6"
set "TK_LIBRARY=!PYENV!\tcl\tk8.6"

cd /d "!SUB!"
if exist "validate_env\python.exe" (
    "validate_env\python.exe" "%ROOT%fix_manifests.py" "%ROOT%" > "%ROOT%repair_log.txt" 2>&1
) else (
    "validate_env\Scripts\python.exe" "%ROOT%fix_manifests.py" "%ROOT%" > "%ROOT%repair_log.txt" 2>&1
)

cd /d "%ROOT%"
echo ---------------------------------------------------------------
type "%ROOT%repair_log.txt"
echo ---------------------------------------------------------------
echo.
echo A copy of these results was saved as repair_log.txt in this folder.
echo If images still show as not available, send that file back.
echo.
pause
