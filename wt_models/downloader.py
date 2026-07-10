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

    _download_file(url, dest, log, progress, expected_size_mb)
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


def _cache_bundle_dir(cache_bundle: dict) -> Path:
    """Where a cache bundle should be extracted to. Driven by the registry
    entry's 'extract_to' (relative to models/), so it matches exactly where
    the runner looks. For SpeciesNet this is
    models/speciesnet-global/kagglehub_cache, the path _runner.py points
    KAGGLEHUB_CACHE at."""
    rel = cache_bundle.get("extract_to", "")
    return models_dir() / rel if rel else models_dir()


def cache_bundle_present(cache_bundle: dict) -> bool:
    """True if the extracted cache bundle already exists (probe path present
    under the bundle's extract dir)."""
    base  = _cache_bundle_dir(cache_bundle)
    probe = cache_bundle.get("probe", "")
    return (base / probe).exists() if probe else base.exists()


def _parse_hf_url(url: str):
    """If url is a Hugging Face resolve URL, return (repo_id, filename) so we
    can use huggingface_hub's resumable, retrying downloader. Otherwise None.
    Expected form:
      https://huggingface.co/<user>/<repo>/resolve/<rev>/<path/to/file>
    """
    import re
    m = re.match(
        r"https?://huggingface\.co/([^/]+/[^/]+)/resolve/([^/]+)/(.+)$", url)
    if not m:
        return None
    repo_id, revision, filename = m.group(1), m.group(2), m.group(3)
    return repo_id, revision, filename


def _download_file(url: str, dest: Path,
                   log: Callable[[str], None],
                   progress: Callable[[int, int], None],
                   expected_size_mb: int) -> None:
    """Download url -> dest. Prefer huggingface_hub for HF URLs (resumable,
    retrying, integrity-checked); fall back to urllib otherwise."""
    hf = _parse_hf_url(url)
    if hf:
        repo_id, revision, filename = hf
        try:
            from huggingface_hub import hf_hub_download
            log("  Downloading via Hugging Face (resumable)...")
            # hf_hub_download resumes partial downloads and retries on
            # transient network errors automatically. It downloads into its
            # own cache, then we copy the resolved file to dest.
            cached = hf_hub_download(
                repo_id=repo_id, filename=filename, revision=revision)
            import shutil
            shutil.copy(cached, dest)
            progress(dest.stat().st_size, dest.stat().st_size)
            return
        except Exception as e:
            log(f"  Hugging Face download unavailable ({e}); "
                f"falling back to direct download.")

    # Fallback: plain urllib (no resume, but works for any host)
    def _reporthook(count, block_size, total_size):
        if total_size > 0:
            progress(min(count * block_size, total_size), total_size)
        else:
            progress(count * block_size, expected_size_mb * 1024 * 1024)
    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)


def download_cache_bundle(
    model_id:     str,
    cache_bundle: dict,
    log:      Callable[[str], None] = print,
    progress: Callable[[int, int], None] = lambda done, total: None,
) -> None:
    """
    Download a zipped model-cache bundle (e.g. SpeciesNet's kagglehub cache)
    and extract it to where the runner expects it
    (models/speciesnet-global/kagglehub_cache), so SpeciesNet finds its
    models locally with no Kaggle contact. Skips if already present.

    The zip is expected to contain a top-level `kagglehub/` folder.
    """
    import zipfile, tempfile

    if cache_bundle_present(cache_bundle):
        log("  SpeciesNet model files already present.")
        return

    url              = cache_bundle["url"]
    expected_size_mb = cache_bundle.get("size_mb", 0)
    extract_to       = _cache_bundle_dir(cache_bundle)
    extract_to.mkdir(parents=True, exist_ok=True)

    log(f"  Downloading SpeciesNet model files (~{expected_size_mb} MB)...")
    log("  This is a one-time download; it's reused on future runs.")

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="speciesnet_")
    os.close(tmp_fd)
    tmp_zip = Path(tmp_path)

    try:
        _download_file(url, tmp_zip, log, progress, expected_size_mb)

        log("  Extracting model files...")
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(extract_to)

        # The hosted zip has models/ at its root, so it extracts straight to
        # <extract_to>/models/... which is exactly where the runner's
        # KAGGLEHUB_CACHE points. As a safety net, if a future zip ever has
        # an extra kagglehub/ wrapper, lift its contents up one level.
        wrapper = extract_to / "kagglehub"
        if wrapper.is_dir() and not (extract_to / "models").exists():
            import shutil
            for child in wrapper.iterdir():
                dest = extract_to / child.name
                if dest.exists():
                    shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
                shutil.move(str(child), str(dest))
            try:
                wrapper.rmdir()
            except OSError:
                pass

        if not cache_bundle_present(cache_bundle):
            raise RuntimeError(
                "Download completed but the model files were not found "
                "where expected after extraction. The download may be "
                "corrupt; please try again.")
        log("  SpeciesNet model files ready.")
    finally:
        try:
            tmp_zip.unlink()
        except OSError:
            pass


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

    meta = get_model(model_id)

    # Cache-bundle models (e.g. SpeciesNet) keep their real model files in a
    # library cache (kagglehub) outside models/, so the ready.json marker
    # alone isn't enough — the cache itself could be missing even if the
    # marker exists. Check the actual cache presence for these.
    cache_bundle = meta.get("cache_bundle")
    if cache_bundle:
        # Still install pip deps (idempotent, fast if already there)
        if meta.get("pip_deps"):
            log(f"\nSetting up {meta['name']}...")
            log("  Checking dependencies...")
            ensure_pip_deps(meta["pip_deps"], log)
        if not cache_bundle_present(cache_bundle):
            download_cache_bundle(
                model_id     = model_id,
                cache_bundle = cache_bundle,
                log          = log,
                progress     = progress,
            )
        else:
            log(f"  {meta['name']}: model files present.")
        mark_ready(model_id, {"id": model_id, "name": meta["name"]})
        return model_dir(model_id)

    if is_ready(model_id):
        return model_dir(model_id)

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
