# Building the wildtag.ai installer

This turns your wildtag.ai folder into a single **`wildtag_Setup.exe`** that
your users double-click to install, no unzipping, no cmd window, a proper
desktop icon with the wildtag logo.

## What the user experiences

1. They receive one file: `wildtag_Setup.exe`.
2. They double-click it → a normal Windows installer wizard appears (with
   your logo), click Next a couple of times.
3. It installs, creates a desktop shortcut and Start Menu entry with the
   wildtag icon.
4. They click the icon → wildtag opens, **no black cmd window at all**.

No folder to navigate, nothing to accidentally close.

## One-time setup on your dev machine

1. **Install Inno Setup** (free, tiny): https://jrsoftware.org/isdl.php
   Accept the defaults.

## Building the installer

1. Make sure these two files are in your `wildtag.ai\` folder (the same
   folder as `wildtag.py`, `wildtag.ico`, `wildtag_env\`, `models\`, etc.):
   - `wildtag_installer.iss`
   - `wildtag_launch.vbs`
2. Make sure `wildtag.ico` is present in that folder (it's your logo, and
   the installer uses it for the shortcuts and the setup icon).
3. Right-click `wildtag_installer.iss` → **Compile**.
   (Or open it in the Inno Setup Compiler and press **F9**.)
4. It churns for a while, it's compressing the whole multi-GB folder,
   so this can take several minutes and the resulting file is large.
5. When done, look in the new **`Output\`** subfolder:
   **`Output\wildtag_Setup.exe`** is your finished installer.

That single `.exe` is what you distribute (Google Drive, hard drive, etc.).

## Notes and gotchas

- **Size**: the installer will be roughly the size of your zipped folder
  (several GB) because it bundles the Python runtime and model weights.
  That's unavoidable for the full app. It's still *one file* and far less
  intimidating than a folder to unzip.
- **Install location**: by default it installs to the user's
  `%LOCALAPPDATA%\wildtag.ai` (no admin rights needed, and the app can
  write its settings/outputs next to itself). If you'd rather it install
  to `Program Files`, change `DefaultDirName` in the `.iss` file, but note
  Program Files needs admin rights and can cause permission issues since
  wildtag writes files alongside itself.
- **The GPU setup still works**: the installed app is a normal folder
  under the hood, so `setup_gpu.bat` and the automatic GPU install work
  exactly as before. The installer changes only how it's delivered and
  launched, not how it runs.
- **Windowless launch**: the shortcut runs `wildtag_launch.vbs`, which
  uses `pythonw.exe` (windowless Python). If wildtag ever fails to start,
  it shows a small error dialog instead of vanishing silently.
- **Volunteers**: this installer is for the *full* app. Volunteer
  validate-only packages are still distributed as zips via the Distribute
  tab, that flow is unchanged. (You could make a separate small installer
  for volunteers later if the zip proves intimidating too, same process,
  pointed at a validate-only folder.)

## Updating the version number

Each time you cut a new release, bump this line near the top of
`wildtag_installer.iss`:

```
#define MyAppVersion "1.0"
```

so the installer's displayed version matches your git tag.
