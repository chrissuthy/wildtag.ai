wildtag.ai - Camera Trap Image Processing
==========================================
Version 1.3 - July 2026

DOWNLOAD
  wildtag.ai installer:  https://huggingface.co/chrissuthy/wildtag-installer/resolve/main/wildtag_Setup.exe
  User manual (PDF):     see wildtag_manual.pdf (included with the app)

  wildtag now ships without any model bundled in, so the installer is
  smaller than before (about 670 MB to download, mostly the bundled Python
  runtime). You download the model you want from inside the app the first
  time you use it (see MODELS below).

  The installer is a single file, wildtag_Setup.exe.

REQUIREMENTS
  - Windows 10 or 11 (64-bit)
  - Disk space: the installer download is about 670 MB. After installing,
    the app uses roughly 2.8 GB (mostly the bundled Python runtime), plus the
    model you download (DeepFaune about 1.1 GB, or SpeciesNet about 500 MB).
    So allow about 4 GB once DeepFaune is installed.
  - An internet connection is needed to download the installer, and the
    first time you download a model. After a model is downloaded it works
    fully offline. DeepFaune, the recommended model for UK and European
    wildlife, runs offline once installed.

GETTING STARTED

  1. Download the installer
     Download wildtag_Setup.exe from the link above.

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

  4. Download a model (first time only)
     Open the Models tab. It lists the available models with their size
     and licence. While you are connected to the internet, click Download
     next to the model you want (DeepFaune is recommended, see MODELS).
     This happens once; the model is then stored on your computer and used
     offline from then on.

  5. Run your first job
     - Open the Run tab
     - Click Browse to select your image folder
     - Choose the model you downloaded
     - Click Run wildtag

  6. Validate and export results
     - Open the Validate tab, review predictions, and Mark batch complete
     - Validation is saved instantly as you work
     - On the Summary tab, click Export results to write results_with_ids.csv
       (wildtag also exports automatically when you close it). See Appendix C
       of the manual for how validation data is stored and kept safe.

MODELS

  wildtag does not come with a model built in. You choose and download one
  from the Models tab the first time you use the app. Each model is stored
  locally after its first download and then runs offline.

  DeepFaune v1.4 (recommended for UK and European wildlife)
     A fast, accurate classifier for UK and European species. Works fully
     offline once downloaded (about 1.1 GB). Runs well on any computer,
     with or without a graphics card. This is the best choice for most
     users.

  SpeciesNet (Google, global species classification)
     Covers 2000+ species worldwide (download about 500 MB). Choose this when
     you need global coverage or taxonomy-level results.

     Running the full global model can take a long time per image, especially
     on a computer without a graphics card (GPU). Setting a Geographic filter
     (your country) in the Run options is recommended: it narrows SpeciesNet
     to species from your region and substantially speeds up processing. A GPU
     also helps for very large projects.

  Some models (DeepFaune-UK, DeepFaune New England, DeepFauna Sub-Sahara)
  appear on the Models tab marked "Planned"; these are in development and
  cannot yet be downloaded.

  Each model includes its own animal detector, so it locates animals in
  each image before classifying them.

SHARING VALIDATION WITH VOLUNTEERS

  You can send batches of images to volunteers to check. On the Distribute
  tab, "Prepare zip packages" now creates image-only packages by default:
  each zip contains just the images and a small spreadsheet, so they are
  small and quick to send. Volunteers open them with the free wildtag
  Validate app, a single file you send them once. They click "Open folder",
  point it at the unzipped package, check the labels, and send back a small
  results file. See wildtag_manual.pdf (Distribute) for the full workflow.

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
  - If the Models tab shows a model as "Not installed" and you have no
    internet, connect to the internet once to download it. After that it
    works offline.
  - If a run is interrupted (for example, the computer restarts partway
    through), wildtag can resume where it left off. When you reopen the
    project, it will offer to finish building the validation folders.
  - If SpeciesNet is slow, set a Geographic filter (your country) in the
    Run options - it narrows the global model to your region's species and
    speeds up processing considerably. A GPU helps for very large projects.
