"""
check_wildtag_version.py
========================
Quick sanity check that a wildtag.py is the latest cumulative version (with the
SQLite validation store) and not an older patched copy.

USAGE:
    python check_wildtag_version.py path\\to\\wildtag.py
    python check_wildtag_version.py            (checks wildtag.py in this folder)

It looks for markers that MUST be present in the new code and markers that MUST
be gone (the temporary "Sync validations" hack we removed).
"""

import sys
from pathlib import Path

# (label, substring) — all of these must be PRESENT
MUST_HAVE = [
    ("SQLite validation store module", "def val_db_upsert("),
    ("db-backed stats",                "def val_db_stats("),
    ("on-demand export",               "def val_db_export_csv("),
    ("first-open migration",           "def val_db_migrate_if_needed("),
    ("staleness check",                "def val_db_is_stale("),
    ("Export button handler",          "def _summary_export_results("),
    ("clean-close auto-export",        "def _on_app_close("),
    ("canvas confusion matrix",        "create_rectangle("),
    ("atomic export write",            "os.replace(tmp, master_csv)"),
    ("sqlite import",                  "sqlite3"),
]

# (label, substring) — all of these must be ABSENT (removed hacks / old code)
MUST_NOT_HAVE = [
    ("temporary Sync-validations handler", "def _val_sync_to_master("),
    ("Sync-validations button",            "Sync validations to results"),
    ("old big-CSV merge routine",          "def _val_merge_to_master("),
]


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("wildtag.py")
    if not target.exists():
        sys.exit(f"Not found: {target}")

    src = target.read_text(encoding="utf-8", errors="replace")

    print(f"Checking: {target.resolve()}")
    print(f"Size: {len(src):,} chars\n")

    ok = True

    print("Must be PRESENT:")
    for label, needle in MUST_HAVE:
        found = needle in src
        print(f"  [{'OK ' if found else 'MISSING'}] {label}")
        if not found:
            ok = False

    print("\nMust be ABSENT:")
    for label, needle in MUST_NOT_HAVE:
        absent = needle not in src
        print(f"  [{'OK ' if absent else 'STILL PRESENT'}] {label}")
        if not absent:
            ok = False

    print()
    if ok:
        print("RESULT: PASS - this is the latest cumulative wildtag.py.")
        sys.exit(0)
    else:
        print("RESULT: FAIL - this is NOT the latest version. Do not commit/build "
              "it; replace it with the newest wildtag.py first.")
        sys.exit(1)


if __name__ == "__main__":
    main()
