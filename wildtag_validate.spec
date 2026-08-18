# wildtag_validate.spec
# =====================
# PyInstaller spec for the standalone, validate-only wildtag build.
# Produces a single file: dist\wildtag_validate.exe
#
# Build it with:
#     validate_env\python.exe -m PyInstaller --noconfirm --clean wildtag_validate.spec
# or just run build_validate_exe.bat
#
# Why this stays small: the frozen exe has no wildtag_env beside it, so
# wildtag.py auto-selects validate-only mode at runtime and never imports the
# detection/classification stack (torch, onnxruntime, opencv, wt_models). We
# exclude that whole stack from the build so the exe is only tkinter + Pillow.

block_cipher = None

a = Analysis(
    ['wildtag.py'],
    pathex=[],
    binaries=[
        # Conda keeps sqlite3.dll in Library\bin, so PyInstaller bundles
        # _sqlite3.pyd but misses the DLL it depends on. Ship it explicitly.
        ('wildtag_env/Library/bin/sqlite3.dll', '.'),
    ],
    datas=[('wildtag.ico', '.')],          # so the app can set its window icon
    hiddenimports=['PIL._tkinter_finder'],  # helps ImageTk find tkinter
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision',
        'onnxruntime', 'onnx',
        'cv2', 'opencv-python',
        'wt_models',
        'numpy', 'scipy', 'pandas', 'matplotlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wildtag_validate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # windowed app, no console box
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='wildtag.ico',
)
