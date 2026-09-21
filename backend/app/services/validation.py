"""Geometry and artifact gates shared by builds and publication."""

import hashlib
import json
from pathlib import Path
import struct
import re

import numpy as np
from PIL import Image
import trimesh

from app.services.catalog import catalog
from app.config import get_settings


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_component_history(manifest, parent):
    for name, component in manifest["components"].items():
        if (
            not component["changed"]
            and manifest["component_hashes"][name] != parent["component_hashes"][name]
        ):
            raise ValueError(
                f"Unchanged component {name} has different surfaces; create an explicit reviewed revision."
            )
    for claim in manifest.get("changes", []):
        name = claim["component"]
        if (
            claim["representation"] == "modeled"
            and manifest["component_hashes"][name] == parent["component_hashes"][name]
        ):
            raise ValueError(
                f"{name} is marked as modeled, but its surfaces have not changed. Use annotation-only or revise the assembly."
            )


def validate_geometry(path, regulation_path=None):
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("Invalid GLB header.")
    version, total, size, kind = struct.unpack_from("<4I", data, 4)
    if version != 2 or total != len(data) or kind != 0x4E4F534A:
        raise ValueError("Invalid GLB structure.")
    gltf = json.loads(data[20 : 20 + size])
    nodes = gltf.get("nodes", [])
    components = {n.get("extras", {}).get("component") for n in nodes if "mesh" in n}
    if components != set(catalog()["components"]):
        raise ValueError("GLB component IDs do not match the catalog.")
    if not gltf.get("textures") or not gltf.get("materials"):
        raise ValueError("GLB lacks its packed textures/materials.")
    if any("bufferView" not in item for item in gltf.get("images", [])):
        raise ValueError("GLB textures must be embedded in the immutable asset.")
    regulations = json.loads(
        (
            regulation_path or get_settings().REFERENCE_ROOT / "regulations-2026.json"
        ).read_text()
    )
    rules = {
        r["parameter"]: r["value"] / 1000
        for r in regulations["constraints"]
        if r["unit"] == "mm"
    }
    scene = trimesh.load(path, force="scene", process=False)
    bounds = np.array(scene.bounds)
    if not np.isfinite(bounds).all() or bounds[0, 1] < -0.012:
        raise ValueError("Geometry is non-finite or extends below ground.")
    if (
        not 4.3 < scene.extents[2] < 5.6
        or not 1.6 < scene.extents[0] < 2.1
        or not 0.7 < scene.extents[1] < 1.2
    ):
        raise ValueError("Car proportions are invalid.")
    tyre_centres = {}
    nose_points = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        geom = scene.geometry[geom_name].copy()
        geom.apply_transform(transform)
        if node.startswith("nose.") and "impact_structure" in node:
            # glTF splits one mesh into primitives at material boundaries (e.g.
            # a yellow nose tip). Validate the complete impact structure.
            nose_points.extend(geom.vertices)
        if (
            node.startswith("wheels.")
            and "_tyre" in node
            and abs(geom.bounds[0, 1]) > 0.012
        ):
            raise ValueError("A tyre is not in contact with the ground.")
        if node.startswith("wheels.") and "_tyre" in node:
            tyre_centres[node] = geom.bounds.mean(axis=0)
        if (
            not node.startswith("wheels.")
            and abs(geom.vertices[:, 0]).max() > rules["max_body_half_width"] + 0.001
        ):
            raise ValueError("Body exceeds FIA C2.3.1 half-width envelope.")
    if not nose_points:
        raise ValueError("Nose impact structure is missing.")
    nose_bounds = np.array([np.min(nose_points, axis=0), np.max(nose_points, axis=0)])
    nose_extents = nose_bounds[1] - nose_bounds[0]
    if nose_extents[2] < nose_extents[1] * 2 or nose_bounds[:, 2].mean() > -1:
        raise ValueError("Nose must be longitudinal and point toward negative Z.")
    if len(tyre_centres) != 4:
        raise ValueError("Exactly four grounded tyre assemblies are required.")
    wheelbase = max(p[2] for p in tyre_centres.values()) - min(
        p[2] for p in tyre_centres.values()
    )
    if wheelbase > rules["max_wheelbase"] + 0.001:
        raise ValueError("Wheelbase exceeds the reviewed FIA reference.")
    triangles = sum(len(g.faces) for g in scene.geometry.values())
    return {
        "bounds_m": bounds.tolist(),
        "triangles": triangles,
        "glb_bytes": len(data),
        "component_count": len(components),
        "textures": len(gltf["textures"]),
        "wheelbase_m": wheelbase,
        "regulation_reference": regulations["id"],
        "coordinate_system": "metres; Y-up; nose -Z",
    }


def validate_release(directory: Path, manifest):
    required = {
        "glb",
        "source",
        "geometry",
        "builder",
        "catalog",
        "regulations",
        "spec",
    } | {
        prefix + view
        for prefix in ("preview_", "render_")
        for view in ("front", "side", "rear", "three_quarter")
    }
    assets = manifest.get("assets", {})
    if not required.issubset(assets):
        raise ValueError("The release is missing required artifacts.")
    for key, asset in assets.items():
        if Path(asset["filename"]).name != asset["filename"]:
            raise ValueError("Invalid artifact filename.")
        path = directory / asset["filename"]
        if (
            not path.is_file()
            or path.stat().st_size == 0
            or sha256(path) != asset["sha256"]
        ):
            raise ValueError(f"Artifact missing or changed: {key}")
        if key.startswith(("preview_", "render_")):
            with Image.open(path) as image:
                expected = (1920, 1080) if key.startswith("preview_") else (3840, 2160)
                if image.size != expected:
                    raise ValueError(f"Wrong render dimensions: {key}")
                image.verify()
    geometry = json.loads((directory / assets["geometry"]["filename"]).read_text())
    if geometry.get("component_hashes") != manifest.get("component_hashes"):
        raise ValueError("Component geometry hashes disagree with the manifest.")
    hashes = geometry["component_hashes"]
    if set(hashes) != set(catalog()["components"]) or any(
        not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
        for value in hashes.values()
    ):
        raise ValueError("Every component needs a valid surface fingerprint.")
    spec = json.loads((directory / assets["spec"]["filename"]).read_text())
    if spec.get("parameters") != {
        name: c["parameters"] for name, c in manifest["components"].items()
    }:
        raise ValueError("The editable build specification disagrees with the release.")
    if (
        not (directory / assets["source"]["filename"])
        .read_bytes()
        .startswith(b"BLENDER")
    ):
        raise ValueError("The editable Blender scene is invalid.")
    return validate_geometry(
        directory / assets["glb"]["filename"],
        directory / assets["regulations"]["filename"],
    )
