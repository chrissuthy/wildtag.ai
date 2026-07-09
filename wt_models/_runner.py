"""
wt_models/_runner.py
====================
Inference runner - executed as a subprocess inside wildtag_env/.

This script runs inside the bundled Python environment which has
PyTorch, torchvision, SpeciesNet etc. installed.

wildtag.py calls this via subprocess and reads the JSON results from stdout.
Progress is written to stderr so wildtag can stream it to the log.
All other log output also goes to stderr.
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime


def _safe_path(p: Path) -> str:
    """Return a path string that Windows can still open past the 260 char
    MAX_PATH limit, by opting into the \\\\?\\ long path prefix. Camera trap
    projects nest images under project/images/<site>/, so a long project
    folder name or site name can easily push the full path over the limit,
    which shows up as OSError: [Errno 22] Invalid argument on open."""
    s = str(p)
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        s = "\\\\?\\" + os.path.abspath(s)
    return s


_log_file_path = None


def log(msg: str):
    print(msg, flush=True)
    if _log_file_path:
        try:
            with open(_log_file_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass


def progress(done: int, total: int = 0):
    print(f"PROGRESS:{done}:{total}", flush=True)


# Test basic imports immediately so errors are visible
try:
    import torch
    log(f"-- torch {torch.__version__} imported OK")
except Exception as e:
    log(f"ERROR: Failed to import torch: {e}")
    sys.exit(1)

log(f"-- args: {sys.argv}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-list",  required=True)
    parser.add_argument("--classifier",  required=True)
    parser.add_argument("--det-conf",    type=float, default=0.1)
    parser.add_argument("--cls-conf",    type=float, default=0.6)
    parser.add_argument("--models-dir",  required=True)
    parser.add_argument("--wt-root",     required=True)
    parser.add_argument("--project-dir", default="")
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--geofence",    default="", help="e.g. 'GBR' to filter to UK species")
    parser.add_argument("--device",      default="cpu", help="cpu or cuda")
    parser.add_argument("--threads",     type=int, default=4, help="CPU thread count")
    parser.add_argument("--checkpoint-file",  default="", help="periodically written progress file")
    parser.add_argument("--checkpoint-every", type=int, default=200, help="checkpoint every N images")
    parser.add_argument("--log-file",         default="", help="also append log lines to this file")
    parser.add_argument("--stop-file",        default="", help="if this file appears, finish the current batch and exit")
    parser.add_argument("--resume",           action="store_true", help="seed results from --checkpoint-file")
    args = parser.parse_args()

    global _log_file_path
    if args.log_file:
        _log_file_path = args.log_file

    # Add wt_root to path so we can import wt_models
    wt_root = Path(args.wt_root)
    if str(wt_root) not in sys.path:
        sys.path.insert(0, str(wt_root))

    # Read image list
    with open(args.image_list, encoding="utf-8") as f:
        image_paths = [Path(l.strip()) for l in f if l.strip()]

    if not image_paths:
        log("No images to process.")
        print("[]")
        return

    log(f"-- Device detection...")
    if args.device == "cuda":
        try:
            if torch.cuda.is_available():
                device = "cuda"
                log(f"-- Device: CUDA ({torch.cuda.get_device_name(0)})")
            else:
                device = "cpu"
                log("-- WARNING: CUDA requested but not available, using CPU")
        except Exception:
            device = "cpu"
            log("-- WARNING: CUDA check failed, using CPU")
    else:
        device = "cpu"
        log("-- Device: CPU")

    models_dir = Path(args.models_dir)

    # Load classifier first so we know if detector is needed
    log(f"\n-- Loading classifier: {args.classifier}")
    cls_dir     = models_dir / args.classifier
    handles_own = "speciesnet" in args.classifier.lower()
    log(f"-- HANDLES_OWN_DETECTION = {handles_own} (classifier={args.classifier})")

    if handles_own and (args.checkpoint_file or args.stop_file or args.resume):
        log("-- WARNING: checkpoint/resume/stop are not supported for "
            "SpeciesNet (it processes all images internally as one "
            "opaque subprocess). This run will not checkpoint.")

    if not handles_own:
        cls_inf   = _load_module(args.classifier, cls_dir, wt_root)
        cls_model = cls_inf.load(cls_dir, device)
        log(f"   Loaded.")
    else:
        cls_inf   = None
        cls_model = None
        log(f"   SpeciesNet: subprocess mode, skipping load()")

    # Load detector
    # DeepFaune: use its bundled YOLOv8s detector (22MB, no MegaDetector needed)
    # SpeciesNet: uses its own internal detector (skipped entirely)
    # Others: use the user-selected detector (MegaDetector)
    det_inf   = None
    det_model = None
    if not handles_own:
        if "deepfaune" in args.classifier.lower():
            import sys as _sys
            _sys.path.insert(0, str(wt_root))
            from wt_models.deepfaune_v1_4 import detector as _df_det
            det_dir   = models_dir / args.classifier
            det_inf   = _df_det
            det_model = det_inf.load(det_dir, device)
            log(f"\n-- Using DeepFaune detector (YOLOv8s, 22MB)")
            log(f"   Loaded.")
        else:
            log(f"\n-- Loading detector: {args.detector}")
            det_dir   = models_dir / args.detector
            import importlib.util
            det_inf   = _load_module(args.detector, det_dir, wt_root)
            det_model = det_inf.load(det_dir, device)
            log(f"   Loaded.")

    # ── SpeciesNet special case ───────────────────────────────────────────────
    # SpeciesNet is a complete pipeline tool — it runs its own MegaDetector
    # and classifier internally via `python -m speciesnet.scripts.run_model`.
    # We call it as a subprocess and parse its JSON output.
    if handles_own:
        import tempfile as _tempfile, subprocess as _sp, os as _os_sn

        # Find the common image folder (project root)
        project_root = image_paths[0].parent
        for p in image_paths[1:]:
            while True:
                try:
                    p.relative_to(project_root)
                    break
                except ValueError:
                    project_root = project_root.parent

        # Use a temp path that doesn't exist yet — SpeciesNet creates it
        sn_json = Path(_tempfile.gettempdir()) / f"sn_out_{_os_sn.getpid()}.json"
        if sn_json.exists():
            sn_json.unlink()

        # Point kagglehub at our local models cache so no internet needed
        sn_cache = Path(args.models_dir) / "speciesnet-global" / "kagglehub_cache"
        env = _os_sn.environ.copy()
        if sn_cache.exists():
            env["KAGGLEHUB_CACHE"] = str(sn_cache)
            log(f"-- Using local SpeciesNet cache: {sn_cache}")
        else:
            log(f"-- WARNING: local SpeciesNet cache not found, will use system cache")

        try:
            cmd = [
                sys.executable,
                "-m", "speciesnet.scripts.run_model",
                "--folders", str(project_root),
                "--predictions_json", str(sn_json),
            ]
            if args.geofence:
                cmd += ["--country", args.geofence]

            log(f"-- Running SpeciesNet on {project_root.name}...")
            log(f"-- Command: {' '.join(str(c) for c in cmd)}")
            log(f"-- SpeciesNet processes all images internally — progress shown below.")

            sn_proc = _sp.Popen(
                cmd,
                stdout=_sp.PIPE,
                stderr=_sp.STDOUT,
                text=True, encoding="utf-8",
                env=env, bufsize=1)

            sn_img_count = 0
            for raw in sn_proc.stdout:
                line = raw.rstrip()
                if not line:
                    continue
                # Try to extract progress from SpeciesNet output
                if any(kw in line.lower() for kw in
                       ("processing", "image", "prediction", "%")):
                    log(f"  SN: {line}")
                    # Emit a progress tick so the UI stays alive
                    sn_img_count += 1
                    if sn_img_count % 10 == 0:
                        pct = min(sn_img_count, len(image_paths))
                        progress(pct, len(image_paths))
                elif "error" in line.lower() or "warning" in line.lower():
                    log(f"  SN: {line}")

            sn_proc.wait()

            if sn_proc.returncode != 0:
                raise RuntimeError(
                    f"SpeciesNet failed (exit code {sn_proc.returncode}). "
                    f"See log above for details.")

            if not sn_json.exists():
                raise FileNotFoundError(
                    f"SpeciesNet produced no output at {sn_json}")

            with open(sn_json, encoding="utf-8") as f:
                sn_output = json.load(f)

        finally:
            try: sn_json.unlink()
            except: pass

        # Parse SpeciesNet output JSON into wildtag row format
        results = _parse_speciesnet_output(sn_output, args.cls_conf, project_root)
        log(f"\n-- Done. {len(results):,} detections from {len(image_paths):,} images.")

        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(results, f)
        log(f"-- Results written to {args.output_file}")
        return

    # ── Phase 1: Detection (all images) ──────────────────────────────────────
    log(f"\n-- Processing {len(image_paths):,} images...")
    n = len(image_paths)

    # Derive project root using --project-dir (the user's project folder)
    # images/ subfolder means relative paths include site name → locationName populated
    if args.project_dir:
        proj       = Path(args.project_dir)
        images_dir = proj / "images"
        if images_dir.exists() and image_paths:
            try:
                image_paths[0].relative_to(images_dir)
                project_root = images_dir
            except ValueError:
                project_root = proj
        else:
            project_root = proj
    elif image_paths:
        try:
            common = image_paths[0].parent
            for p in image_paths[1:]:
                while True:
                    try:
                        p.relative_to(common)
                        break
                    except ValueError:
                        common = common.parent
            project_root = common
        except Exception:
            project_root = image_paths[0].parent
    else:
        project_root = Path(args.wt_root)

    def _site_of(img_path: Path) -> str:
        """Return the site folder name for an image, e.g.
        images/site1/IMG_001.JPG -> site1. Same logic as the
        locationName field in _make_row, so progress logging and
        the CSV output always agree on which site an image is in."""
        try:
            rel = img_path.relative_to(project_root)
        except ValueError:
            return ""
        parts = rel.parts
        if parts and parts[0].lower() == "images":
            parts = parts[1:]
        return parts[0] if len(parts) > 1 else ""

    # Set PyTorch to use specified thread count and device
    import os
    torch.set_num_threads(args.threads)
    log(f"-- Using {args.threads} CPU threads, device: {args.device}")

    from PIL import Image

    # Detection batch size — larger = faster on GPU, keep smaller on CPU
    DET_BATCH = 8 if args.device == "cuda" else 4

    results = []
    if args.resume and args.checkpoint_file:
        cp_path = Path(args.checkpoint_file)
        if cp_path.exists():
            try:
                results = json.loads(cp_path.read_text(encoding="utf-8"))
                log(f"-- Resumed {len(results):,} rows from checkpoint")
            except Exception as e:
                log(f"WARNING: could not read checkpoint file: {e}")
                results = []

    pending_crops = []

    # Cap how many crops we hold in memory at once. Classifying in chunks
    # like this bounds peak memory regardless of dataset size, instead of
    # queuing every crop from the whole run before classifying any of them.
    BATCH_SIZE  = 32 if args.device == "cuda" else 16
    MAX_PENDING = BATCH_SIZE * 10

    def _log_failed_image(img_path, err):
        """Append to a permanent failure log. Unlike the checkpoint file,
        this is never cleared, on success or otherwise, so a list of
        every image that could not be read survives across runs."""
        if not args.project_dir:
            return
        try:
            fail_log = Path(args.project_dir) / "wildtag_failed_images.txt"
            stamp    = datetime.now().isoformat(timespec="seconds")
            with open(fail_log, "a", encoding="utf-8") as f:
                f.write(f"{stamp}\t{img_path}\t{err}\n")
        except Exception:
            pass

    def _open_image_with_retry(img_path, attempts=3, delay=1.0):
        """Try to open an image up to `attempts` times, pausing between
        tries. A bad read on a network drive is often transient, so most
        failures should clear up on a second or third attempt. Only after
        every attempt fails do we log it and give up on this image."""
        last_err = None
        for attempt in range(1, attempts + 1):
            try:
                return Image.open(_safe_path(img_path)).convert("RGB")
            except Exception as e:
                last_err = e
                if attempt < attempts:
                    time.sleep(delay)
        log(f"  ERROR loading {img_path.name} after {attempts} attempts: {last_err}")
        _log_failed_image(img_path, last_err)
        return None

    def _write_checkpoint():
        if not args.checkpoint_file:
            return
        try:
            Path(args.checkpoint_file).write_text(
                json.dumps(results), encoding="utf-8")
        except Exception as e:
            log(f"WARNING: could not write checkpoint: {e}")

    def _stop_requested():
        return bool(args.stop_file) and Path(args.stop_file).exists()

    def _flush_crops():
        """Classify whatever is currently in pending_crops, then clear it."""
        if not pending_crops:
            return
        has_batch = hasattr(cls_inf, "predict_batch")
        log(f"  Classifying {len(pending_crops):,} queued crops...")

        if has_batch:
            for b_start in range(0, len(pending_crops), BATCH_SIZE):
                b_end   = min(b_start + BATCH_SIZE, len(pending_crops))
                b_items = pending_crops[b_start:b_end]
                crops   = [item[4] for item in b_items]

                try:
                    batch_preds = cls_inf.predict_batch(cls_model, crops)
                except Exception as e:
                    log(f"  Batch classify error: {e}, falling back to single")
                    batch_preds = [cls_inf.predict(cls_model, c) for c in crops]

                for (img_path, w, h, det, _), preds in zip(b_items, batch_preds):
                    _append_cls_result(
                        results, img_path, w, h, det, preds,
                        project_root, args, cls_inf)
        else:
            for img_path, w, h, det, crop in pending_crops:
                try:
                    preds = cls_inf.predict(cls_model, crop)
                except Exception as e:
                    log(f"  ERROR classifying {img_path.name}: {e}")
                    preds = []
                _append_cls_result(
                    results, img_path, w, h, det, preds,
                    project_root, args, cls_inf)

        pending_crops.clear()

    # Process images in detection batches
    stopped         = False
    last_checkpoint = 0
    for batch_start in range(0, n, DET_BATCH):
        batch_paths = image_paths[batch_start:batch_start+DET_BATCH]
        batch_imgs  = []
        batch_sizes = []

        for img_path in batch_paths:
            img = _open_image_with_retry(img_path)
            if img is not None:
                batch_imgs.append(img)
                batch_sizes.append(img.size)
            else:
                batch_imgs.append(None)
                batch_sizes.append((0, 0))

        # Run batch detection if supported, else fall back to single
        valid_imgs = [img for img in batch_imgs if img is not None]
        try:
            if not valid_imgs:
                # Every image in this batch failed to load, nothing to detect
                batch_detections = [[] for _ in batch_imgs]
            elif hasattr(det_inf, "detect_batch"):
                batch_detections = det_inf.detect_batch(
                    det_model, valid_imgs, args.det_conf)
                # Re-align with None entries
                det_iter = iter(batch_detections)
                batch_detections = [
                    next(det_iter) if img is not None else []
                    for img in batch_imgs]
            else:
                batch_detections = []
                for img in batch_imgs:
                    if img is None:
                        batch_detections.append([])
                    else:
                        batch_detections.append(
                            det_inf.detect(det_model, img, args.det_conf))
        except Exception as e:
            log(f"  ERROR in batch detection: {e}")
            batch_detections = [[] for _ in batch_imgs]

        for i, (img_path, img, (w, h), detections) in enumerate(
                zip(batch_paths, batch_imgs, batch_sizes, batch_detections)):
            global_i = batch_start + i
            progress(global_i, n)

            if img is None:
                results.append(_make_row(
                    img_path, "load_error", 0.0,
                    [0.0, 0.0, 0.0, 0.0], w, h, project_root,
                    det_label="NA", det_conf=0.0,
                    cv_label="NA", cv_conf=0.0,
                    cv_model=args.classifier,
                    is_empty=True))
                continue

            try:
                if not detections:
                    results.append(_make_row(
                        img_path, "empty", 0.0,
                        [0.0, 0.0, 0.0, 0.0], w, h, project_root,
                        det_label="NA", det_conf=0.0,
                        cv_label="NA", cv_conf=0.0,
                        cv_model=args.classifier,
                        is_empty=True))
                    continue

                for det in detections:
                    cat      = det.get("category", "animal")
                    det_conf = det["conf"]

                    if cat != "animal":
                        results.append(_make_row(
                            img_path, cat, det_conf,
                            det["bbox"], w, h, project_root,
                            det_label=cat, det_conf=det_conf,
                            cv_label="NA", cv_conf=0.0,
                            cv_model=args.classifier))
                        continue

                    # Build crop and queue for batch classification
                    if hasattr(cls_inf, "square_crop"):
                        crop = cls_inf.square_crop(img, det["bbox"])
                    else:
                        bx, by, bw, bh = det["bbox"]
                        x0 = max(0, int(bx * w));       y0 = max(0, int(by * h))
                        x1 = min(w, int((bx+bw) * w));  y1 = min(h, int((by+bh) * h))
                        if x1 <= x0 or y1 <= y0:
                            continue
                        crop = img.crop((x0, y0, x1, y1))

                    pending_crops.append((img_path, w, h, det, crop))

            except Exception as e:
                log(f"  ERROR {img_path.name}: {e}")

        done = min(batch_start + DET_BATCH, n)
        if done % 50 == 0 or done == n:
            site      = _site_of(batch_paths[-1]) if batch_paths else ""
            site_note = f" (in {site})" if site else ""
            log(f"  {done:,}/{n:,} images detected, "
                f"{len(pending_crops):,} crops queued{site_note}")

        # Flush periodically so we never hold more than MAX_PENDING crops
        # in memory at once, regardless of how large the dataset is.
        if len(pending_crops) >= MAX_PENDING:
            _flush_crops()

        if args.checkpoint_file and done - last_checkpoint >= args.checkpoint_every:
            _flush_crops()
            _write_checkpoint()
            last_checkpoint = done
            log(f"  Checkpoint saved: {len(results):,} rows")

        if _stop_requested():
            log("\n-- Stop file detected, finishing up and saving progress...")
            _flush_crops()
            _write_checkpoint()
            stopped = True
            break

    # Classify anything left over after the final detection batch
    _flush_crops()

    if stopped:
        print("STOPPED", flush=True)

    progress(n, n)
    log(f"\n-- Done. {len(results):,} detections from {n:,} images.")

    _write_checkpoint()

    # Write results to output file (avoids stdout pollution from libraries)
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(results, f)
    log(f"-- Results written to {args.output_file}")


def _parse_sn_taxonomy(taxonomy_str: str) -> str:
    """
    Extract human-readable label from SpeciesNet taxonomy string.
    Format: uuid;class;order;family;genus;species;common_name
    Returns common_name if present, else species, else family, else 'unknown'.
    Normalises to lowercase with underscores.

    Special cases handled:
      blank / no common_name → 'empty'
      no_cv_result           → 'low_confidence'
    """
    if not taxonomy_str:
        return "unknown"

    # Some predictions are bare keywords not taxonomy strings
    bare = taxonomy_str.strip().lower()
    if bare in ("blank", "empty", "no cv result", "no_cv_result"):
        return "empty"

    parts = taxonomy_str.split(";")

    # Check if this is a blank prediction (uuid;;;;;;blank format)
    if len(parts) >= 7 and parts[6].strip().lower() == "blank":
        return "empty"

    for idx in [6, 5, 3]:  # common_name, species, family
        if idx < len(parts) and parts[idx].strip():
            label = parts[idx].strip().lower().replace(" ", "_")
            # Map very broad labels to low_confidence
            if label in ("animal", "mammal", "bird", "vertebrate",
                         "animalia", "no_cv_result"):
                return "low_confidence"
            return label

    return "unknown"


def _parse_speciesnet_output(sn_output: dict, cls_conf: float,
                              project_root: Path) -> list:
    """
    Parse SpeciesNet run_model JSON output into wildtag row format.

    Confirmed field structure from v4.0.3a output:
      filepath         - full absolute path
      prediction       - uuid;class;order;family;genus;species;common_name
      prediction_score - float
      prediction_source- 'detector'|'classifier'|'classifier+geofence+rollup_to_family' etc.
      detections       - [{category:1/2/3, label, conf, bbox:[x,y,w,h]}]
      classifications  - {classes:[taxonomy_strings], scores:[floats]}
    """
    results = []
    from PIL import Image as PilImg

    predictions = sn_output.get("predictions", [])

    for pred in predictions:
        filepath = pred.get("filepath", "")
        if not filepath:
            continue

        img_path = Path(filepath)

        # Image dimensions
        try:
            with PilImg.open(img_path) as img:
                img_w, img_h = img.size
        except Exception:
            img_w, img_h = 0, 0

        # Parse top-level prediction
        raw_pred    = pred.get("prediction", "")
        pred_score  = float(pred.get("prediction_score", 0.0))
        pred_source = pred.get("prediction_source", "")
        label       = _parse_sn_taxonomy(raw_pred)

        # Blank/empty detection
        is_blank = label in ("empty", "blank", "low_confidence", "unknown") or not raw_pred

        # Detections — find best animal/human/vehicle bbox
        detections = pred.get("detections", [])
        best_det   = None
        for det in detections:
            cat = int(det.get("category", 0))
            if cat == 1:  # animal
                if best_det is None or float(det.get("conf", 0)) > float(best_det.get("conf", 0)):
                    best_det = det
            elif cat == 2 and label == "human":
                if best_det is None:
                    best_det = det
            elif cat == 3 and label == "vehicle":
                if best_det is None:
                    best_det = det

        if best_det and not is_blank:
            bx, by, bw, bh = best_det.get("bbox", [0, 0, 0, 0])
            det_conf  = float(best_det.get("conf", 0))
            det_label = best_det.get("label", "animal")
        else:
            bx = by = bw = bh = 0.0
            det_conf  = 0.0
            det_label = "NA"

        # Top CV classification
        cls_data    = pred.get("classifications", {})
        cls_classes = cls_data.get("classes", [])
        cls_scores  = cls_data.get("scores", [])
        if cls_classes and cls_scores:
            cv_label = _parse_sn_taxonomy(cls_classes[0])
            cv_conf  = float(cls_scores[0])
        else:
            cv_label = label
            cv_conf  = pred_score

        # Final label — apply confidence threshold
        if is_blank:
            final_label = "empty"
            conf_str    = "NA"
        elif pred_score < cls_conf:
            final_label = "low_confidence"
            conf_str    = str(round(pred_score, 5))
        else:
            final_label = label
            conf_str    = str(round(pred_score, 5))

        # Relative path
        try:
            rel = img_path.relative_to(project_root)
        except ValueError:
            rel = Path(img_path.name)

        rel_parts = rel.parts
        if rel_parts and rel_parts[0].lower() == "images":
            rel_parts = rel_parts[1:]
        location_name = rel_parts[0] if len(rel_parts) > 1 else ""

        exif = _extract_exif(img_path)

        row = {
            "absolute_path":           str(project_root),
            "relative_path":           str(rel),
            "locationName":            location_name,
            "data_type":               "img",
            "label":                   final_label,
            "confidence":              conf_str,
            "detector_label":          det_label,
            "detector_confidence":     "NA" if is_blank else str(round(det_conf, 5)),
            "cv_label":                cv_label,
            "cv_confidence":           "NA" if is_blank else str(round(cv_conf, 5)),
            "cv_model":                "speciesnet-global",
            "human_verified":          "FALSE",
            "bbox_left":               "NA" if is_blank else str(bx),
            "bbox_top":                "NA" if is_blank else str(by),
            "bbox_right":              "NA" if is_blank else str(bx + bw),
            "bbox_bottom":             "NA" if is_blank else str(by + bh),
            "bbox_normalised":         "NA" if is_blank else "1",
            "file_width":              str(img_w),
            "file_height":             str(img_h),
            "DateTimeOriginal":        exif["DateTimeOriginal"],
            "DateTime":                exif["DateTime"],
            "DateTimeDigitized":       exif["DateTimeDigitized"],
            "Latitude":                exif["Latitude"],
            "Longitude":               exif["Longitude"],
            "GPSLink":                 exif["GPSLink"],
            "Altitude":                exif["Altitude"],
            "Make":                    exif["Make"],
            "Model":                   exif["Model"],
            "Flash":                   exif["Flash"],
            "ExifOffset":              exif["ExifOffset"],
            "ResolutionUnit":          exif["ResolutionUnit"],
            "YCbCrPositioning":        exif["YCbCrPositioning"],
            "XResolution":             exif["XResolution"],
            "YResolution":             exif["YResolution"],
            "ExifVersion":             exif["ExifVersion"],
            "ComponentsConfiguration": exif["ComponentsConfiguration"],
            "FlashPixVersion":         exif["FlashPixVersion"],
            "ColorSpace":              exif["ColorSpace"],
            "ExifImageWidth":          exif["ExifImageWidth"],
            "ISOSpeedRatings":         exif["ISOSpeedRatings"],
            "ExifImageHeight":         exif["ExifImageHeight"],
            "ExposureMode":            exif["ExposureMode"],
            "WhiteBalance":            exif["WhiteBalance"],
            "SceneCaptureType":        exif["SceneCaptureType"],
            "ExposureTime":            exif["ExposureTime"],
            "Software":                exif["Software"],
            "Sharpness":               exif["Sharpness"],
            "Saturation":              exif["Saturation"],
            "ReferenceBlackWhite":     exif["ReferenceBlackWhite"],
        }
        results.append(row)

    return results


def _load_module(model_id: str, model_dir: Path, wt_root: Path):
    """Load inference.py from model_dir or wt_models built-ins."""
    import importlib.util

    # First look in the models/ download directory
    candidate = model_dir / "inference.py"
    if not candidate.exists():
        # Try exact name conversion
        builtin_name = model_id.replace("-", "_")
        candidate = wt_root / "wt_models" / builtin_name / "inference.py"

    if not candidate.exists():
        # Search all subfolders of wt_models for a matching inference.py
        # Match on the base model name (e.g. "deepfaune" matches "deepfaune_v1_4")
        base_name = model_id.split("-")[0].replace("-", "_")
        wt_models_dir = wt_root / "wt_models"
        for subfolder in wt_models_dir.iterdir():
            if subfolder.is_dir() and base_name in subfolder.name:
                inf = subfolder / "inference.py"
                if inf.exists():
                    candidate = inf
                    break

    if not candidate.exists():
        raise FileNotFoundError(
            f"No inference.py found for {model_id}. "
            f"Looked in {wt_root / 'wt_models'}")

    spec   = importlib.util.spec_from_file_location(
        f"wt_{model_id.replace('-','_')}", candidate)
    module = importlib.util.module_from_spec(spec)

    # Read HANDLES_OWN_DETECTION directly from source BEFORE exec_module
    source = candidate.read_text(encoding="utf-8")
    if "HANDLES_OWN_DETECTION = True" in source:
        module.HANDLES_OWN_DETECTION = True
    else:
        module.HANDLES_OWN_DETECTION = False

    # Register in sys.modules then exec
    import sys as _sys
    mod_name = f"wt_{model_id.replace('-','_')}"
    _sys.modules[mod_name] = module
    spec.loader.exec_module(module)

    # If exec_module failed to define functions (e.g. speciesnet import error),
    # re-read and exec with a clean namespace using compile+exec
    if not hasattr(module, "run_on_folder") and not hasattr(module, "predict"):
        code = compile(source, str(candidate), "exec")
        exec(code, module.__dict__)

    return module


# ── UK species geofence ───────────────────────────────────────────────────────
# Species known to occur in the UK - filter out implausible predictions
UK_SPECIES = {
    # ── Wild mammals ──────────────────────────────────────────────────────────
    # Deer
    "red_deer", "roe_deer", "fallow_deer", "sika_deer",
    "chinese_water_deer", "muntjac", "deer",
    # Carnivores
    "red_fox", "fox", "badger", "otter", "stoat", "weasel",
    "polecat", "pine_marten", "mink", "american_mink",
    "wildcat",
    # Lagomorphs
    "rabbit", "brown_hare", "mountain_hare", "lagomorph",
    # Rodents
    "red_squirrel", "grey_squirrel", "squirrel",
    "water_vole", "bank_vole", "field_vole", "orkney_vole",
    "wood_mouse", "yellow_necked_mouse", "harvest_mouse",
    "brown_rat", "black_rat",
    "dormouse", "hazel_dormouse",
    "micromammal",
    # Insectivores
    "hedgehog", "mole",
    "common_shrew", "pygmy_shrew", "water_shrew",
    # Wild boar
    "wild_boar",
    # Bats (camera traps rarely capture but possible)
    "bat",
    # ── Livestock and domestic ────────────────────────────────────────────────
    "cow", "cattle", "sheep", "goat", "horse", "equid",
    "dog", "cat",
    # ── Birds ─────────────────────────────────────────────────────────────────
    "bird", "raptor", "pheasant", "red_grouse", "partridge",
    "crow", "raven", "magpie", "jay", "buzzard", "red_kite",
    # ── Special / system labels ───────────────────────────────────────────────
    "human", "vehicle", "empty", "undefined",
    "unclassified", "low_confidence",
    # ── Broad group labels (DeepFaune) ────────────────────────────────────────
    "mustelid", "micromammal", "lagomorph", "equid", "bird",
    # ── SpeciesNet taxonomy rollup labels ─────────────────────────────────────
    "cervidae_family", "sciuridae_family", "mustelidae_family",
    "leporidae_family", "bovidae_family", "felidae_family",
    "artiodactyla_order", "carnivora_order", "rodentia_order",
    "lagomorpha_order", "chiroptera_order",
    "european_roe_deer", "european_red_deer", "european_fallow_deer",
    "european_badger", "eurasian_otter", "european_pine_marten",
    "european_hedgehog", "european_rabbit", "brown_hare",
    "red_fox", "arctic_fox",
}


def _append_cls_result(results, img_path, w, h, det, preds,
                        project_root, args, cls_inf):
    """Apply geofence/threshold and append a classification result row."""
    det_conf = det["conf"]

    if not preds:
        results.append(_make_row(
            img_path, "unclassified", det_conf,
            det["bbox"], w, h, project_root,
            det_label="animal", det_conf=det_conf,
            cv_label="NA", cv_conf=0.0,
            cv_model=args.classifier))
        return

    cv_label, cv_conf = preds[0]

    if args.geofence:
        cv_label, cv_conf = _apply_geofence(
            cv_label, cv_conf, preds, args.geofence)

    final_label = cv_label if cv_conf >= args.cls_conf else "low_confidence"

    results.append(_make_row(
        img_path, final_label, cv_conf,
        det["bbox"], w, h, project_root,
        det_label="animal", det_conf=det_conf,
        cv_label=cv_label, cv_conf=cv_conf,
        cv_model=args.classifier))


def _apply_geofence(label: str, conf: float, all_preds: list,
                    geofence: str) -> tuple:
    """
    If geofence is set, check if label is plausible for that region.
    If not, find the top prediction that IS plausible.
    Returns (label, conf) - possibly unchanged.
    """
    if not geofence:
        return label, conf

    region_species = UK_SPECIES if geofence.upper() in ("GBR", "UK", "GB") else None
    if not region_species:
        return label, conf

    if label.lower() in region_species:
        return label, conf

    # Find best plausible prediction from all_preds
    for pred_label, pred_conf in all_preds:
        if pred_label.lower() in region_species:
            return pred_label, pred_conf

    # Nothing plausible - return original but flagged
    return label, conf


def _extract_exif(img_path: Path) -> dict:
    """Extract EXIF metadata from an image file."""
    EXIF_TAGS = {
        36867: "DateTimeOriginal", 36868: "DateTimeDigitized", 306: "DateTime",
        271: "Make", 272: "Model", 37385: "Flash", 34665: "ExifOffset",
        296: "ResolutionUnit", 531: "YCbCrPositioning", 282: "XResolution",
        283: "YResolution", 36864: "ExifVersion", 37121: "ComponentsConfiguration",
        40960: "FlashPixVersion", 40961: "ColorSpace", 40962: "ExifImageWidth",
        34855: "ISOSpeedRatings", 40963: "ExifImageHeight", 41986: "ExposureMode",
        41987: "WhiteBalance", 41990: "SceneCaptureType", 33434: "ExposureTime",
        305: "Software", 41994: "Sharpness", 41993: "Saturation",
        532: "ReferenceBlackWhite",
    }
    result = {col: "NA" for col in EXIF_TAGS.values()}
    result.update({"Latitude": "NA", "Longitude": "NA",
                   "GPSLink": "NA", "Altitude": "NA"})
    try:
        from PIL import Image as PilImage
        with PilImage.open(_safe_path(img_path)) as img:
            exif_data = img._getexif()
            if not exif_data:
                return result
            for tag_id, value in exif_data.items():
                if tag_id in EXIF_TAGS:
                    result[EXIF_TAGS[tag_id]] = str(value)
            gps_tag_id = 34853
            if gps_tag_id in exif_data:
                gps = exif_data[gps_tag_id]
                def to_deg(vals):
                    d, m, s = vals
                    return float(d) + float(m)/60 + float(s)/3600
                try:
                    lat = to_deg(gps[2])
                    if gps[1] == "S": lat = -lat
                    lon = to_deg(gps[4])
                    if gps[3] == "W": lon = -lon
                    result["Latitude"]  = str(round(lat, 6))
                    result["Longitude"] = str(round(lon, 6))
                    result["GPSLink"]   = f"https://maps.google.com/?q={lat},{lon}"
                    if 6 in gps:
                        result["Altitude"] = str(float(gps[6]))
                except Exception:
                    pass
    except Exception:
        pass
    return result


_exif_cache = {}


def _make_row(img_path: Path, label, conf, bbox, img_w, img_h,
              project_root: Path = None,
              det_label: str = "",
              det_conf: float = 0.0,
              cv_label: str = "",
              cv_conf: float = 0.0,
              cv_model: str = "",
              is_empty: bool = False) -> dict:
    """Build a result row with all CSV fields including EXIF."""
    bx, by, bw, bh = bbox

    if project_root:
        try:
            rel = img_path.relative_to(project_root)
        except ValueError:
            rel = Path(img_path.name)
    else:
        rel = Path(img_path.name)

    # Derive locationName from first folder component of relative path
    # e.g. images/site1/IMG_001.JPG -> site1
    # Strip leading 'images/' if present
    rel_parts = rel.parts
    if rel_parts and rel_parts[0].lower() == "images":
        rel_parts = rel_parts[1:]
    location_name = rel_parts[0] if len(rel_parts) > 1 else ""

    key = str(img_path)
    if key not in _exif_cache:
        _exif_cache[key] = _extract_exif(img_path)
    exif = _exif_cache[key]

    # For empty images, bbox and detection fields are NA
    if is_empty:
        bbox_left = bbox_top = bbox_right = bbox_bottom = "NA"
        bbox_norm = "NA"
    else:
        bbox_left  = str(bx)
        bbox_top   = str(by)
        bbox_right = str(bx + bw)
        bbox_bottom= str(by + bh)
        bbox_norm  = "1"

    return {
        "absolute_path":           str(project_root) if project_root else str(img_path.parent),
        "relative_path":           str(rel),
        "locationName":            location_name,
        "data_type":               "img",
        "label":                   str(label).lower().replace(" ", "_"),
        "confidence":              "NA" if is_empty else str(round(float(conf), 5)),
        "detector_label":          str(det_label),
        "detector_confidence":     "NA" if is_empty else str(round(float(det_conf), 5)),
        "cv_label":                str(cv_label),
        "cv_confidence":           "NA" if is_empty else str(round(float(cv_conf), 5)),
        "cv_model":                str(cv_model),
        "human_verified":          "FALSE",
        "bbox_left":               bbox_left,
        "bbox_top":                bbox_top,
        "bbox_right":              bbox_right,
        "bbox_bottom":             bbox_bottom,
        "bbox_normalised":         bbox_norm,
        "file_width":              str(img_w),
        "file_height":             str(img_h),
        "DateTimeOriginal":        exif["DateTimeOriginal"],
        "DateTime":                exif["DateTime"],
        "DateTimeDigitized":       exif["DateTimeDigitized"],
        "Latitude":                exif["Latitude"],
        "Longitude":               exif["Longitude"],
        "GPSLink":                 exif["GPSLink"],
        "Altitude":                exif["Altitude"],
        "Make":                    exif["Make"],
        "Model":                   exif["Model"],
        "Flash":                   exif["Flash"],
        "ExifOffset":              exif["ExifOffset"],
        "ResolutionUnit":          exif["ResolutionUnit"],
        "YCbCrPositioning":        exif["YCbCrPositioning"],
        "XResolution":             exif["XResolution"],
        "YResolution":             exif["YResolution"],
        "ExifVersion":             exif["ExifVersion"],
        "ComponentsConfiguration": exif["ComponentsConfiguration"],
        "FlashPixVersion":         exif["FlashPixVersion"],
        "ColorSpace":              exif["ColorSpace"],
        "ExifImageWidth":          exif["ExifImageWidth"],
        "ISOSpeedRatings":         exif["ISOSpeedRatings"],
        "ExifImageHeight":         exif["ExifImageHeight"],
        "ExposureMode":            exif["ExposureMode"],
        "WhiteBalance":            exif["WhiteBalance"],
        "SceneCaptureType":        exif["SceneCaptureType"],
        "ExposureTime":            exif["ExposureTime"],
        "Software":                exif["Software"],
        "Sharpness":               exif["Sharpness"],
        "Saturation":              exif["Saturation"],
        "ReferenceBlackWhite":     exif["ReferenceBlackWhite"],
    }


if __name__ == "__main__":
    main()
