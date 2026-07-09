r"""
fix_shebangs.py
================
Repairs wildtag_env and validate_env after the whole wildtag.ai folder has
been moved, copied, or extracted somewhere new.

Why this is needed:
pip (and any other package that installs a console-script entry point,
like wheel, torchrun, yolo) writes a small wrapper next to python.exe in
Scripts. That wrapper is a compiled launcher plus a companion "-script.py"
file whose first line is a shebang, an absolute path to the python.exe
that existed at the moment the package was installed. If the folder is
later zipped up and extracted somewhere else, on this machine or a
different one, that path no longer exists and the wrapper fails with a
launcher error, even though python.exe itself works fine.

This script finds every such wrapper script under wildtag_env\Scripts and
validate_env\Scripts and rewrites its shebang to point at THIS folder's
python.exe. It never touches python.exe itself, and it is safe to run
as often as needed, it does nothing to a shebang that is already correct.

Run it directly:
    wildtag_env\\python.exe fix_shebangs.py
or via fix_shebangs.bat.
"""
import sys
from pathlib import Path


def fix_env(env_dir: Path) -> int:
    """Rewrite shebangs in env_dir\\Scripts\\*.py to point at env_dir\\python.exe.
    Returns the number of files fixed."""
    scripts_dir = env_dir / "Scripts"
    if not scripts_dir.exists():
        return 0

    python_exe = env_dir / "python.exe"
    if not python_exe.exists():
        print(f"  Skipping {env_dir.name}: no python.exe found there")
        return 0

    correct_shebang = f"#!{python_exe}\n"
    fixed = 0

    for script in scripts_dir.glob("*.py"):
        try:
            with open(script, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"  Could not read {script.name}: {e}")
            continue

        if not lines or not lines[0].startswith("#!"):
            continue
        if lines[0] == correct_shebang:
            continue

        old_shebang = lines[0].strip()
        lines[0] = correct_shebang

        try:
            with open(script, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"  Could not write {script.name}: {e}")
            continue

        fixed += 1
        print(f"  Fixed {script.name}")
        print(f"    was: {old_shebang}")
        print(f"    now: {correct_shebang.strip()}")

    return fixed


def main():
    root = Path(__file__).parent
    total = 0

    for env_name in ("wildtag_env", "validate_env"):
        env_dir = root / env_name
        if not env_dir.exists():
            continue
        print(f"Checking {env_name}...")
        found = fix_env(env_dir)
        if found == 0:
            print("  Nothing to fix.")
        total += found

    print(f"\nDone. Fixed {total} script(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
