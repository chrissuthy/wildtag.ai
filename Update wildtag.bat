@echo off
cd /d "%~dp0"

if not exist "%~dp0wildtag.py" (
    echo PROBLEM: wildtag.py is not in this folder.
    echo Put the new wildtag.py here, next to this file, then run again.
    echo.
    pause
    exit /b 1
)

echo Updating wildtag in each validation folder...
echo.
set /a count=0
for /d %%D in (*_validation) do (
    copy /y "%~dp0wildtag.py" "%%~fD\wildtag.py" >nul
    if errorlevel 1 (
        echo   FAILED  %%D
    ) else (
        echo   updated %%D
        set /a count+=1
    )
)
echo.
echo Done. Updated %count% folder(s).
echo Now open each batch as usual - it will fix itself automatically.
echo.
pause
