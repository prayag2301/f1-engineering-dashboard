#!/usr/bin/env python3
"""Build frozen, editable constructor artifacts locally; does not publish."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / "modeling/catalog.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--teams", nargs="+", choices=list(catalog["teams"]), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--device", choices=["CPU", "METAL"], default="CPU")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--jobs", type=int, choices=[1, 2], default=1)
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args()
    if args.samples < 16:
        parser.error("Use at least 16 samples")
    args.output.mkdir(parents=True, exist_ok=True)

    def build(team):
        out = (args.output / team).resolve()
        out.mkdir(exist_ok=False)  # Never replace an earlier frozen build.
        for name in ["build_car.py", "catalog.json"]:
            shutil.copy2(ROOT / "modeling" / name, out / name)
        shutil.copy2(
            ROOT / "data/references/regulations-2026.json", out / "regulations.json"
        )
        spec = {
            "team_key": team,
            "season": 2026,
            "parameters": {
                key: catalog["teams"][team]["parameters"].get(key, {})
                for key in catalog["components"]
            },
        }
        (out / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
        command = [
            args.blender,
            "--background",
            "--python-exit-code",
            "1",
            "--python",
            str(out / "build_car.py"),
            "--",
            "--input",
            str(out / "spec.json"),
            "--output",
            str(out),
            "--samples",
            str(args.samples),
            "--device",
            args.device,
        ]
        if args.geometry_only:
            command.append("--geometry-only")
        print("Building", team, flush=True)
        with (out / "build.log").open("w") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        print("Finished", team, flush=True)

    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(build, args.teams))


if __name__ == "__main__":
    main()
