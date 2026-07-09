"""
wt_models/env_utils.py
======================
Utilities for finding and using the wildtag bundled Python environment.

wildtag.py itself runs in the user's system Python (just needs tkinter).
Model inference runs in wildtag_env/ which has PyTorch, SpeciesNet etc.

This module finds the right Python executable for each context.
"""

import sys
import platform
from pathlib import Path

SYSTEM = platform.system().lower()


def bundled_python() -> Path:
    """
    Return the path to Python inside wildtag_env/, or None if not present.
    """
    root = Path(__file__).parent.parent
    if SYSTEM == "windows":
        candidate = root / "wildtag_env" / "python.exe"
    else:
        candidate = root / "wildtag_env" / "bin" / "python"
    return candidate if candidate.exists() else None


def inference_python() -> Path:
    """
    Return the best Python for running model inference:
    1. wildtag_env/ if present (preferred - fully isolated)
    2. Current Python as fallback (requires manual pip installs)
    """
    bp = bundled_python()
    if bp:
        return bp
    return Path(sys.executable)


def has_bundled_env() -> bool:
    return bundled_python() is not None


def env_status() -> str:
    """Human-readable status string for the Setup pane."""
    bp = bundled_python()
    if bp:
        return f"Bundled environment found: {bp.parent}"
    return "No bundled environment - using system Python"
