"""
wildtag.ai - DeepFaune New England (DFNE) inference module

DFNE is a re-trained DeepFaune model for north-eastern North American taxa
(Clarfeld et al. 2025, USGS; doi:10.5066/P1E7NDAF;
code.usgs.gov/vtcfwru/deepfaune-new-england).

Same architecture as DeepFaune v1.4 (ViT-Large DINOv2, timm
'vit_large_patch14_dinov2.lvd142m', 182px, dynamic_img_size=True), so this
module mirrors the DeepFaune v1.4 backend. Differences, all taken verbatim from
the DFNE authors' code:
  - 24 classes (alphabetical order, incl. 'no-species'), normalised here to
    wildtag's underscore convention.
  - checkpoint is wrapped: weights live under checkpoint['model_state_dict'].
  - transform uses default (bilinear) resize + standard ImageNet mean/std.
"""

from pathlib import Path
from PIL import Image
import sys


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# DFNE 24 taxa - DEFINITIVE order from the authors' model class (dfne model.py).
# Normalised to wildtag's lowercase/underscore convention. DISPLAY holds the
# authors' original human-readable names (kept for reference / optional UI use).
CLASSES = [
    "american_marten",     # 0
    "bird",                # 1   (author: "Bird sp.")
    "black_bear",          # 2
    "bobcat",              # 3
    "coyote",              # 4
    "domestic_cat",        # 5
    "domestic_cow",        # 6
    "domestic_dog",        # 7
    "fisher",              # 8
    "gray_fox",            # 9
    "gray_squirrel",       # 10
    "human",               # 11
    "moose",               # 12
    "mouse",               # 13  (author: "Mouse sp.")
    "opossum",             # 14
    "raccoon",             # 15
    "red_fox",             # 16
    "red_squirrel",        # 17
    "skunk",               # 18
    "snowshoe_hare",       # 19
    "white_tailed_deer",   # 20
    "wild_boar",           # 21
    "wild_turkey",         # 22
    "no_species",          # 23
]

DISPLAY = {
    "american_marten": "American Marten", "bird": "Bird sp.",
    "black_bear": "Black Bear", "bobcat": "Bobcat", "coyote": "Coyote",
    "domestic_cat": "Domestic Cat", "domestic_cow": "Domestic Cow",
    "domestic_dog": "Domestic Dog", "fisher": "Fisher", "gray_fox": "Gray Fox",
    "gray_squirrel": "Gray Squirrel", "human": "Human", "moose": "Moose",
    "mouse": "Mouse sp.", "opossum": "Opossum", "raccoon": "Raccoon",
    "red_fox": "Red Fox", "red_squirrel": "Red Squirrel", "skunk": "Skunk",
    "snowshoe_hare": "Snowshoe Hare", "white_tailed_deer": "White-tailed Deer",
    "wild_boar": "Wild Boar", "wild_turkey": "Wild Turkey",
    "no_species": "no-species",
}

CROP_SIZE = 182
BACKBONE  = "vit_large_patch14_dinov2.lvd142m"
WEIGHTS   = "dfne_weights_v1_0.pth"


def load(model_dir: Path, device: str):
    """Load DFNE exactly as the authors' model class does."""
    import torch
    import timm
    import torchvision.transforms as T

    weights_path = model_dir / WEIGHTS
    if not weights_path.exists():
        raise FileNotFoundError(f"DFNE weights not found at {weights_path}")

    n_classes = len(CLASSES)

    model = timm.create_model(
        BACKBONE,
        pretrained=False,
        num_classes=n_classes,
        dynamic_img_size=True,          # allows 182px input
    )

    # DFNE checkpoint is a training checkpoint: weights under 'model_state_dict'.
    # (Authors use weights_only=True; fall back to False for older torch.)
    try:
        ckpt = torch.load(str(weights_path), map_location=device,
                          weights_only=True)
    except Exception:
        ckpt = torch.load(str(weights_path), map_location=device,
                          weights_only=False)
    state = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    log(f"  DeepFaune New England loaded ({n_classes} classes, {CROP_SIZE}px)")

    # Author's exact transform: default (bilinear) resize + ImageNet norm.
    transform = T.Compose([
        T.Resize((CROP_SIZE, CROP_SIZE)),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    return {
        "model":     model,
        "classes":   CLASSES,
        "transform": transform,
        "device":    device,
    }


def square_crop(image: Image.Image, bbox: list) -> Image.Image:
    """
    Square and crop image using the DeepFaune get_crop logic.
    bbox is normalised [x, y, w, h] (MegaDetector format). Identical to the
    DeepFaune v1.4 backend - DFNE takes detector crops the same way.
    """
    width, height = image.size
    bx, by, bw, bh = bbox

    xmin = int(round(bx * width))
    ymin = int(round(by * height))
    xmax = int(round(bw * width)) + xmin
    ymax = int(round(bh * height)) + ymin

    xsize = xmax - xmin
    ysize = ymax - ymin

    if xsize > ysize:
        ymin = ymin - int((xsize - ysize) / 2)
        ymax = ymax + int((xsize - ysize) / 2)
    if ysize > xsize:
        xmin = xmin - int((ysize - xsize) / 2)
        xmax = xmax + int((ysize - xsize) / 2)

    return image.crop((max(0, xmin), max(0, ymin),
                       min(xmax, width), min(ymax, height)))


def predict(model_bundle: dict, crop: Image.Image) -> list:
    """
    Classify an animal crop.
    Returns [(label, confidence), ...] sorted by confidence descending.
    """
    import torch

    model     = model_bundle["model"]
    classes   = model_bundle["classes"]
    transform = model_bundle["transform"]
    device    = model_bundle["device"]

    tensor_img = transform(crop.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = model(tensor_img).softmax(dim=1)[0].tolist()

    results = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
    return [(label, float(conf)) for label, conf in results]
