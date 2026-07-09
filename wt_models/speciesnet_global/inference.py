"""
wildtag.ai - SpeciesNet (Global) inference module

Weights are cached by kagglehub during build_env.py.
The classifier loads from the kagglehub cache automatically.
"""

from pathlib import Path
from PIL import Image
import os


def load(model_dir: Path, device: str):
    """Load SpeciesNet classifier using kagglehub cached weights."""
    try:
        from speciesnet.classifier import SpeciesNetClassifier
        import kagglehub
    except ImportError as e:
        raise ImportError(f"Required package not installed: {e}")

    # kagglehub returns the local cache path (downloads if not cached)
    model_path = kagglehub.model_download("google/speciesnet/pyTorch/v4.0.3a")

    # Load classifier from the absolute local path
    classifier = SpeciesNetClassifier(model_name=model_path)
    return {"classifier": classifier, "device": device}


def predict(model_bundle: dict, crop: Image.Image) -> list:
    """Classify an animal crop. Returns [(label, confidence), ...]"""
    import tempfile

    classifier = model_bundle["classifier"]

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        tmp_path = f.name
    try:
        crop.convert("RGB").save(tmp_path, "JPEG")

        # Correct signature: predict(filepath, img=None)
        result = classifier.predict(tmp_path, None)

        import sys
        print(f"SN_DEBUG: type={type(result).__name__} val={str(result)[:200]}", file=sys.stderr, flush=True)

        if result and "scores" in result:
            labels = classifier.model_info.label_names
            scores = result["scores"]
            preds  = sorted(zip(labels, scores),
                           key=lambda x: x[1], reverse=True)
            return [(str(l).lower().replace(" ", "_"), float(s))
                    for l, s in preds]
        return []
    except Exception as e:
        raise RuntimeError(f"SpeciesNet prediction failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
