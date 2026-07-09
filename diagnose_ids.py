"""
diagnose_ids.py
===============
Finds out why results_with_ids.csv has far fewer rows than results.csv.

Run it from your project folder (the one containing results.csv), or pass
the path to results.csv as an argument:

    wildtag_env\\python.exe diagnose_ids.py
    wildtag_env\\python.exe diagnose_ids.py "S:\\...\\CC_2026_May\\results.csv"

It reads results.csv three different ways and reports the row count each
way, then checks for the specific things that silently truncate a CSV
(embedded nulls, stray quotes, delimiter confusion, duplicate IDs). It
does NOT modify any of your files.
"""
import sys, csv, io
from pathlib import Path
from collections import Counter

csv.field_size_limit(1 << 24)  # allow very large fields


def find_results(argv):
    if len(argv) > 1:
        return Path(argv[1])
    here = Path(__file__).parent
    for name in ("results.csv", "results_with_ids.csv"):
        p = here / name
        if p.exists():
            return here / "results.csv"
    # search one level down
    for p in here.rglob("results.csv"):
        return p
    return None


def raw_line_count(path):
    """Count physical lines (newlines), a rough upper bound on rows."""
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def null_byte_scan(path):
    """Find the first NUL byte, which truncates many CSV readers."""
    pos = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                return None
            idx = chunk.find(b"\x00")
            if idx != -1:
                return pos + idx
            pos += len(chunk)


def sniff_delim(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        first = f.readline()
    return "\t" if "\t" in first else ","


def count_via_dictreader(path, delim):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delim)
        fields = reader.fieldnames
        n = sum(1 for _ in reader)
    return n, fields


def count_via_manual_split(path, delim):
    """Count by splitting lines ourselves, ignoring CSV quoting. If this is
    much higher than the DictReader count, a quoting/newline issue is
    eating rows."""
    n = 0
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        next(f, None)  # header
        for line in f:
            if line.strip():
                n += 1
    return n


def main():
    path = find_results(sys.argv)
    if not path or not path.exists():
        print("Could not find results.csv. Pass its path as an argument.")
        return 1

    print(f"Analysing: {path}")
    print(f"File size: {path.stat().st_size / 1e6:.1f} MB\n")

    raw = raw_line_count(path)
    print(f"Physical lines in file (incl. header): {raw:,}")

    nul = null_byte_scan(path)
    if nul is not None:
        print(f"\n*** NUL BYTE found at byte offset {nul:,} ***")
        print("    This is very likely the truncation cause: many CSV")
        print("    readers stop or misparse at the first NUL byte.")
    else:
        print("No NUL bytes found.")

    delim = sniff_delim(path)
    print(f"\nDetected delimiter: {'TAB' if delim == chr(9) else 'comma'}")

    dr_count, fields = count_via_dictreader(path, delim)
    print(f"Rows via csv.DictReader (what wildtag uses): {dr_count:,}")

    manual = count_via_manual_split(path, delim)
    print(f"Rows via plain line split:                   {manual:,}")

    if dr_count < manual * 0.9:
        print("\n*** DictReader is losing rows vs a plain line count. ***")
        print("    This points to embedded quotes or newlines inside")
        print("    fields confusing the CSV parser.")

    # Try the OTHER delimiter to see if it's a delimiter mismatch
    other = "," if delim == "\t" else "\t"
    try:
        alt_count, _ = count_via_dictreader(path, other)
        print(f"\nRows if delimiter were {'comma' if other==',' else 'TAB'} "
              f"instead: {alt_count:,}")
        if alt_count > dr_count * 1.5:
            print("*** The delimiter guess may be WRONG. The file parses")
            print(f"    into many more rows as {'comma' if other==',' else 'TAB'}"
                  "-delimited. ***")
    except Exception as e:
        print(f"(couldn't test other delimiter: {e})")

    # Duplicate detection_id check, only if the columns exist
    if fields and "detection_id" in fields:
        print("\nChecking for duplicate detection_id values...")
        seen = Counter()
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=delim):
                seen[r.get("detection_id","")] += 1
        dupes = sum(c - 1 for c in seen.values() if c > 1)
        print(f"  Unique detection_ids: {len(seen):,}")
        print(f"  Rows lost if deduplicated by detection_id: {dupes:,}")

    print("\nDone. Send this output back to interpret the cause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
