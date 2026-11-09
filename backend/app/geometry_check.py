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


def check_wing_attachments(scene, records):
    surfaces = {}
    for record in records:
        for key in ("part", "surface"):
            name = record[key]
            if name not in surfaces:
                parts = []
                for node in scene.graph.nodes_geometry:
                    if node == name or node.startswith(name + "_"):
                        transform, geom = scene.graph[node]
                        part = scene.geometry[geom].copy()
                        part.apply_transform(transform)
                        # Collapsed bevel-cap triangles make distance queries undefined.
                        part.update_faces(part.nondegenerate_faces())
                        parts.append(part)
                assert parts, f"Missing wing attachment mesh: {name}"
                surfaces[name] = trimesh.util.concatenate(parts)
            _, distance, _ = trimesh.proximity.closest_point_naive(
                surfaces[name], np.array([record["anchor"]])
            )
            assert distance[0] < 0.004, f"Detached wing support: {name} ({distance[0]})"


def check_wing_clearance(scene):
    """Compare actual exported skins along vertical rays through their overlap."""
    for component, names, spans in (
        (
            "front_wing",
            ("mainplane", "slot_flap_right", "upper_flap_right"),
            (0.21, 0.44, 0.71),
        ),
        (
            "rear_wing",
            ("spoon_mainplane", "slot_flap", "upper_flap"),
            (0.15, 0.35, 0.47),
        ),
    ):
        surfaces = []
        for name in names:
            transform, geom = scene.graph[component + "." + name]
            part = scene.geometry[geom].copy()
            part.apply_transform(transform)
            surfaces.append(part)
        for lower, upper in zip(surfaces, surfaces[1:]):
            zs = np.linspace(
                max(lower.bounds[0, 2], upper.bounds[0, 2]),
                min(lower.bounds[1, 2], upper.bounds[1, 2]),
                25,
            )
            origins = np.array([(x, 2.0, z) for x in spans for z in zs])
            directions = np.tile([0.0, -1.0, 0.0], (len(origins), 1))
            hits = []
            for surface in (lower, upper):
                points, indices, _ = surface.ray.intersects_location(
                    origins, directions
                )
                hits.append({i: points[indices == i, 1] for i in set(indices)})
            common = hits[0].keys() & hits[1].keys()
            assert common, f"No sampled wing overlap: {component}"
            gap = min(hits[1][i].min() - hits[0][i].max() for i in common)
            assert gap > 0.001, f"Intersecting {component} elements: {gap} m"
        plate_name = (
            "endplate.001" if component == "front_wing" else "curved_endplate.001"
        )
        transform, geom = scene.graph[component + "." + plate_name]
        plate = scene.geometry[geom].copy()
        plate.apply_transform(transform)
        plate.update_faces(plate.nondegenerate_faces())
        for surface in surfaces[1:] if component == "front_wing" else surfaces:
            tips = surface.vertices[
                abs(surface.vertices[:, 0] - surface.bounds[1, 0]) < 1e-5
            ]
            _, distance, _ = trimesh.proximity.closest_point_naive(plate, tips)
            assert (
                distance.min() < 0.004
            ), f"Detached {component} endplate: {distance.min()}"


def main():
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="f1-geometry-") as temporary:
        root = Path(temporary)
        hashes = {}
        shapes = {}
        cases = [(team, team, False) for team in catalog()["teams"]]
        cases.append(("revised", "ferrari", True))
        cases.extend(
            (team + "_wing_parameters", team, True)
            for team in ("mclaren", "racing_bulls")
        )
        for name, team, change in cases:
            params = {
                key: dict(catalog()["teams"][team]["parameters"].get(key, {}))
                for key in catalog()["components"]
            }
            if change:
                params["front_wing"]["camber"] += 0.008
                if team in {"mclaren", "racing_bulls"}:
                    params["front_wing"]["chord"] += 0.012
                    params["front_wing"]["sweep"] += 0.008
                    params["rear_wing"]["chord"] += 0.012
                    params["rear_wing"]["camber"] += 0.004
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
            assert len(report["wing_attachments"]) == (
                24 if team in {"mclaren", "racing_bulls"} else 8
            )
            check_wing_attachments(scene, report["wing_attachments"])
            if team in {"mclaren", "racing_bulls"}:
                check_wing_clearance(scene)
                for prefix in ("rear_wing.pylon_upper_shoe", "rear_wing.pylon_lower_shoe", "rear_wing.pylon_mount_fastener"):
                    assert any(n.startswith(prefix) for n in scene.graph.nodes_geometry), prefix
                transform, geom = scene.graph["front_wing.endplate.001"]
                vertices = trimesh.transformations.transform_points(scene.geometry[geom].vertices, transform)
                assert np.ptp(vertices[:, 0]) > .015, "Front endplate lost its rolled rim"
            for tag in ("fl", "fr", "rl", "rr"):
                for detail in (
                    "rim_barrel",
                    "brake_rotor",
                    "rotor_bell",
                    "brake_caliper",
                    "valve",
                ):
                    prefix = f"wheels.{tag}_{detail}"
                    matching = [
                        n for n in scene.graph.nodes_geometry if n.startswith(prefix)
                    ]
                    assert matching, f"Missing exported wheel detail: {prefix}"
                    if detail in {"rim_barrel", "brake_rotor", "rotor_bell"}:
                        for node in matching:
                            _, geom = scene.graph[node]
                            surface = scene.geometry[geom]
                            assert surface.is_watertight and surface.volume > 0, node
                            assert (
                                surface.euler_number == 0
                            ), f"Wheel sleeve bore is closed: {node}"
                assert not any(
                    n.startswith(f"wheels.{tag}_rim_inset")
                    for n in scene.graph.nodes_geometry
                )
            for detail in (
                "steering_display",
                "steering_grip",
                "shoulder_harness",
                "harness_buckle",
            ):
                assert any(
                    n.startswith(f"chassis.{detail}")
                    for n in scene.graph.nodes_geometry
                ), detail
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
        for team in ("mclaren", "racing_bulls"):
            changed = {
                key
                for key in hashes[team]
                if hashes[team][key] != hashes[team + "_wing_parameters"][key]
            }
            assert changed == {"front_wing", "rear_wing"}, (team, changed)
        for component in ("front_wing", "rear_wing"):
            assert shapes["mclaren"][component] != shapes["racing_bulls"][component]
        print(
            "PASS: distinct pilot wing contours; scaled-wing supports stay attached and nine nonwing assemblies are identical."
        )
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
