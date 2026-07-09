"""
wt_models/downloader.py
=======================
Handles model weight downloads, caching, pip dependency installation,
and integrity verification.

All models are cached in a `models/` folder next to wildtag.py.
Downloads happen automatically when a model is first used.
"""

import os
import sys
import json
import hashlib
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Optional


def models_dir() -> Path:
    """Return the models/ directory, creating it if needed."""
    d = Path(__file__).parent.parent / "models"
    d.mkdir(exist_ok=True)
    return d


def model_dir(model_id: str) -> Path:
    """Return the directory for a specific model."""
    d = models_dir() / model_id
    d.mkdir(exist_ok=True)
    return d


def is_ready(model_id: str) -> bool:
    """
    Return True if the model is fully downloaded and ready to use.
    Checks for the weights file and a ready.json marker.
    """
    marker = model_dir(model_id) / "ready.json"
    return marker.exists()


def mark_ready(model_id: str, meta: dict):
    """Write a ready.json marker after successful download."""
    marker = model_dir(model_id) / "ready.json"
    with open(marker, "w") as f:
        json.dump(meta, f, indent=2)


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_pip_deps(
    deps: list[str],
    log: Callable[[str], None] = print
):
    """
    Install any missing pip dependencies.
    Uses the same Python that is running wildtag.
    """
    for dep in deps:
        pkg = dep.split("==")[0].split(">=")[0].split("[")[0]
        try:
            __import__(pkg.replace("-", "_"))
            log(f"  {pkg}: already installed")
        except ImportError:
            log(f"  Installing {dep}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install",
                 dep, "--break-system-packages", "-q"],
                capture_output=True, text=True)
            if result.returncode == 0:
                log(f"  {dep}: installed successfully")
            else:
                log(f"  ERROR installing {dep}: {result.stderr[:200]}")
                raise RuntimeError(
                    f"Could not install {dep}. "
                    f"Please run: pip install {dep}")


def download_weights(
    model_id: str,
    url: str,
    filename: str,
    expected_size_mb: int,
    checksum: Optional[str],
    log:      Callable[[str], None] = print,
    progress: Callable[[int, int], None] = lambda done, total: None,
) -> Path:
    """
    Download model weights to models/<model_id>/<filename>.
    Shows progress via the progress callback (bytes_done, bytes_total).
    Returns the path to the downloaded file.
    """
    dest = model_dir(model_id) / filename

    if dest.exists():
        if checksum:
            log(f"  Verifying {filename}...")
            if sha256_file(dest) == checksum:
                log(f"  {filename}: verified OK")
                return dest
            else:
                log(f"  Checksum mismatch - re-downloading {filename}")
                dest.unlink()
        else:
            log(f"  {filename}: already downloaded")
            return dest

    log(f"  Downloading {filename} (~{expected_size_mb} MB)...")

    def _reporthook(count, block_size, total_size):
        done = min(count * block_size, total_size)
        progress(done, total_size)

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    progress(dest.stat().st_size, dest.stat().st_size)

    if checksum:
        log(f"  Verifying {filename}...")
        actual = sha256_file(dest)
        if actual != checksum:
            dest.unlink()
            raise RuntimeError(
                f"Checksum verification failed for {filename}. "
                f"Expected {checksum[:12]}... got {actual[:12]}...")
        log(f"  {filename}: verified OK")

    log(f"  {filename}: download complete")
    return dest


def ensure_model(
    model_id:  str,
    log:       Callable[[str], None] = print,
    progress:  Callable[[int, int], None] = lambda d, t: None,
) -> Path:
    """
    Ensure a model is ready to use.
    If weights were pre-downloaded by build_env.py, just installs pip deps.
    Otherwise downloads weights on demand (fallback for development use).
    Returns the model directory.
    """
    from wt_models.registry import get_model

    if is_ready(model_id):
        return model_dir(model_id)

    meta = get_model(model_id)
    log(f"\nSetting up {meta['name']}...")

    # Install pip dependencies
    if meta.get("pip_deps"):
        log("  Checking dependencies...")
        ensure_pip_deps(meta["pip_deps"], log)

    # Download weights only if not already present
    if meta.get("weights_url") and meta.get("weights_file"):
        weights_path = model_dir(model_id) / meta["weights_file"]
        if weights_path.exists():
            log(f"  {meta['weights_file']}: found.")
        else:
            log(f"  Weights not found locally. Downloading...")
            log(f"  Note: weights should have been included with the app.")
            log(f"  Downloading {meta['weights_file']} "
                f"(~{meta['weights_size']} MB)...")
            download_weights(
                model_id         = model_id,
                url              = meta["weights_url"],
                filename         = meta["weights_file"],
                expected_size_mb = meta["weights_size"],
                checksum         = meta.get("checksum"),
                log              = log,
                progress         = progress,
            )

    # Download classes file if separate
    if meta.get("classes_url"):
        classes_file = model_dir(model_id) / "classes.txt"
        if not classes_file.exists():
            log("  Downloading classes list...")
            urllib.request.urlretrieve(meta["classes_url"], classes_file)

    mark_ready(model_id, {
        "id":      model_id,
        "name":    meta["name"],
        "version": meta.get("version", ""),
    })
    log(f"  {meta['name']}: ready")
    return model_dir(model_id)
