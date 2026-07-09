"""
run_enrich.py
=============
Runs ONLY the ID-enrichment step (enrich_csv) against your results.csv,
in isolation, so we can see exactly what it does and whether it drops
rows. Imports the real functions from wildtag.py, so it exercises the
same code the app uses, no reimplementation.

Run it from your project folder, or pass the path to results.csv:

    wildtag_env\\python.exe run_enrich.py > enrich_output.txt 2>&1
    wildtag_env\\python.exe run_enrich.py "S:\\...\\results.csv" > enrich_output.txt 2>&1

It writes results_with_ids.csv exactly as the app would (overwriting any
existing one), and reports the input and output row counts plus any error.
Open enrich_output.txt afterwards to read the result.
"""
import sys, csv, traceback
from pathlib import Path

csv.field_size_limit(1 << 24)


def main():
    # Locate wildtag.py (assume this script sits next to it, or in the
    # project; try a couple of sensible places)
    here = Path(__file__).parent
    candidates = [here / "wildtag.py",
                  here.parent / "wildtag.py"]
    wildtag_py = next((p for p in candidates if p.exists()), None)
    if not wildtag_py:
        # search nearby
        for p in here.rglob("wildtag.py"):
            wildtag_py = p
            break
    if not wildtag_py:
        print("Could not find wildtag.py. Put this script next to it.")
        return 1
    print(f"Using wildtag.py at: {wildtag_py}")

    sys.path.insert(0, str(wildtag_py.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("wildtag_mod", wildtag_py)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        # wildtag.py may call into tkinter at import if run as main; the
        # guard should prevent that, but just in case
        pass

    # Find results.csv
    if len(sys.argv) > 1:
        results = Path(sys.argv[1])
    else:
        results = wildtag_py.parent / "results.csv"
        if not results.exists():
            found = next(iter(Path.cwd().rglob("results.csv")), None)
            results = found or results
    if not results.exists():
        print(f"Could not find results.csv (looked at {results}). "
              f"Pass its path as an argument.")
        return 1
    print(f"Input results.csv: {results}")

    # Count input rows independently first
    def _count(path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            first = f.readline()
            delim = "\t" if "\t" in first else ","
            f.seek(0)
            return sum(1 for _ in csv.DictReader(f, delimiter=delim)), delim

    in_rows, delim = _count(results)
    print(f"Input row count (independent): {in_rows:,}  "
          f"(delimiter: {'TAB' if delim==chr(9) else 'comma'})")

    # Run the REAL enrich_csv with a simple logging function
    log_lines = []
    def log(msg, tag=""):
        log_lines.append(str(msg))

    print("\nRunning enrich_csv...")
    try:
        out_path = mod.enrich_csv(str(results), log)
    except Exception:
        print("\n*** enrich_csv RAISED AN EXCEPTION ***")
        traceback.print_exc()
        print("\nLog up to failure:")
        for ln in log_lines:
            print("  " + ln)
        return 1

    print("enrich_csv log:")
    for ln in log_lines:
        print("  " + ln)

    # Count output rows
    out_rows, _ = _count(out_path)
    print(f"\nOutput file: {out_path}")
    print(f"Output row count: {out_rows:,}")
    print(f"Input row count:  {in_rows:,}")
    if out_rows < in_rows:
        print(f"\n*** {in_rows - out_rows:,} ROWS LOST during enrichment. ***")
        print("    The loss is inside load_input/load_csv (the read), since")
        print("    enrich_csv writes every row it receives. The row count in")
        print("    the log above is len(rows) AFTER reading, if that already")
        print("    shows ~56K, the read is the culprit, not the write.")
    else:
        print("\nNo rows lost, enrichment preserved every input row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
