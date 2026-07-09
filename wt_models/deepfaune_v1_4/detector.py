"""
wildtag.ai - DeepFaune v1.4 detector module

Uses deepfaune_detector.pt (YOLOv8s, 22MB) to detect animals, persons
and vehicles. Same output format as MegaDetector so _runner.py needs
no changes to the detection loop.

Detection output:
  [{"bbox": [x, y, w, h],  # normalised 0-1, xywh format
    "conf": float,
    "category": "animal" | "human" | "vehicle"}, ...]
"""

from pathlib import Path
from PIL import Image

_CATEGORIES = {0: "animal", 1: "human", 2: "vehicle"}


def load(model_dir: Path, device: str):
    from ultralytics import YOLO

    weights = model_dir / "deepfaune_detector.pt"
    if not weights.exists():
        raise FileNotFoundError(
            f"DeepFaune detector weights not found at {weights}.")

    model = YOLO(str(weights))

    # Move to device if CUDA requested
    if device == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                model.to("cuda")
        except Exception:
            pass

    return {"model": model, "device": device}


def detect(model_bundle: dict, image: Image.Image,
           confidence_threshold: float = 0.1) -> list:
    return detect_batch(model_bundle, [image], confidence_threshold)[0]


def detect_batch(model_bundle: dict, images: list,
                 confidence_threshold: float = 0.1) -> list:
    """Run detection on a batch of images. Returns list of detection lists."""
    model  = model_bundle["model"]
    device = model_bundle.get("device", "cpu")

    results = model(
        images,
        conf=confidence_threshold,
        device=0 if device == "cuda" else "cpu",
        verbose=False,
    )

    all_detections = []
    for r in results:
        detections = []
        if r.boxes is not None:
            for box in r.boxes:
                conf     = float(box.conf)
                cls_id   = int(box.cls)
                category = _CATEGORIES.get(cls_id, "animal")
                x1, y1, x2, y2 = box.xyxyn.tolist()[0]
                detections.append({
                    "bbox":     [x1, y1, x2 - x1, y2 - y1],
                    "conf":     conf,
                    "category": category,
                })
        all_detections.append(detections)

    return all_detections
