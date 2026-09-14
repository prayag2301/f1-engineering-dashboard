"""Real Blender export smoke test, runnable in the worker container without rendering."""

import json
from pathlib import Path
import subprocess
import tempfile
from app.config import get_settings
from app.services.catalog import catalog
from app.services.validation import validate_geometry


def main():
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="f1-geometry-") as temporary:
        root = Path(temporary)
        hashes = {}
        shapes = {}
        for name, team, change in (
            ("ferrari", "ferrari", False),
            ("mercedes", "mercedes", False),
            ("revised", "ferrari", True),
        ):
            params = {
                key: dict(catalog()["teams"][team]["parameters"].get(key, {}))
                for key in catalog()["components"]
            }
            if change:
                params["front_wing"]["camber"] += 0.008
            spec = root / (name + ".json")
            spec.write_text(json.dumps({"team_key": team, "parameters": params}))
            out = root / name
            command = [
                settings.BLENDER_BINARY,
                "--background",
                "--python-exit-code",
                "1",
                "--python",
                str(settings.MODELING_ROOT / "build_car.py"),
                "--",
                "--input",
                str(spec),
                "--output",
                str(out),
                "--geometry-only",
            ]
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=180,
            )
            if result.returncode:
                raise RuntimeError(result.stdout[-4000:])
            validation = validate_geometry(out / "car.glb")
            hashes[name] = json.loads((out / "geometry.json").read_text())[
                "component_hashes"
            ]
            shapes[name] = json.loads((out / "geometry.json").read_text())[
                "shape_hashes"
            ]
            print(name, json.dumps(validation), flush=True)
        changed = {
            key
            for key in hashes["ferrari"]
            if hashes["ferrari"][key] != hashes["revised"][key]
        }
        assert changed == {"front_wing"}, f"Unexpected geometry changes: {changed}"
        print("PASS: one revised front wing; all ten other assemblies are identical.")
        for component in ("sidepods", "engine_cover", "nose"):
            assert (
                shapes["ferrari"][component] != shapes["mercedes"][component]
            ), component
        assert shapes["ferrari"]["suspension"] == shapes["mercedes"]["suspension"]
        print(
            "PASS: sidepods, engine cover and nose differ independently of their materials; common suspension is retained."
        )


if __name__ == "__main__":
    main()
