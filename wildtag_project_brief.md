# wildtag.ai — Project Brief

## What is wildtag.ai?

wildtag.ai is a Windows desktop application for processing camera trap images using AI species identification. It is built for field ecologists with no coding background. The target audience deploys camera traps across sites, collects tens of thousands to hundreds of thousands of images, and needs an automated pipeline to identify species before manual validation.

It is part of the UK Wildlife Observatory (UKWO) umbrella initiative alongside MammalWeb (mammalweb.org) and Conservation AI (conservationai.co.uk).

---

## Distribution

- **Format**: A folder (~4-5GB) distributed as a zip via Google Drive
- **Platform**: Windows only
- **Dependencies**: All bundled — no user installation required
- **Runtime**: `wildtag_env\` — a Python venv with PyTorch, ultralytics, Pillow etc.
- **Volunteer runtime**: `validate_env\` — a lightweight venv (~28MB) bundled in volunteer zips

### Distribution folder structure
```
wildtag.ai\
  wildtag.py               — main app
  wildtag.bat              — launcher (sets env vars, runs wildtag_env\python.exe wildtag.py)
  wildtag.ico
  wildtag_manual.pdf
  README.txt
  deployment_template.csv
  setup_gpu.bat            — installs CUDA PyTorch into wildtag_env
  setup_map.bat            — installs tkinterweb
  setup_validate_env.bat   — builds validate_env from embeddable Python
  build_dist.bat           — builds wildtag_dist\ and zips it
  models\
    deepfaune-v1.4\
      deepfaune_v1.4.pt       (1.2GB — ViT-Large DINOv2 classifier)
      deepfaune_detector.pt   (22MB — YOLOv8s detector)
    speciesnet-global\
      kagglehub_cache\        (SpeciesNet weights ~500MB)
  wildtag_env\             (~2.6GB Python venv)
  validate_env\            (~28MB minimal venv for volunteers)
  wt_models\               (Python inference modules)
```

---

## Project folder structure (user's data)

```
my_project\
  images\
    site1\   IMG_0001.JPG ...
    site2\   IMG_0001.JPG ...
  validation\          — created by wildtag, one subfolder per species
  distribute\          — volunteer zips go here
  collect\             — drop returned zips here
    processed\         — merged zips moved here (also removed from distribute\)
  camtrapdp\           — Camtrap DP export output
  deployment.csv       — required: locationName, latitude, longitude, deploymentStart, deploymentEnd
  results.csv
  results_with_ids.csv
  wildtag_run_summary.txt  — written on completion
