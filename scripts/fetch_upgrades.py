#!/usr/bin/env python3
"""
Repo-root wrapper so this command works from the project root:
python scripts/fetch_upgrades.py [--season ... --max-entries ... --dry-run]
"""

from pathlib import Path
import runpy
import sys


if __name__ == "__main__":
    backend_script = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "api"
        / "backend"
        / "scripts"
        / "fetch_upgrades.py"
    )
    try:
        runpy.run_path(str(backend_script), run_name="__main__")
    except ModuleNotFoundError as exc:
        print(
            "Missing local Python dependency while running fetch_upgrades.py. "
            "Use the API container command instead: "
            "docker compose exec -T api python backend/scripts/fetch_upgrades.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
