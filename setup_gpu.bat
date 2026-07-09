@echo off
:: setup_gpu.bat
:: Installs GPU-enabled PyTorch into wildtag_env for NVIDIA GPU users.
:: Only run this if you have an NVIDIA GPU.
:: Requires internet connection.
cd /d "%~dp0"
echo ============================================
echo  wildtag.ai - GPU Setup (NVIDIA only)
echo ============================================
echo.
echo This will install GPU-enabled PyTorch into wildtag_env.
echo Only proceed if you have an NVIDIA GPU.
echo Requires an internet connection.
echo.
pause
if not exist "wildtag_env\python.exe" (
    echo ERROR: wildtag_env not found.
    pause
    exit /b 1
)
echo.
echo Installing GPU PyTorch (CUDA 11.8)...
echo This may take several minutes...
echo.
wildtag_env\python.exe -m pip install torch torchvision ^
    --upgrade --force-reinstall ^
    --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 (
    echo.
    echo ERROR: PyTorch install failed. Check your internet connection and try again.
    pause
    exit /b 1
)
echo.
echo Verifying CUDA availability...
wildtag_env\python.exe -c "import torch, sys; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'); sys.exit(0 if torch.cuda.is_available() else 1)"
if errorlevel 1 (
    echo.
    echo WARNING: PyTorch installed, but CUDA is still not available on this GPU.
    echo This usually means the NVIDIA driver needs updating, or, on laptops with
    echo NVIDIA Optimus, that the NVIDIA GPU is not the active processor. Check
    echo NVIDIA Control Panel and set the global default graphics processor to
    echo the NVIDIA GPU, update the driver from nvidia.com/drivers, then run
    echo this script again.
) else (
    echo.
    echo Done. Restart wildtag.ai - the GPU option should now appear.
)
echo.
pause
echo.
echo Installing tkinterweb for in-app map rendering...
wildtag_env\python.exe -m pip install tkinterweb --quiet
if errorlevel 1 (
    echo WARNING: tkinterweb install failed. Map tab may not work.
) else (
    echo Done.
)
pause
