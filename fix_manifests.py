"""
fix_manifests.py  (run this via Fix validation folders.bat)
===========================================================
Repairs volunteer validation folders whose validation.csv lists more images
than are actually in the folder. That mismatch is what shows up as
"Image not found" tiles and a wrong "images remaining" count.

For each validation.csv it keeps only the rows whose image is present in the
same folder. It never touches the images, and it keeps any validating already
done. The original validation.csv is backed up to validation.csv.bak the first
time only. Safe to run more than once.
"""

import csv
import sys
from pathlib import Path

IMG_EXTS = (".jpg", ".jpeg", ".png")


def repair_one(csv_path):
    folder = csv_path.parent
    present = {p.name.lower() for p in folder.iterdir()
               if p.suffix.lower() in IMG_EXTS}

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows   = list(reader)

    if not fields or "image_name" not in fields:
        return ("skip", csv_path, len(rows), len(rows), "no image_name column")

    kept = [r for r in rows
            if Path(r.get("image_name", "")).name.lower() in present]

    if len(kept) == len(rows):
        return ("ok", csv_path, len(rows), len(kept), "already correct")

    backup = csv_path.with_suffix(".csv.bak")
    if not backup.exists():
        backup.write_bytes(csv_path.read_bytes())

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)

    return ("fixed", csv_path, len(rows), len(kept), "")


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    root = root.resolve()
    print(f"Checking folders in: {root}\n")

    # Skip the bundled Python environments; validation.csv never lives there.
    csvs = [c for c in sorted(root.rglob("validation.csv"))
            if "validate_env" not in c.parts]
    if not csvs:
        print("No validation folders found here.")
        print("Make sure this file is in the folder that contains the")
        print("...validation folders, then run it again.")
        return

    fixed = 0
    for csv_path in csvs:
        status, path, before, after, note = repair_one(csv_path)
        try:
            label = path.relative_to(root)
        except ValueError:
            label = path
        tag = {"fixed": "FIXED", "ok": " ok  ", "skip": "SKIP "}[status]
        extra = f"  ({note})" if note else ""
        print(f"[{tag}] {label}: {before} -> {after} images{extra}")
        if status == "fixed":
            fixed += 1

    print(f"\nDone. Repaired {fixed} folder(s), checked {len(csvs)}.")
    if fixed:
        print("A backup of each original was saved as validation.csv.bak.")
    print("\nYou can now close this window and open wildtag again.")


if __name__ == "__main__":
    main()
