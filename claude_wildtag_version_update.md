# wildtag.ai - version update and release steps

_One-page release checklist. Update the "What changed" section each release; the steps stay the same._

## What changed in this update

App (`wildtag.py`):

- **Model download SSL fix** (`wt_models/downloader.py`) - downloads now verify against certifi's trusted root certificates for both the Hugging Face and direct-download paths, fixing `SSL: CERTIFICATE_VERIFY_FAILED` on machines whose bundled Python cannot find the OS certificate store. Verification stays on (not disabled); this does not bypass networks that perform active SSL inspection.
- **Three definitive label columns** in `results_with_ids.csv`: `ai_label` (model prediction), `human_label` (human's species where validated - correction if changed, confirmed AI label if validated-unchanged, blank if not validated), and `best_label` (`human_label` if present, else `ai_label`). Written from the first processing pass and populated fully on Export.
- **`human_verified` column removed** - no longer created for new projects, and dropped from older files on their next Export (backward compatible; build forward clean).
- **Map label selector** - a "Labels" dropdown (Best available / AI prediction / Human validated) switches which representation colours the map. Under "Human validated", unvalidated detections show as "not validated" rather than disappearing. The map reads the exported master CSV, so Export before the map reflects new validations.
- **Two-finger / mouse-wheel scrolling fixed** across the whole app - scrolling is now driven by a single persistent global handler that routes to whichever scrollable region is under the pointer, removing the dead zones that appeared over labels, buttons, and the validation image tiles.

Docs:

- Project brief CSV-column list updated (new label columns in, `human_verified` out).

## Step 1 - Sanity-check the code

From the repo folder: `python check_wildtag_version.py wildtag.py` -> expect `RESULT: PASS`.

## Step 2 - Bump the version number (keep these three in sync)

- `wildtag.py`: search for the sidebar label `wildtag.ai  v0.1` and update it.
- `wildtag_installer.iss`: `#define MyAppVersion "0.2"`.
- `README.txt`: the `Version ...` line at the top.

## Step 3 - Commit and push (run in your terminal)

```
cd "C:\Users\css6\Dropbox\W\wildtag.ai"
git status                 # review what changed
git add wildtag.py wt_models\downloader.py ^
        README.txt ^
        wildtag_manual.html index.html quick_reference.html ^
        wildtag_installer.iss
git commit -m "SSL cert fix for model download; ai/human/best label columns + map selector; drop human_verified; global wheel-scroll fix"
git push
```

Do not commit `dist\`, `build\`, `validate_env\`, `wildtag_env\`, or `*.db` (the .gitignore should already skip these; check `git status` if unsure).

## Step 4 - Build

Pre-flight (both builds): **pause Dropbox** first, and confirm `wildtag_env\python.exe` is ~90 KB, not 0 bytes.

**4a. Full app installer** (`wildtag_Setup.exe`)
- Right-click `wildtag_installer.iss` -> Compile (or open in Inno Setup, press F9).
- Output: `Output\wildtag_Setup.exe` (~670 MB, model-free).

**4b. Standalone validator** (`wildtag_validate.exe`)
- Double-click `build_validate_exe.bat` (installs PyInstaller into `validate_env`/`wildtag_env`, then compiles `wildtag_validate.spec`).
- Output: `dist\wildtag_validate.exe`. Send this one file to each volunteer once; afterwards they only need the image-only zips from the Distribute tab.
- If PyInstaller fails, paste the error and we switch to a validate-only Inno installer instead.

Resume Dropbox once both builds finish.
