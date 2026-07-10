# Building the wildtag.ai installer

This turns your wildtag.ai folder into a **`wildtag_Setup.exe`** (plus a
`.bin` payload file) that your users run to install, no unzipping the app,
no cmd window, a proper desktop icon with the wildtag logo.

## What the user experiences

1. They download and unzip `wildtag_installer.zip`, giving them
   `wildtag_Setup.exe` and a `.bin` file (kept together).
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
4. It churns for a few minutes while it compresses the multi-GB folder.
5. When done, look in the new **`Output\`** subfolder. You'll have:
   - `wildtag_Setup.exe` (a small launcher stub, ~7 MB)
   - `wildtag_Setup-1.bin` (the compressed payload, most of the size)

   Both files together are the installer. They must be distributed and
   kept **together** in the same folder for the install to work.

## What gets excluded (and why)

The `.iss` `[Files]` section ships the whole folder EXCEPT:

- `models\speciesnet-global\kagglehub_cache\*` — the SpeciesNet model files
  (~512 MB). These **download on demand** the first time a user selects
  SpeciesNet, so bundling them would just bloat the installer. DeepFaune's
  weights live elsewhere in `models\` and ARE shipped, so DeepFaune works
  out of the box.
- `__pycache__\*`, `*.mp4` (demo videos), `.git\*`, `*.log` — dev/runtime
  cruft not needed to run the app.

If you ever want SpeciesNet bundled again (e.g. for an offline audience),
remove the first exclude, but expect a ~512 MB larger installer.

## Hosting the installer (Hugging Face)

For public distribution, zip the two Output files into one download and
host on Hugging Face:

1. Zip them:
   ```
   powershell "Compress-Archive -Path 'Output\wildtag_Setup.exe','Output\wildtag_Setup-1.bin' -DestinationPath '%USERPROFILE%\Desktop\wildtag_installer.zip' -Force"
   ```
2. Create a public HF repo (e.g. `chrissuthy/wildtag-installer`) and upload
   `wildtag_installer.zip` to it.
3. The public download URL is then:
   `https://huggingface.co/chrissuthy/wildtag-installer/resolve/main/wildtag_installer.zip`
4. Tell users: download the zip (~1.8 GB, use wifi), unzip, run
   `wildtag_Setup.exe`, keeping the `.bin` beside it.

## Notes and gotchas

- **Size**: the installer is ~1.8 GB (was larger before excluding the
  SpeciesNet cache and demo videos). Installed size is ~3.8 GB. Most of it
  is the Python runtime and DeepFaune weights, unavoidable for the full app.
- **Compression**: the `.iss` uses `Compression=lzma2/fast`. This installs
  much faster on the user's machine than `lzma2/max` for only a modest size
  increase. If you want the smallest possible download and don't mind slower
  installs, switch it back to `lzma2/max`.
- **Disk spanning**: `DiskSpanning=yes` + `DiskSliceSize=max` split the
  payload past Inno's ~2 GB single-file cap, hence the `.bin` slice. For a
  ~1.8 GB payload there is usually just one `.bin`.
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
#define MyAppVersion "1.1"
```
