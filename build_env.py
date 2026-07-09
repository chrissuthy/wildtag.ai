"""
build_env.py
============
Developer script - run this once to build the wildtag bundled environment.

Creates wildtag_env/ containing Python + PyTorch + all model dependencies.
Users never run this - only the project lead runs it once per release.

Requirements: internet connection, ~4 GB free disk space, ~15 minutes.
"""

import os
import sys
import platform
import subprocess
import urllib.request
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
ENV_DIR = ROOT / "wildtag_env"
SYSTEM = platform.system().lower()   # 'windows', 'darwin', 'linux'
ARCH   = platform.machine().lower()  # 'amd64', 'x86_64', 'arm64', 'aarch64'


# ── Micromamba download URLs ───────────────────────────────────────────────────
# These are the correct URLs from the official micromamba distribution
# Windows uses a zip, Mac/Linux use a tar.bz2

def _mamba_url() -> tuple[str, str]:
    """Return (url, format) for this platform."""
    # All platforms use tar.bz2 from micro.mamba.pm
    if SYSTEM == "windows":
        return (
            "https://micro.mamba.pm/api/micromamba/win-64/latest",
            "tarbz2"
        )
    elif SYSTEM == "darwin":
        if "arm" in ARCH:
            return (
                "https://micro.mamba.pm/api/micromamba/osx-arm64/latest",
                "tarbz2"
            )
        else:
            return (
                "https://micro.mamba.pm/api/micromamba/osx-64/latest",
                "tarbz2"
            )
    else:  # linux
        if "aarch" in ARCH or "arm" in ARCH:
            return (
                "https://micro.mamba.pm/api/micromamba/linux-aarch64/latest",
                "tarbz2"
            )
        else:
            return (
                "https://micro.mamba.pm/api/micromamba/linux-64/latest",
                "tarbz2"
            )


MAMBA_EXE = ROOT / ("micromamba.exe" if SYSTEM == "windows" else "micromamba")


# ── Download micromamba ────────────────────────────────────────────────────────

def download_micromamba():
    url, fmt = _mamba_url()
    tmp = ROOT / "micromamba_download.tar.bz2"

    print(f"Downloading micromamba ({SYSTEM} {ARCH})...")
    print(f"  URL: {url}")

    def _progress(count, block, total):
        if total > 0:
            pct = min(count * block / total * 100, 100)
            print(f"\r  {pct:.0f}%", end="", flush=True)

    urllib.request.urlretrieve(url, tmp, reporthook=_progress)
    print()

    print("Extracting micromamba...")

    import tarfile
    with tarfile.open(tmp, "r:bz2") as t:
        # Windows: Library/bin/micromamba.exe
        # Mac/Linux: bin/micromamba
        for member in t.getmembers():
            if member.name.endswith("micromamba.exe") or \
               member.name.endswith("bin/micromamba"):
                f = t.extractfile(member)
                MAMBA_EXE.write_bytes(f.read())
                break

    tmp.unlink()

    if SYSTEM != "windows":
        MAMBA_EXE.chmod(0o755)

    # Verify it's a real executable
    if not MAMBA_EXE.exists() or MAMBA_EXE.stat().st_size < 1_000_000:
        sys.exit(
            f"ERROR: micromamba download failed or is too small "
            f"({MAMBA_EXE.stat().st_size if MAMBA_EXE.exists() else 0} bytes). "
            f"Please download manually from https://mamba.readthedocs.io")

    print(f"  micromamba ready ({MAMBA_EXE.stat().st_size // 1_000_000} MB)")


# ── Build environment ──────────────────────────────────────────────────────────

