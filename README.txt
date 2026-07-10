wildtag.ai - Camera Trap Image Processing
==========================================
Version 1.1 - July 2026

DOWNLOAD
  wildtag.ai installer:  https://huggingface.co/chrissuthy/wildtag-installer/resolve/main/wildtag_installer.zip
  User manual (PDF):     see wildtag_manual.pdf (included with the app)

  The installer download is about 1.8 GB, so use wifi rather than mobile
  data where possible.

REQUIREMENTS
  - Windows 10 or 11 (64-bit)
  - About 4 GB of free disk space
  - An internet connection is needed only to download the installer, and
    (optionally) the first time you use the SpeciesNet model. DeepFaune,
    the recommended model for UK and European wildlife, works fully
    offline once installed.

GETTING STARTED

  1. Download and unzip the installer
     Download wildtag_installer.zip from the link above.
     Right-click it and select "Extract All".
     Inside you will find wildtag_Setup.exe and a .bin file. Keep these
     two together in the same folder.

  2. Run the installer
     Double-click wildtag_Setup.exe and follow the prompts.
     wildtag installs to your user account (no administrator rights are
     needed) and creates a desktop and Start Menu shortcut.
     If you see a Windows security warning, click "More info" then
     "Run anyway". This is normal for software that is not yet
     code-signed.

  3. Launch wildtag
     Open wildtag from the desktop shortcut or the Start Menu.
     The app opens directly, there is no console window.

  4. Run your first job
     - Click Browse to select your image folder
     - Choose a species classifier (see MODELS below)
     - Click Run wildtag

MODELS

  DeepFaune v1.4 (recommended for UK and European wildlife)
     Included and ready to use immediately, works offline. Fast on any
     computer. This is the best choice for most users.

  SpeciesNet (Google, global species classification)
     Covers species worldwide. It is a large model designed to run on a
     graphics card (GPU). The first time you select it, wildtag offers
     to download its model files (about 500 MB, one time only).

     Important: SpeciesNet is very slow on a computer without a GPU
     (often 10 or more seconds per image), so a large project could take
     many hours. If your computer has no GPU, DeepFaune is strongly
     recommended instead. wildtag will warn you about this when you
     select SpeciesNet.

  Both models use MegaDetector internally to locate animals in each
  image before classifying them.

DOCUMENTATION
  See wildtag_manual.pdf in the install folder for full instructions.

SUPPORT
  Contact: css6@st-andrews.ac.uk

TROUBLESHOOTING
  - If the app does not open, try reinstalling from the downloaded
    installer.
  - If you see a Windows security warning, click "More info" then
    "Run anyway". This is expected for software that is not yet
    code-signed.
  - If a run is interrupted (for example, the computer restarts partway
    through), wildtag can resume where it left off. When you reopen the
    project, it will offer to finish building the validation folders.
  - SpeciesNet running slowly is expected on computers without a GPU.
    Switch to DeepFaune for much faster results on UK and European
    wildlife.
