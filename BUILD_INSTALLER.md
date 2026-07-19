# Building the wildtag.ai installer

This turns your wildtag.ai folder into a single **`wildtag_Setup.exe`** that
your users run to install, no unzipping the app,
no cmd window, a proper desktop icon with the wildtag logo.

## What the user experiences

1. They download and unzip `wildtag_installer.zip`, giving them
   `wildtag_Setup.exe` (a single file).
2. They double-click `wildtag_Setup.exe` -> a normal Windows installer
   wizard appears (with your logo), click Next a couple of times.
3. It installs, creates a desktop shortcut and Start Menu entry with the
   wildtag icon.
4. They click the icon -> wildtag opens, **no black cmd window at all**,
   and the taskbar icon is the wildtag logo (even when pinned).

No app folder to navigate, nothing to accidentally close.

## One-time setup on your dev machine

1. **Install Inno Setup** (free, tiny): https://jrsoftware.org/isdl.php
   Accept the defaults.

## Building the installer

1. Make sure these files are in your `wildtag.ai\` folder (the same folder
   as `wildtag.py`, `wildtag.ico`, `wildtag_env\`, `models\`, etc.):
   - `wildtag_installer.iss`
   - `wildtag_launch.vbs`
   - `wildtag.ico` (your logo, used for the shortcuts and setup icon)
2. If your folder is Dropbox-synced, **pause Dropbox** during the compile.
   Dropbox holding files open causes "the process cannot access the file
   because it is being used by another process" errors mid-build.
3. Right-click `wildtag_installer.iss` -> **Compile** (or open it in the
   Inno Setup Compiler and press **F9**).
4. It churns for a few minutes while it compresses the folder (~640 MB output).
5. When done, look in the new **`Output\`** subfolder. You'll have:
   - `wildtag_Setup.exe` (a single self-contained installer, ~640 MB)

   This one file is the installer. It must be distributed and
   kept **together** in the same folder for the install to work.

## What gets excluded (and why)

This is a **model-free** build: no model weights are bundled. The app
downloads whichever model the user picks from the Models screen on first
use, and caches it under `models\` for offline use thereafter.

The `.iss` `[Files]` section ships the whole folder EXCEPT:

- `models\*` — all model weights. None are bundled; every model (DeepFaune,
  SpeciesNet, and any future model) downloads on first use. The app creates
  `models\` itself at runtime, so it does not need to be shipped.
- `__pycache__\*`, `*.mp4` (demo videos), `.git\*`, `*.log` — dev/runtime
  cruft not needed to run the app.

> **Make sure the `.iss` matches.** For a truly model-free installer, the
> `[Files]` section must exclude all of `models\`, not just the SpeciesNet
> cache. If your `.iss` still only excludes
> `models\speciesnet-global\kagglehub_cache\*`, update its `Excludes` so the
> DeepFaune weights are not shipped either.

If you ever want a fully-bundled, offline-from-first-launch installer, ship
`models\` (run `build_env.py --bundle-models` first to populate it), but
expect a roughly 1.6 GB larger installer.

## Hosting the installer (Hugging Face)

For public distribution, zip the two Output files into one download and
host on Hugging Face:

1. Zip them:
   ```
   powershell "Compress-Archive -Path 'Output\wildtag_Setup.exe' -DestinationPath '%USERPROFILE%\Desktop\wildtag_installer.zip' -Force"
   ```
2. Create a public HF repo (e.g. `chrissuthy/wildtag-installer`) and upload
   `wildtag_installer.zip` to it.
3. The public download URL is then:
   `https://huggingface.co/chrissuthy/wildtag-installer/resolve/main/wildtag_installer.zip`
4. Tell users: download the zip (smaller now that no models are bundled;
   confirm the size after your first build), unzip, run `wildtag_Setup.exe`,
   and run it. On first launch they open the Models screen
   and download a model while connected to the internet.

## Notes and gotchas

- **Size**: with no weights bundled, the installer is much smaller than the
  old ~1.8 GB (the DeepFaune weights alone were ~1.1 GB). Most of the
  remaining size is the bundled Python runtime. Users then download their
  chosen model once (DeepFaune ~1.1 GB, or SpeciesNet ~500 MB) from the
  Models screen. Confirm the exact figure after your first model-free build.
- **Compression**: the `.iss` uses `Compression=lzma2/fast`. This installs
  much faster on the user's machine than `lzma2/max` for only a modest size
  increase. If you want the smallest possible download and don't mind slower
  installs, switch it back to `lzma2/max`.
- **Disk spanning**: `DiskSpanning=yes` + `DiskSliceSize=max` split the
  The model-free payload compresses to well under Inno's ~2 GB single-file
  cap, so the output is a single `.exe` with no `.bin` slices.
- **Install location**: defaults to `%LOCALAPPDATA%\wildtag.ai` (no admin
  rights; the app can write its settings/outputs next to itself). Installing
  to `Program Files` needs admin rights and can cause permission issues
  since wildtag writes files alongside itself.
- **Icons**: the shortcuts set `IconIndex: 0` and `AppUserModelID:
  "wildtag.ai.desktop.1"`, and `wildtag.py` sets the same AppUserModelID at
  runtime. Together these make the wildtag logo show on the shortcut, the
  running taskbar button, AND when pinned to the taskbar (Windows otherwise
  falls back to the Python icon for pythonw-launched apps). Windows caches
  icons aggressively, so when testing, uninstall the old build first and run
  `ie4uinit.exe -show` to clear the icon cache before reinstalling.
- **Windowless launch**: the shortcut runs `wildtag_launch.vbs`, which uses
  `pythonw.exe`. All of wildtag's subprocesses (model runner, SpeciesNet,
  nvidia-smi, pip) are launched with `CREATE_NO_WINDOW`, so no console
  window flashes during a run.
- **The GPU setup still works**: the installed app is a normal folder under
  the hood, so `setup_gpu.bat` and the automatic GPU install work as before.
- **Volunteers**: this installer is for the *full* app. Volunteer
  validate-only packages are still distributed as zips via the Distribute
  tab, that flow is unchanged.

## Updating the version number

Each time you cut a new release, bump this line near the top of
`wildtag_installer.iss` so the installer's displayed version matches your
git tag:

```
#define MyAppVersion "1.2"
```
