"""
wt_models/engine.py
===================
The wildtag.ai inference engine.

Runs detection + classification using the bundled Python environment
(wildtag_env/) so wildtag.py itself only needs tkinter and standard
library - no PyTorch required in the system Python.

The engine spawns a subprocess using the bundled Python, which has
all heavy dependencies installed. Results are returned via JSON stdout.

Checkpointing
--------------
While the subprocess runs, _runner.py periodically writes everything it
has classified so far to `wildtag_checkpoint.json` in the project folder,
alongside a running `wildtag_run_log.txt`. If the run crashes or the
computer loses power partway through, the next run can resume from the
checkpoint instead of starting over - see `checkpoint_status()` and the
`resume` argument to `run_pipeline()`.

Stopping
--------
`run_pipeline()` accepts a `stop_flag` callable. When it starts returning
True, the engine touches `wildtag_stop.flag` in the project folder, which
_runner.py checks between batches. The runner finishes its current batch,
saves everything it has, and exits cleanly rather than being killed
outright - so a stopped run behaves like a paused one, not a crash.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from wt_models.env_utils import inference_python
from wt_models.downloader import ensure_model, model_dir


# ── Checkpoint / log / stop file locations ───────────────────────────────────
# All three live directly in the user's project folder, next to
# results.csv and wildtag_run_summary.txt, so they are easy to find.

def checkpoint_paths(project_dir: str) -> dict:
    proj = Path(project_dir)
    return {
        "checkpoint": proj / "wildtag_checkpoint.json",
        "log":        proj / "wildtag_run_log.txt",
        "stop":       proj / "wildtag_stop.flag",
    }


def checkpoint_status(project_dir: str) -> dict:
    """
    Look for a leftover checkpoint from a previous, unfinished run.
    Returns {"exists": bool, "count": int, "mtime": float or None}.
    """
    if not project_dir:
        return {"exists": False, "count": 0, "mtime": None}
    cp = checkpoint_paths(project_dir)["checkpoint"]
    if not cp.exists():
        return {"exists": False, "count": 0, "mtime": None}
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
        return {"exists": True, "count": len(data), "mtime": cp.stat().st_mtime}
    except Exception:
        return {"exists": True, "count": 0, "mtime": cp.stat().st_mtime}


def clear_checkpoint(project_dir: str):
    """Remove any leftover checkpoint/log/stop files for a fresh run."""
    if not project_dir:
        return
    for p in checkpoint_paths(project_dir).values():
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def run_pipeline(
    image_paths:      list,
    classifier_id:    str,
    det_confidence:   float = 0.1,
    cls_confidence:   float = 0.6,
    geofence:         str = "",
    device:           str = "cpu",
    threads:          int = 4,
    project_dir:      str = "",
    log:              Callable = print,
    progress:         Callable = lambda d, t: None,
    stop_flag:        Callable = lambda: False,
    resume:           bool = False,
    checkpoint_every: int = 200,
) -> tuple:
    """
    Run detection + classification on a list of image paths.
    Spawns a subprocess in the bundled Python environment.
    Each classifier brings its own detector:
      - DeepFaune: uses bundled deepfaune_detector.pt (YOLOv8s)
      - SpeciesNet: uses its own internal pipeline

    Returns (results, stopped):
      results  - list of detection dicts matching wildtag CSV column structure
                 (includes anything recovered from a resumed checkpoint)
      stopped  - True if the run ended because stop_flag() returned True,
                 rather than finishing normally
    """

    log(f"\n-- Preparing classifier: {classifier_id}")
    ensure_model(classifier_id, log, progress)

    py      = inference_python()
    wt_root = Path(__file__).parent.parent
    runner  = Path(__file__).parent / "_runner.py"

    if py is None:
        raise FileNotFoundError(
            "wildtag_env not found. This is a validation-only build "
            "and cannot run the AI pipeline. "
            "Please use the full wildtag.ai installation to process images.")

    log(f"\n-- Python: {py}")
    log(f"-- Runner: {runner}")

    if not runner.exists():
        raise FileNotFoundError(
            f"_runner.py not found at {runner}. "
            f"Make sure the wt_models folder is complete.")

    paths           = checkpoint_paths(project_dir) if project_dir else {}
    checkpoint_file = str(paths["checkpoint"]) if paths else ""
    log_file        = str(paths["log"])        if paths else ""
    stop_file       = str(paths["stop"])        if paths else ""

    if project_dir and not resume:
        # Fresh run - clear anything left over from a previous attempt
        clear_checkpoint(project_dir)
    elif project_dir:
        # Resuming - a stale stop flag would make the runner exit immediately
        try:
            paths["stop"].unlink()
        except FileNotFoundError:
            pass

    # If resuming, skip images already recorded in the checkpoint so the
    # runner doesn't redo work (and doesn't create duplicate rows).
    if resume and checkpoint_file and Path(checkpoint_file).exists():
        try:
            done_rows  = json.loads(Path(checkpoint_file).read_text(encoding="utf-8"))
            done_paths = {r.get("relative_path", "") for r in done_rows}
        except Exception:
            done_paths = set()

        if done_paths:
            images_dir = Path(project_dir) / "images"

            def _rel(p):
                try:
                    return str(Path(p).relative_to(images_dir)).replace("\\", "/")
                except ValueError:
                    return Path(p).name

            before      = len(image_paths)
            image_paths = [p for p in image_paths if _rel(p) not in done_paths]
            log(f"-- Resuming: {len(done_paths):,} images already done in "
                f"the previous run, {len(image_paths):,} of {before:,} remain", "ok")

    if not image_paths:
        log("-- Nothing left to process - resumed run was already complete.", "ok")
        results = []
        if checkpoint_file and Path(checkpoint_file).exists():
            try:
                results = json.loads(Path(checkpoint_file).read_text(encoding="utf-8"))
            except Exception:
                pass
        return results, False

    # Write image list to a temp file to avoid command-line length limits
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as f:
        f.write("\n".join(str(p) for p in image_paths))
        img_list_path = f.name

    output_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    output_file.close()
    output_path = output_file.name

    cmd = [
        str(py),
        str(runner),
        "--image-list",    img_list_path,
        "--classifier",    classifier_id,
        "--det-conf",      str(det_confidence),
        "--cls-conf",      str(cls_confidence),
        "--models-dir",    str(wt_root / "models"),
        "--wt-root",       str(wt_root),
        "--project-dir",   str(project_dir),
        "--output-file",   output_path,
        "--device",        device,
        "--threads",       str(threads),
    ]
    if geofence:
        cmd += ["--geofence", geofence]
    if checkpoint_file:
        cmd += ["--checkpoint-file",  checkpoint_file,
                 "--checkpoint-every", str(checkpoint_every)]
    if log_file:
        cmd += ["--log-file", log_file]
    if stop_file:
        cmd += ["--stop-file", stop_file]
    if resume:
        cmd.append("--resume")

    results = []
    stopped = False
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge so nothing is lost or reordered
            text=True,
            encoding="utf-8",
            errors="replace",           # SpeciesNet/tqdm output can contain
                                        # non-UTF-8 bytes (e.g. Windows-1252
                                        # dashes in progress bars); replace
                                        # them rather than crashing the reader
            bufsize=1,
        )

        # Read the subprocess's output on a background thread so the main
        # loop stays free to notice stop_flag() promptly, instead of
        # blocking on a single proc.communicate() call until the run ends.
        line_q = queue.Queue()

        def _reader():
            try:
                for raw in proc.stdout:
                    line_q.put(raw.rstrip())
            finally:
                line_q.put(None)  # sentinel: stream closed, process has exited

        threading.Thread(target=_reader, daemon=True).start()

        def _handle_stop_flag(stop_requested_at):
            """Touch the stop file the first time stop_flag() fires, and
            hard-kill the process if it hasn't exited a while after that."""
            if stop_flag() and stop_requested_at is None:
                stop_requested_at = time.time()
                log("\n-- Stop requested - finishing the current "
                    "batch and saving progress...", "skip")
                if stop_file:
                    Path(stop_file).touch()
            if (stop_requested_at is not None
                    and proc.poll() is None
                    and time.time() - stop_requested_at > 45):
                log("-- Not responding to the stop request - terminating.",
                    "warn")
                proc.terminate()
            return stop_requested_at

        stop_requested_at = None
        stream_open        = True
        while stream_open:
            try:
                line = line_q.get(timeout=0.2)
            except queue.Empty:
                stop_requested_at = _handle_stop_flag(stop_requested_at)
                continue

            if line is None:
                stream_open = False
                break
            if not line:
                pass
            elif line == "STOPPED":
                stopped = True
            elif line.startswith("PROGRESS:"):
                try:
                    done = int(line.split(":")[1])
                    progress(done, len(image_paths))
                except Exception:
                    pass
            elif line.startswith("ERROR"):
                log(line, "error")
            elif line.startswith("--"):
                log(line, "head")
            else:
                log(line, "plain")

            stop_requested_at = _handle_stop_flag(stop_requested_at)

        proc.wait()

        if stopped:
            log("\n-- Run stopped. Progress up to this point has been saved.",
                "skip")
        elif proc.returncode != 0:
            note = (f"\nPartial progress was saved to:\n{checkpoint_file}"
                    if checkpoint_file else "")
            raise RuntimeError(
                f"Inference subprocess exited with code {proc.returncode}. "
                f"See log above for details.{note}")

        # Read results from output file (holds partial results too, if stopped)
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content_str = f.read().strip()
            if content_str:
                results = json.loads(content_str)
                log(f"-- {len(results):,} detections loaded from results file", "ok")
            else:
                log("WARNING: Results file is empty - 0 detections", "skip")
                results = []
        except Exception as e:
            log(f"WARNING: Could not read results file: {e}", "skip")
            results = []

    finally:
        try:
            os.unlink(img_list_path)
        except Exception:
            pass
        try:
            os.unlink(output_path)
        except Exception:
            pass

    if not stopped and checkpoint_file:
        # Finished cleanly - the checkpoint has served its purpose
        clear_checkpoint(project_dir)

    log(f"\n-- Inference complete. {len(results):,} detections.", "ok")
    return results, stopped
