#!/usr/bin/env python3
"""
Repo-root wrapper so README command works:
python scripts/seed_regulations.py [--pdf ... --season ... --force]
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    backend_script = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "seed_regulations.py"
    runpy.run_path(str(backend_script), run_name="__main__")
