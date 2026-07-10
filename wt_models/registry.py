"""
wt_models/registry.py
=====================
The wildtag.ai Model Registry

Defines the catalogue of available models and their metadata.
This is the single source of truth for what models wildtag knows about.

To add a new model to wildtag:
  1. Add an entry to REGISTRY below
  2. Create wt_models/<model_id>/inference.py implementing load() and predict()
  3. That's it

The registry is intentionally kept as plain data - no magic, no frameworks.
"""

from pathlib import Path

# ── Registry ──────────────────────────────────────────────────────────────────
#
# Each entry describes one model. Fields:
#
#   id            Unique identifier, used as folder name under wt_models/
#   name          Human-readable name shown in UI
#   type          "detector" (finds animals) or "classifier" (identifies species)
#   regions       List of geographic regions this model covers
#   architecture  Neural network architecture (informational)
#   input_size    Image crop size in pixels fed to the classifier
#   classes_url   URL to download the classes/labels file
#   weights_url   URL to download model weights
#   weights_file  Local filename for weights (relative to model folder)
#   weights_size  Approximate download size in MB (shown to user)
#   checksum      SHA256 of weights file (None = skip verification)
#   license       Model license
#   citation      How to cite this model
#   pip_deps      List of pip packages required (installed automatically)
#   description   One-sentence description shown in UI

REGISTRY = [

    # ── Classification models ──────────────────────────────────────────────────
    # Each classifier bundles its own detector:
    #   DeepFaune v1.4   -> deepfaune_detector.pt (YOLOv8s, bundled, 22MB)
    #   SpeciesNet Global -> internal MegaDetector (bundled in kagglehub cache)

    {
        "id":           "deepfaune-v1.4",
        "name":         "DeepFaune v1.4 (Europe)",
        "type":         "classifier",
        "regions":      ["Europe"],
        "architecture": "ViT-Large DINOv2",
        "input_size":   224,
        "classes_url":  None,
        "weights_url":  (
            "https://pbil.univ-lyon1.fr/software/download/deepfaune/v1.4/"
            "deepfaune-vit_large_patch14_dinov2.lvd142m.v4.pt"
        ),
        "weights_file": "deepfaune_v1.4.pt",
        "weights_size": 1100,
        "checksum":     None,
        "license":      "CC-BY-NC-SA-4.0",
        "citation":     (
            "Rigoudy et al. (2023) The DeepFaune initiative: a collaborative "
            "effort towards the automatic identification of the European fauna "
            "in camera-trap images. European Journal of Wildlife Research."
        ),
        "pip_deps":     ["torch", "torchvision", "timm", "Pillow", "numpy", "ultralytics"],
        "description":  (
            "European wildlife classifier covering 38 species/groups. "
            "Excellent performance for UK and European mammals."
        ),
    },

    {
        "id":           "speciesnet-global",
        "name":         "SpeciesNet (Global)",
        "type":         "classifier",
        "regions":      ["Global"],
        "architecture": "EfficientNet-B7 + Geo ensemble",
        "input_size":   600,
        "classes_url":  None,
        "weights_url":  None,
        "weights_file": None,
        "weights_size": 500,
        "checksum":     None,
        "license":      "Apache-2.0",
        "citation":     (
            "Google (2024) SpeciesNet: A large-scale multimodal model for "
            "species identification in camera trap images."
        ),
        "pip_deps":     ["speciesnet"],
        "cache_bundle": {
            # SpeciesNet's model files live in a kagglehub cache. The runner
            # (_runner.py) points KAGGLEHUB_CACHE at
            # models/speciesnet-global/kagglehub_cache, so we extract there.
            # The hosted zip has models/ at its root, so it extracts straight
            # to models/speciesnet-global/kagglehub_cache/models/google/speciesnet,
            # exactly where the runner looks. (A stray kagglehub/ wrapper, if
            # ever present in a future zip, is auto-flattened on extract.)
            # 'extract_to' is relative to models/; 'probe' is relative to
            # extract_to and its presence means "already downloaded".
            "url":        "https://huggingface.co/chrissuthy/wildtag-speciesnet/resolve/main/speciesnet_cache.zip",
            "size_mb":    512,
            "extract_to": "speciesnet-global/kagglehub_cache",
            "probe":      "models/google/speciesnet",
        },
        "description":  (
            "Google's global species classifier covering 2000+ species "
            "across all continents."
        ),
    },
]

# ── Lookup helpers ─────────────────────────────────────────────────────────────

def get_model(model_id: str) -> dict:
    """Return registry entry for model_id, or raise KeyError."""
    for m in REGISTRY:
        if m["id"] == model_id:
            return m
    raise KeyError(f"Unknown model: {model_id}")

def classifiers() -> list:
    return [m for m in REGISTRY if m["type"] == "classifier"]
