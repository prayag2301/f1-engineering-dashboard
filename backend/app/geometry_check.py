"""Real Blender export smoke test, runnable in the worker container without rendering."""

import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import trimesh
from app.config import get_settings
from app.services.catalog import catalog
from app.services.validation import validate_geometry


def main():
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="f1-geometry-") as temporary:
        root = Path(temporary)
        hashes = {}
        shapes = {}
        cases = [(team, team, False) for team in catalog()["teams"]]
        cases.append(("revised", "ferrari", True))
        for name, team, change in cases:
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
            scene = trimesh.load(out / "car.glb", force="scene")
            report = json.loads((out / "geometry.json").read_text())
            # Check the actual exported shell, not just the requested endpoints.
            # Each mount is embedded 4 mm; a detached arm must fail this check.
            mounts = report["suspension_attachments"]
            assert len(mounts) == 26
            for mount in mounts:
                parts = []
                for node in scene.graph.nodes_geometry:
                    if node == mount["surface"] or node.startswith(
                        mount["surface"] + "_"
                    ):
                        transform, geometry = scene.graph[node]
                        part = scene.geometry[geometry].copy()
                        part.apply_transform(transform)
                        parts.append(part)
                assert parts, f"Missing attachment surface: {mount['surface']}"
                shell = trimesh.util.concatenate(parts)
                _, distance, _ = trimesh.proximity.closest_point_naive(
                    shell, np.array([mount["anchor"]])
                )
                assert distance[0] < 0.006, f"Detached mount: {mount} ({distance})"
            assert not any(
                n.startswith("suspension.front_axle")
                for n in scene.graph.nodes_geometry
            )
            # Catch inside-out airfoils, accidentally bridged nose gaps and a
            # regression to the old flat floor / cylindrical edge construction.
            for node in scene.graph.nodes_geometry:
                transform, geometry = scene.graph[node]
                surface = scene.geometry[geometry]
                vertices = trimesh.transformations.transform_points(
                    surface.vertices, transform
                )
                if node.startswith(
                    ("front_wing.upper_flap", "rear_wing.spoon_mainplane")
                ):
                    assert surface.is_watertight and surface.volume > 0, node
                if node.startswith("front_wing.upper_flap_left"):
                    assert vertices[:, 0].max() < -0.10, "Flap crosses the nose gap"
                if node.startswith("front_wing.upper_flap_right"):
                    assert vertices[:, 0].min() > 0.10, "Flap crosses the nose gap"
                if node.startswith("floor.contoured_upper_surface"):
                    assert (
                        np.ptp(vertices[:, 1]) > 0.065
                    ), "Floor lost its upper contour"
            assert not any(
                node.startswith(("floor.edge_wing", "front_wing.tip_roll"))
                for node in scene.graph.nodes_geometry
            ), "Obsolete tubular aero geometry returned"
            points = []
            for node in scene.graph.nodes_geometry:
                if node.startswith(
                    ("sidepods.broad_shoulder", "sidepods.raised_rear_deck")
                ):
                    transform, geometry = scene.graph[node]
                    points.extend(
                        trimesh.transformations.transform_points(
                            scene.geometry[geometry].vertices, transform
                        )
                    )
            points = np.array(points)
            middle = points[(points[:, 2] > 0.75) & (points[:, 2] < 0.9), 1].max()
            rear = points[(points[:, 2] > 1.2) & (points[:, 2] < 1.3), 1].max()
            # Model silhouette checks, not measurements of a factory car.
            assert (
                rear - middle > 0.008 if team == "mercedes" else rear - middle < -0.03
            )
            hashes[name] = json.loads((out / "geometry.json").read_text())[
                "component_hashes"
            ]
            shapes[name] = json.loads((out / "geometry.json").read_text())[
                "shape_hashes"
            ]
            print(name, json.dumps(validation), flush=True)
        for component in ("sidepods", "engine_cover", "nose"):
            fingerprints = [shapes[team][component] for team in catalog()["teams"]]
            assert len(set(fingerprints)) == len(
                fingerprints
            ), f"Recoloured duplicate: {component}"
        print(
            "PASS: all eleven constructors have distinct nose, sidepod and engine-cover surfaces."
        )
        changed = {
            key
            for key in hashes["ferrari"]
            if hashes["ferrari"][key] != hashes["revised"][key]
        }
        assert changed == {"front_wing"}, f"Unexpected geometry changes: {changed}"
        print("PASS: one revised front wing; all ten other assemblies are identical.")
        for component in (
            "sidepods",
            "engine_cover",
            "nose",
            "front_wing",
            "floor",
            "rear_wing",
            "suspension",
            "diffuser",
        ):
            assert (
                shapes["ferrari"][component] != shapes["mercedes"][component]
            ), component
        print(
            "PASS: team-specific body, aero and surface-seated suspension; all 26 mounts contact the exported shell."
        )


if __name__ == "__main__":
    main()
