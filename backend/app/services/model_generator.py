"""Command-line entry point for the Blender source-of-truth pipeline."""

import argparse
import json
from pathlib import Path
import subprocess
from app.config import get_settings
from app.services.catalog import catalog


def generate_and_save(team_id: str, output_path: str | Path, season: int = 2026):
    if season != 2026 or team_id not in catalog()["teams"]:
        raise ValueError(
            "Only the Ferrari and Mercedes 2026 reference configurations are supported."
        )
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    info = catalog()["teams"][team_id]
    spec = {
        "team_key": team_id,
        "parameters": {
            name: info["parameters"].get(name, {}) for name in catalog()["components"]
        },
    }
    path = output / "spec.json"
    path.write_text(json.dumps(spec, indent=2))
    subprocess.run(
        [
            settings.BLENDER_BINARY,
            "--background",
            "--python-exit-code",
            "1",
            "--python",
            str(settings.MODELING_ROOT / "build_car.py"),
            "--",
            "--input",
            str(path),
            "--output",
            str(output),
        ],
        check=True,
    )
    return output / "car.glb"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", choices=["ferrari", "mercedes"], required=True)
    parser.add_argument(
        "--output", required=True, help="Output directory, not a GLB filename"
    )
    args = parser.parse_args()
    print(generate_and_save(args.team, args.output))
