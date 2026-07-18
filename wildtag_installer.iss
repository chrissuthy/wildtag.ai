; ============================================================
;  wildtag.ai - Inno Setup installer script
; ------------------------------------------------------------
;  Builds a single wildtag_Setup.exe that installs the whole
;  wildtag.ai folder, creates Start Menu + desktop shortcuts
;  with the wildtag logo, and launches with NO console window.
;
;  HOW TO BUILD (one-time, on your dev machine):
;   1. Install Inno Setup (free): https://jrsoftware.org/isdl.php
;   2. Put this .iss file in your wildtag.ai\ folder, next to
;      wildtag.py, wildtag.ico, wildtag_env\, models\, etc.
;   3. Right-click this file -> "Compile", OR open it in the
;      Inno Setup Compiler and press F9.
;   4. Out pops Output\wildtag_Setup.exe - that's the single
;      file you send to users.
;
;  Users then just double-click wildtag_Setup.exe, click through
;  a normal installer, and get a desktop icon. No unzip, no cmd
;  window, no folder to navigate.
; ============================================================

#define MyAppName "wildtag.ai"
#define MyAppVersion "1.2"
#define MyAppPublisher "wildtag.ai"
#define MyAppExeName "wildtag_launch.vbs"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Install into the user's local app data by default (no admin rights
; needed, avoids Program Files permission issues with a writable app
; folder - wildtag writes settings/outputs next to itself)
DefaultDirName={localappdata}\wildtag.ai
DefaultGroupName=wildtag.ai
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
; Branding
SetupIconFile=wildtag.ico
UninstallDisplayIcon={app}\wildtag.ico
WizardStyle=modern
; Output
OutputBaseFilename=wildtag_Setup
; Compression choice is a trade-off. lzma2/max gives the smallest download
; but is slow to BOTH build and install (it has to decompress ~5GB on the
; user's machine). lzma2/fast decompresses much faster, so installs are
; far quicker, for a modest increase in download size. For a multi-GB app
; where install time is a real user pain point, fast is the better balance.
Compression=lzma2/fast
SolidCompression=yes
; This bundle is multi-GB (models + Python env), past Inno's ~2GB
; single-file cap. DiskSpanning=yes lets the output exceed that by
; splitting into slices; DiskSliceSize=max makes each slice as large as
; allowed so there are as few files as possible. The user still runs
; wildtag_Setup.exe; any extra .bin slices sit beside it and are used
; automatically. Distribute ALL the produced files together.
DiskSpanning=yes
DiskSliceSize=max
LZMAUseSeparateProcess=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Ship the wildtag.ai folder, but EXCLUDE things that shouldn't be bundled:
;  - ALL model weights (models\): this is a MODEL-FREE build. Every model
;    (DeepFaune, SpeciesNet, and any future model) downloads on first use
;    from the Models screen and is cached under models\ afterwards. The app
;    creates models\ itself at runtime, so nothing there needs shipping.
;  - __pycache__ (Python bytecode, regenerated automatically)
;  - demo .mp4 videos (large, not needed to run the app)
;  - the .git folder and log files (dev/runtime cruft)
Source: "*"; DestDir: "{app}"; \
    Excludes: "models\*,*\__pycache__\*,__pycache__\*,*.mp4,.git\*,*.log"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
; (The installer exe itself and this script are excluded automatically
;  if you build into an Output\ subfolder, which is the default.)

[Icons]
; Start Menu shortcut - points at the windowless VBS launcher, uses the logo.
; IconIndex: 0 forces the shortcut to use wildtag.ico rather than the default
; script-host (Python/WScript) icon that .vbs shortcuts otherwise inherit.
; AppUserModelID must match the AUMID the app sets at runtime
; (SetCurrentProcessExplicitAppUserModelID in wildtag.py). When they match,
; Windows keeps the shortcut and the running window associated, so the
; correct icon is used even when the app is PINNED to the taskbar. Without
; this, pinning falls back to the pythonw.exe (Python) icon.
Name: "{group}\wildtag.ai"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\wildtag.ico"; IconIndex: 0; WorkingDir: "{app}"; AppUserModelID: "wildtag.ai.desktop.1"
Name: "{group}\Uninstall wildtag.ai"; Filename: "{uninstallexe}"
; Desktop shortcut (optional task)
Name: "{userdesktop}\wildtag.ai"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\wildtag.ico"; IconIndex: 0; WorkingDir: "{app}"; AppUserModelID: "wildtag.ai.desktop.1"; Tasks: desktopicon

[Run]
; Offer to launch straight after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch wildtag.ai now"; Flags: nowait postinstall skipifsilent shellexec
