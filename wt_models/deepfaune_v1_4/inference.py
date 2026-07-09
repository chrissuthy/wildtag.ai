"""
wildtag.ai - DeepFaune v1.4 inference module

Based on the official AddaxAI/DeepFaune integration code.
Source: classifTools.py from DeepFaune team (CNRS)

26 classes, ViT-Large DINOv2, 182px input with dynamic_img_size=True.
"""

from pathlib import Path
from PIL import Image
import sys


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# DeepFaune v1.4 class list - DEFINITIVE
# Source: AddaxAI classifTools.py for DeepFaune v1.4 (13 May 2025)
# https://plmlab.math.cnrs.fr/deepfaune/software/-/blob/master/classifTools.py
CLASSES = [
    "bison",         # 0
    "badger",        # 1
    "ibex",          # 2
    "beaver",        # 3
    "red_deer",      # 4  VERIFIED
    "golden_jackal", # 5
    "chamois",       # 6
    "cat",           # 7
    "goat",          # 8
    "roe_deer",      # 9  VERIFIED
    "dog",           # 10
    "raccoon_dog",   # 11
    "fallow_deer",   # 12
    "squirrel",      # 13 VERIFIED
    "moose",         # 14
    "equid",         # 15
    "genet",         # 16
    "wolverine",     # 17
    "hedgehog",      # 18
    "lagomorph",     # 19
    "wolf",          # 20
    "otter",         # 21
    "lynx",          # 22
    "marmot",        # 23
    "micromammal",   # 24
    "mouflon",       # 25
    "sheep",         # 26
    "mustelid",      # 27 VERIFIED
    "bird",          # 28
    "bear",          # 29
    "porcupine",     # 30
    "nutria",        # 31
    "muskrat",       # 32
    "raccoon",       # 33
    "fox",           # 34
    "reindeer",      # 35
    "wild_boar",     # 36
    "cow",           # 37
]

CROP_SIZE = 182
BACKBONE  = "vit_large_patch14_dinov2.lvd142m"


def load(model_dir: Path, device: str):
    """Load DeepFaune v1.4 using the official classifTools approach."""
    import torch
    import timm
    import torchvision.transforms as T
    from torch import tensor

    weights_path = model_dir / "deepfaune_v1.4.pt"
    if not weights_path.exists():
        raise FileNotFoundError(
            f"DeepFaune weights not found at {weights_path}")

    n_classes = len(CLASSES)

    # Build model exactly as classifTools.py does
    model = timm.create_model(
        BACKBONE,
        pretrained=False,
        num_classes=n_classes,
        dynamic_img_size=True,   # critical - allows 182px input
    )

    # Load checkpoint
    ckpt  = torch.load(str(weights_path), map_location=device,
                       weights_only=False)
    state = ckpt.get("state_dict", ckpt)

    # Strip base_model. prefix (checkpoint saves as base_model.xxx)
    # but timm model expects xxx directly
    state = {k.replace("base_model.", ""): v for k, v in state.items()}

    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    log(f"  DeepFaune v1.4 loaded ({n_classes} classes, {CROP_SIZE}px)")

    # Official transform from classifTools.py
    transform = T.Compose([
        T.Resize(size=(CROP_SIZE, CROP_SIZE),
                 interpolation=T.InterpolationMode.BICUBIC,
                 max_size=None, antialias=None),
        T.ToTensor(),
        T.Normalize(mean=tensor([0.4850, 0.4560, 0.4060]),
                    std= tensor([0.2290, 0.2240, 0.2250])),
    ])

    return {
        "model":     model,
        "classes":   CLASSES,
        "transform": transform,
        "device":    device,
    }


def square_crop(image: Image.Image, bbox: list) -> Image.Image:
    """
    Square and crop image using official DeepFaune get_crop logic.
    bbox is normalised [x, y, w, h] (MegaDetector format).
    """
    width, height = image.size
    bx, by, bw, bh = bbox

    xmin = int(round(bx * width))
    ymin = int(round(by * height))
    xmax = int(round(bw * width)) + xmin
    ymax = int(round(bh * height)) + ymin

    xsize = xmax - xmin
    ysize = ymax - ymin

    # Square the box
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

    results = sorted(
        zip(classes, probs),
        key=lambda x: x[1],
        reverse=True,
    )

    return [(label, float(conf)) for label, conf in results]