```

The user browses to `my_project\` in the Run tab. wildtag finds `images\` automatically.

---

## Architecture

### Models
No MegaDetector. Each classifier brings its own detector.

**DeepFaune v1.4 (Europe)**
- Detector: `deepfaune_detector.pt` (YOLOv8s via ultralytics) — 38 classes: animal/person/vehicle
- Classifier: `deepfaune_v1.4.pt` (ViT-Large DINOv2, 38 species/groups)
- `wt_models/deepfaune_v1_4/detector.py` — supports `detect()` and `detect_batch()`
- `wt_models/deepfaune_v1_4/inference.py` — supports `predict()` and `predict_batch()`

**SpeciesNet Global v4.0.3a**
- Runs as complete subprocess: `python -m speciesnet.scripts.run_model`
- `handles_own = True` — bypasses detector/classifier loop entirely
- Outputs JSON parsed by `_parse_speciesnet_output()`
- Cache: `models/speciesnet-global/kagglehub_cache/` via `KAGGLEHUB_CACHE` env var

### Pipeline flow
1. `wildtag.py` — user selects project folder, model, thresholds, clicks Run
2. `wt_models/engine.py` — writes image list to temp file, launches `_runner.py` as subprocess, streams stdout line by line (real-time progress)
3. `wt_models/_runner.py` — loads model, runs batch detection (4 imgs/batch CPU, 8 GPU) + batch classification (16 crops/batch CPU, 32 GPU), writes JSON output
4. `wildtag.py` — reads JSON, writes `results.csv`, runs `enrich_csv()` → `results_with_ids.csv`, runs `sort_detections_counted()` → `validation\` folders
5. Writes `wildtag_run_summary.txt`

### Key `_runner.py` details
- `--project-dir` passed from engine so `project_root = project/images/` giving `relative_path = site1/IMG_0001.JPG` and `locationName = site1`
- Progress emitted as `PROGRESS:done:total` on stdout, streamed by engine
- log() writes to stdout (not stderr) so it streams through engine

### CSV columns (results_with_ids.csv)
`image_id`, `detection_id`, `absolute_path`, `relative_path`, `locationName`, `data_type`, `label`, `confidence`, `ai_label`, `human_label`, `best_label`, `detector_label`, `detector_confidence`, `cv_label`, `cv_confidence`, `cv_model`, `bbox_left`, `bbox_top`, `bbox_right`, `bbox_bottom`, `bbox_normalised`, `file_width`, `file_height`, EXIF fields, `correct_label`, `validated`

**Definitive label columns** (written from the first processing pass; populated fully on Export):
- `ai_label` — the model's predicted species (mirror of `label`)
- `human_label` — the human's species where validated: the correction if the label was changed, the confirmed AI label if validated and unchanged, blank if not validated
- `best_label` — `human_label` if present, otherwise `ai_label`

The obsolete `human_verified` column is no longer created, and is dropped from older files on their next Export.

---

## App Tabs

### Run wildtag
- Browse to `my_project\`
- Checks: `images\` exists, `deployment.csv` exists, sites align with deployment rows
- Model dropdown (DeepFaune / SpeciesNet)
- Confidence thresholds (det/cls)
- Image quality (Low/Medium/High → JPEG 40/65/85)
- Output option: sort images into species folders
- Real-time progress log
- Shows time estimate on start

### Validate
- No browse button — auto-detects `project\validation\` when tab is clicked
- Species dropdown auto-populated with unvalidated species
- Tile gallery (configurable cols, 100 images/batch)
- Click tile → correction dialog (sentence case labels, alphabetical within group)
- Ctrl+click → multi-select, apply correction to multiple images at once
- Label order: `[Unidentifiable, Empty]` → species A-Z → groups A-Z → special A-Z
- Auto-advance to next species when current is fully validated
- Sibling bboxes shown as thin muted boxes for other detections in same image
- Human detections pixelated (GDPR)

### Distribute
- **Part A**: Prepare volunteer zip packages from `validation\`
  - Max 250 images per zip
  - Batched as `roe_deer_001_validation.zip`, `roe_deer_002_validation.zip` etc.
  - Includes `wildtag.py`, `wt_models\`, `validate_env\`, `Run wildtag.bat`
  - Written to `project\distribute\`
- **Part B**: Collect returned zips from `project\collect\`
  - Merges validated rows into local validation CSVs
  - Moves processed zips to `collect\processed\`
  - Removes zip from `distribute\` (has been returned)
- **Part C**: Export Camtrap DP
  - Reads `deployment.csv` → `camtrapdp\deployments.csv`
  - Reads `results_with_ids.csv` → `camtrapdp\media.csv`, `camtrapdp\observations.csv`
  - Writes `camtrapdp\datapackage.json`

### Map
- No browse — auto-loads from current project
- Species filter dropdown (dynamic, updates summary cards)
- Summary cards: Sites / Detections / Species (all dynamic by filter)
- "Open map in browser" → Leaflet + OSM HTML written to temp file
- Map reads `camtrapdp/deployments.csv` first, falls back to `deployment.csv`
- Site matching uses `locationName` from `results_with_ids.csv`

### Summary
- Detection statistics from most recent run

---

## Colour system

```python
THEMES = {
    "light": { "forest": "#2D7A45", "canopy": "#1A2E1E", "white": "#FFFFFF", ... },
    "dark":  { "forest": "#4CAF72", "canopy": "#74C69D", "white": "#1E2B22", ... },
}
C = dict(THEMES["light"])  # mutable — swapped on theme change
```

Dark mode toggle in sidebar restarts the app with new theme stored in settings.

---

## Validate-only mode (volunteer package)

When `wildtag_env\` is absent, wildtag runs in validate-only mode:
- Run, Distribute, Map panes not built (avoids `wt_models` import)
- Only Validate and Summary shown
- Auto-detects `validation\` from same folder as `wildtag.py`
- Volunteer runs `Run wildtag.bat` which calls `validate_env\Scripts\python.exe wildtag.py`

---

## Settings

Stored in `%APPDATA%\wildtag\settings.json`:
- `theme`: `"light"` or `"dark"`
- `onboarding_shown`: `true` after first launch
- `gpu_upgrade_declined`: `true` if user declined GPU upgrade

GPU upgrade check runs on every launch. Returns early if `torch.cuda.is_available()` is True. Only suppressed permanently if `gpu_upgrade_declined` is set.

---

## Key label lists

```python
# DeepFaune label order
DEEPFAUNE_ALL_LABELS = (
    ["unidentifiable", "empty"]          # always first
    + sorted(_DEEPFAUNE_SPECIES)         # 27 species A-Z
    + sorted(_DEEPFAUNE_GROUPS)          # bird, cow, equid, lagomorph, micromammal, mustelid
    + sorted(_DEEPFAUNE_SPECIAL)         # golden_jackal, human, porcupine, muskrat, vehicle
)
```

Labels stored as `lowercase_underscore`. Displayed as sentence case in UI (`roe_deer` → `Roe deer`).

---

## Style rules
- No em dashes (use hyphens)
- No `max_long_edge` (removed — images saved at full resolution)
- Sentence case for species labels in UI
- `self._fonts["tile"]` for tile labels (13pt bold)
- All colours through `C` dict

---

## Known issues / pending
- SpeciesNet progress output is sparse (its internal logging is minimal)
- Map requires internet for OSM tiles
- validate_env needs `setup_validate_env.bat` run once before distribute works
- Processing 473k images takes ~1-2 days on CPU; GPU recommended for large datasets