def build_environment():
    env_yml = ROOT / "environment.yml"
    if not env_yml.exists():
        sys.exit("environment.yml not found.")

    print(f"\nBuilding wildtag_env/ in {ENV_DIR}")
    print("This downloads ~3-4 GB and takes 5-20 minutes.\n")

    # micromamba needs a root prefix
    mamba_root = ROOT / "micromamba_root"
    mamba_root.mkdir(exist_ok=True)

    cmd = [
        str(MAMBA_EXE),
        "env", "create",
        "--file",        str(env_yml),
        "--prefix",      str(ENV_DIR),
        "--yes",
        "--no-shortcuts",
        "-r",            str(mamba_root),
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("\nEnvironment build failed. Check the output above for errors.")

    print(f"\nEnvironment built: {ENV_DIR}")


# ── Find Python in env ─────────────────────────────────────────────────────────

def python_in_env() -> Path:
    if SYSTEM == "windows":
        return ENV_DIR / "python.exe"
    else:
        return ENV_DIR / "bin" / "python"


# ── Install pip packages that need special handling ────────────────────────────

def install_pip_extras():
    """Install pip packages in correct order, protecting MKL version."""
    py = python_in_env()
    if not py.exists():
        sys.exit(f"Python not found in environment: {py}")

    def pip(args, label):
        print(f"  Installing {label}...")
        result = subprocess.run(
            [str(py), "-m", "pip", "install"] + args +
            ["--no-warn-script-location", "-q"],
            capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {label}: OK")
        else:
            print(f"  WARNING: {label} had issues:")
            print(f"    {result.stderr[-400:]}")

    print("\nInstalling pip packages...")

    # 1. timm - no conflicts
    pip(["timm"], "timm")

    # 2. megadetector with --no-deps to prevent MKL downgrade
    pip(["megadetector", "--no-deps"], "megadetector (no-deps)")

    # 3. megadetector runtime deps (excluding mkl/torch which are already installed)
    pip(["ultralytics-yolov5"], "ultralytics-yolov5")
    pip(["jsonpickle", "clipboard", "send2trash", "pytest",
         "dill", "fastquadtree", "ruff", "scikit-learn"],
        "megadetector utilities")

    # 4. speciesnet
    pip(["speciesnet"], "speciesnet")

    # 5. Re-pin MKL to exact version pytorch 2.3 needs
    print("  Re-pinning MKL to 2021.4.0...")
    result = subprocess.run(
        [str(py), "-m", "pip", "install",
         "mkl==2021.4.0", "--force-reinstall", "--no-deps",
         "--no-warn-script-location", "-q"],
        capture_output=True, text=True)
    if result.returncode == 0:
        print("  MKL pinned: OK")
    else:
        print(f"  WARNING: MKL pin failed: {result.stderr[-200:]}")


# ── Download model weights ─────────────────────────────────────────────────────

def download_model_weights():
    """Download all model weights into models/ so users never need internet."""
    import urllib.request
    import json

    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)

    downloads = [
        {
            "id":       "megadetector-v5a",
            "name":     "MegaDetector v5a",
            "url":      "https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt",
            "filename": "md_v5a.pt",
            "size_mb":  280,
        },
        {
            "id":       "deepfaune-v1.3",
            "name":     "DeepFaune v1.3",
            "url":      "https://pbil.univ-lyon1.fr/software/download/deepfaune/v1.3/deepfaune-vit_large_patch14_dinov2.lvd142m.v3.pt",
            "filename": "deepfaune_v1.3.pt",
            "size_mb":  1100,
        },
    ]

    for m in downloads:
        dest_dir  = models_dir / m["id"]
        dest_dir.mkdir(exist_ok=True)
        dest_file = dest_dir / m["filename"]
        marker    = dest_dir / "ready.json"

        if marker.exists():
            print(f"  {m['name']}: already downloaded, skipping.")
            continue

        print(f"\nDownloading {m['name']} (~{m['size_mb']} MB)...")
        print(f"  {m['url']}")

        def _progress(count, block, total):
            if total > 0:
                done_mb  = min(count * block, total) / 1_000_000
                total_mb = total / 1_000_000
                pct      = min(done_mb / total_mb * 100, 100)
                print(f"\r  {done_mb:.0f} / {total_mb:.0f} MB  ({pct:.0f}%)",
                      end="", flush=True)

        urllib.request.urlretrieve(m["url"], dest_file, reporthook=_progress)
        print()

        with open(marker, "w") as f:
            json.dump({"id": m["id"], "name": m["name"]}, f)

        print(f"  {m['name']}: done.")


    # SpeciesNet - download via kagglehub (same mechanism used at runtime)
    sn_dir    = models_dir / "speciesnet-global"
    sn_marker = sn_dir / "ready.json"
    sn_dir.mkdir(exist_ok=True)

    if not sn_marker.exists():
        print("\nDownloading SpeciesNet weights via kagglehub (~500 MB)...")
        py = python_in_env()
        result = subprocess.run(
            [str(py), "-c",
             "import kagglehub; "
             "path = kagglehub.model_download('google/speciesnet/pyTorch/v4.0.3a'); "
             "print('OK:' + path)"],
            capture_output=True, text=True, timeout=900)

        if "OK:" in result.stdout:
            cached_path = result.stdout.strip().split("OK:")[1]
            print(f"  SpeciesNet downloaded to: {cached_path}")
            with open(sn_marker, "w") as f:
                json.dump({"id": "speciesnet-global",
                           "name": "SpeciesNet",
                           "cached_path": cached_path}, f)
        else:
            print("  WARNING: SpeciesNet download failed.")
            print(f"  {result.stderr[-300:]}")
            with open(sn_marker, "w") as f:
                json.dump({"id": "speciesnet-global",
                           "name": "SpeciesNet", "failed": True}, f)
    else:
        print("  SpeciesNet: already downloaded, skipping.")

    print("\nAll model weights downloaded.")


# ── Write launcher scripts ─────────────────────────────────────────────────────

def write_launchers():
    bat = ROOT / "launch_wildtag.bat"
    bat.write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "echo Starting wildtag.ai...\r\n"
        "wildtag_env\\python.exe wildtag.py\r\n"
        "if errorlevel 1 (\r\n"
        "    echo.\r\n"
        "    echo An error occurred. Press any key to close.\r\n"
        "    pause >nul\r\n"
        ")\r\n"
    )

    # Mac .command
    command = ROOT / "launch_wildtag.command"
    command.write_text(
        "#!/bin/bash\n"
        'cd "$(dirname "$0")"\n'
        "echo Starting wildtag.ai...\n"
        "./wildtag_env/bin/python wildtag.py\n"
    )
    command.chmod(0o755)

    # Linux .sh
    sh = ROOT / "launch_wildtag.sh"
    sh.write_text(
        "#!/bin/bash\n"
        'cd "$(dirname "$0")"\n'
        "echo Starting wildtag.ai...\n"
        "./wildtag_env/bin/python wildtag.py\n"
    )
    sh.chmod(0o755)

    print("\nLauncher scripts written:")
    print(f"  Windows: {bat.name}")
    print(f"  Mac:     {command.name}")
    print(f"  Linux:   {sh.name}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("wildtag.ai - environment builder")
    print("=" * 60)
    print(f"Platform: {SYSTEM} {ARCH}")
    print(f"Output:   {ENV_DIR}\n")

    # Download micromamba if needed
    if not MAMBA_EXE.exists():
        download_micromamba()
    else:
        print(f"micromamba already present: {MAMBA_EXE}")

    # Build environment
    if ENV_DIR.exists():
        ans = input(
            "\nwildtag_env/ already exists. "
            "Rebuild from scratch? [y/N]: ").strip().lower()
        if ans == "y":
            print("Removing existing environment...")
            shutil.rmtree(ENV_DIR)
            build_environment()
        else:
            print("Keeping existing environment.")
    else:
        build_environment()

    # Install pip extras
    install_pip_extras()

    # Download model weights
    print("\n" + "=" * 60)
    print("Downloading model weights...")
    print("=" * 60)
    download_model_weights()

    # Write launchers
    write_launchers()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("\nTo start wildtag, double-click:")
    if SYSTEM == "windows":
        print("  launch_wildtag.bat")
    elif SYSTEM == "darwin":
        print("  launch_wildtag.command")
    else:
        print("  launch_wildtag.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()
