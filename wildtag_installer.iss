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
#define MyAppVersion "1.0"
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
Compression=lzma2/max
SolidCompression=yes
; This bundle is multi-GB (models + Python env). Inno's default output
; cap is 2GB; these let it produce one large setup file instead.
DiskSpanning=no
LZMAUseSeparateProcess=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Ship EVERYTHING in the wildtag.ai folder. Inno recurses subfolders.
; This picks up wildtag.py, wildtag.ico, wildtag_env\, validate_env\,
; models\, wt_models\, the .bat scripts, README, etc.
Source: "*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; (The installer exe itself and this script are excluded automatically
;  if you build into an Output\ subfolder, which is the default.)

[Icons]
; Start Menu shortcut - points at the windowless VBS launcher, uses the logo
Name: "{group}\wildtag.ai"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\wildtag.ico"; WorkingDir: "{app}"
Name: "{group}\Uninstall wildtag.ai"; Filename: "{uninstallexe}"
; Desktop shortcut (optional task)
Name: "{userdesktop}\wildtag.ai"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\wildtag.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Offer to launch straight after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch wildtag.ai now"; Flags: nowait postinstall skipifsilent shellexec
