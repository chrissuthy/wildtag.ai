"""
recover_results_with_ids.py
============================
Rebuilds results_with_ids.csv from results.csv using the SAME deterministic
hashing wildtag uses, so every image_id / detection_id comes out identical to
the originals. Your validation\\ files (keyed by detection_id) therefore re-link
exactly. This does NOT reprocess any images.

USAGE (from the project folder that contains results.csv):
    python recover_results_with_ids.py results.csv

It writes results_with_ids.csv next to the input. It refuses to overwrite an
existing results_with_ids.csv unless you pass --force, so back up / rename the
damaged one first.
"""

import sys, csv, hashlib, argparse
from pathlib import Path

csv.field_size_limit(10_000_000)


# --- EXACT copies of wildtag's ID hashing (do not change) --------------------
def _sha256_short(text, length=12):
    return hashlib.sha256(text.encode()).hexdigest()[:length]

def make_image_id(absolute_path, relative_path, datetime_original):
    raw = f"{absolute_path.strip()}|{relative_path.strip()}|{datetime_original.strip()}"
    return f"img_{_sha256_short(raw)}"

def make_detection_id(image_id, bbox_left, bbox_top, bbox_right, bbox_bottom):
    raw = f"{image_id}|{bbox_left}|{bbox_top}|{bbox_right}|{bbox_bottom}"
    return f"det_{_sha256_short(raw)}"
# -----------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="path to results.csv")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing results_with_ids.csv")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"Not found: {src}")

    out = src.parent / (src.stem + "_with_ids.csv")
    if out.exists() and not args.force:
        sys.exit(f"{out.name} already exists. Rename/back it up first, "
                 f"or re-run with --force.")

    with open(src, newline="", encoding="utf-8-sig") as f:
        reader     = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows       = list(reader)

    required = {"absolute_path", "relative_path",
                "bbox_left", "bbox_top", "bbox_right", "bbox_bottom"}
    missing = required - set(fieldnames)
    if missing:
        sys.exit(f"Input is missing columns: {missing}\nFound: {fieldnames}")

    new_cols   = [c for c in ("image_id", "detection_id") if c not in fieldnames]
    out_fields = new_cols + fieldnames

    n = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            img_id = make_image_id(
                row.get("absolute_path", ""), row.get("relative_path", ""),
                row.get("DateTimeOriginal", ""))
            det_id = make_detection_id(
                img_id, row.get("bbox_left", ""), row.get("bbox_top", ""),
                row.get("bbox_right", ""), row.get("bbox_bottom", ""))
            row["image_id"] = img_id
            row["detection_id"] = det_id
            writer.writerow({k: row.get(k, "") for k in out_fields})
            n += 1

    print(f"Read  {len(rows):,} rows from {src.name}")
    print(f"Wrote {n:,} rows to {out.name}")
    if rows:
        print("Sample IDs (should match your originals):")
        r0 = rows[0]
        print(f"  image_id     = {r0['image_id']}")
        print(f"  detection_id = {r0['detection_id']}")
    print("\nDone. Next: put the fixed wildtag.py in place, open the project, "
          "and run a collect (or the merge) so your validation\\ work re-links "
          "by detection_id.")


if __name__ == "__main__":
    main()
