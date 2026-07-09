"""
package_validate.py
Creates one validation bundle zip per species class, to send to collaborators.
Run from wildtag.ai with: validate_env/Scripts/python.exe package_validate.py
"""
import sys, os, zipfile, csv as csv_mod
from pathlib import Path

root = Path(__file__).parent

# Check validate_env exists
venv_py = root / "validate_env" / "Scripts" / "python.exe"
if not venv_py.exists():
    print("ERROR: validate_env not found.")
    print("Please run build_validate_env.bat first.")
    input("\nPress Enter to exit...")
    sys.exit(1)

print("=" * 50)
print("  wildtag.ai - Package Validation Bundles")
print("=" * 50)
print()
project_folder = input("Enter full path to project folder\n(containing validation\\): ").strip().strip('"')
project = Path(project_folder)

if not project.exists():
    print(f"\nERROR: Folder not found:\n  {project}")
    input("\nPress Enter to exit..."); sys.exit(1)

val_dir = project / "validation"
if not val_dir.exists():
    print(f"\nERROR: No validation\\ folder found in:\n  {project}")
    print("Please run a wildtag job with 'Prepare validation folder' enabled first.")
    input("\nPress Enter to exit..."); sys.exit(1)

project_name = project.name.replace(" ", "_")

# Create distribute folder next to validation
dist_dir = project / "distribute"
dist_dir.mkdir(exist_ok=True)

# Find species folders with unvalidated images
species_folders = []
for d in sorted(val_dir.iterdir()):
    if not d.is_dir():
        continue
    images = list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.png"))
    if not images:
        continue
    val_csv = d / "validation.csv"
    if val_csv.exists():
        with open(val_csv, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        pending = [r for r in rows if r.get("validated","").strip().lower() != "yes"]
        if pending:
            species_folders.append((d, len(images)))

if not species_folders:
    print("\nNo species folders with unvalidated images found.")
    input("\nPress Enter to exit..."); sys.exit(0)

print(f"\nFound {len(species_folders)} species folder(s) to package:")
for d, n in species_folders:
    print(f"  {d.name} ({n} images)")
print()

def add_app_files(zf, root):
    """Add the app, env and wt_models to a zip."""
    ve = root / "validate_env"
    for f in ve.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f):
            zf.write(f, Path("wildtag_validate") / "validate_env" / f.relative_to(ve))
    for fname in ["wildtag.py", "wildtag.ico", "wildtag_manual.pdf"]:
        p = root / fname
        if p.exists():
            zf.write(p, Path("wildtag_validate") / fname)
    # Use volunteer-specific README
    readme = root / "README_volunteer.txt"
    if readme.exists():
        zf.write(readme, Path("wildtag_validate") / "README.txt")
    elif (root / "README.txt").exists():
        zf.write(root / "README.txt", Path("wildtag_validate") / "README.txt")
    wt = root / "wt_models"
    for f in wt.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f):
            zf.write(f, Path("wildtag_validate") / "wt_models" / f.relative_to(wt))
    launcher = "@echo off\ncd /d \"%~dp0\"\nvalidate_env\\Scripts\\python.exe wildtag.py\n"
    zf.writestr("wildtag_validate/wildtag.bat", launcher)

for species_dir, n_images in species_folders:
    species_name = species_dir.name
    zip_name = dist_dir / f"wildtag_validate_{project_name}_{species_name}.zip"
    print(f"Packaging {species_name} ({n_images} images)...")

    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            add_app_files(zf, root)
            # Add this species folder only
            for f in species_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, Path("wildtag_validate") / "validation" / species_name / f.relative_to(species_dir))

        size_mb = zip_name.stat().st_size / 1_000_000
        print(f"  Created: {zip_name.name} ({size_mb:.0f} MB)")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

print(f"\nAll done. {len(species_folders)} zip(s) created in:")
print(f"  {dist_dir}")
input("\nPress Enter to exit...")
