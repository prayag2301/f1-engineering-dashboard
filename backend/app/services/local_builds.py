"""Adopt a native Blender build into a draft using the normal artifact gates."""

import json
import re
from pathlib import Path
import shutil
import tempfile
from app.config import get_settings
from app.models.releases import BuildJob, CarVersion
from app.services.catalog import catalog
from app.services.releases import now, audit, VIEWS
from app.services.validation import (
    sha256,
    validate_release,
    validate_component_history,
    validate_geometry,
)


def adopt_build(db, version_id, directory, *, inspection_only=False):
    version = db.query(CarVersion).filter_by(id=version_id).with_for_update().one()
    if version.status not in {"draft", "building", "failed"}:
        raise ValueError("Only an unfinished draft can adopt a local build.")
    jobs = (
        db.query(BuildJob)
        .filter_by(version_id=version.id, kind="build")
        .with_for_update()
        .all()
    )
    if any(job.status == "running" for job in jobs):
        raise ValueError("Wait for the active build worker before importing.")
    if inspection_only and any(job.status == "queued" for job in jobs):
        raise ValueError("Wait for the queued build before importing an inspection.")
    directory = Path(directory)
    spec = json.loads((directory / "spec.json").read_text())
    expected = {
        name: component["parameters"]
        for name, component in version.manifest["components"].items()
    }
    if (
        spec.get("team_key") != version.team_key
        or spec.get("season", 2026) != version.season
        or spec.get("parameters") != expected
    ):
        raise ValueError("Build specification does not match the draft.")
    frozen = json.loads((directory / "catalog.json").read_text())
    geometry = json.loads((directory / "geometry.json").read_text())
    if (
        geometry["generator_version"] != version.manifest["generator_version"]
        or frozen != catalog()
    ):
        raise ValueError("Build catalog/generator does not match the draft.")
    for name in ("build_car.py", "wing_profiles.py"):
        if sha256(directory / name) != sha256(get_settings().MODELING_ROOT / name):
            raise ValueError("Build source differs from the current frozen generator.")
    files = {
        "glb": "car.glb",
        "source": "source.blend",
        "geometry": "geometry.json",
        "spec": "spec.json",
        "builder": "build_car.py",
        "wing_profiles": "wing_profiles.py",
        "catalog": "catalog.json",
        "regulations": "regulations.json",
    }
    if not inspection_only:
        files.update(
            {
                prefix + view: prefix + view + ".png"
                for prefix in ("preview_", "render_")
                for view in VIEWS
            }
        )
    root = get_settings().RELEASE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    destination = (
        root / ".inspections" / str(version.id)
        if inspection_only
        else root / str(version.id)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError("Release directory already exists; do not overwrite it.")
    with tempfile.TemporaryDirectory(prefix=".native-", dir=root) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        for filename in files.values():
            shutil.copy2(directory / filename, stage / filename)
        # The frozen spec identifies the actual release being adopted.
        spec["version_id"] = str(version.id)
        (stage / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
        manifest = {
            **version.manifest,
            "inspection_only": inspection_only,
            "assets": {
                key: {
                    "filename": name,
                    "url": f"/api/v1/releases/{version.id}/{name}",
                    "sha256": sha256(stage / name),
                    "bytes": (stage / name).stat().st_size,
                }
                for key, name in files.items()
            },
            "component_hashes": geometry["component_hashes"],
            "built_at": now().isoformat(),
        }
        if version.parent_id:
            validate_component_history(
                manifest, db.get(CarVersion, version.parent_id).manifest
            )
        if inspection_only:
            hashes = geometry.get("component_hashes", {})
            if set(hashes) != set(expected) or any(
                not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
                for value in hashes.values()
            ):
                raise ValueError(
                    "Every inspection component needs a valid fingerprint."
                )
            if not (stage / "source.blend").read_bytes().startswith(b"BLENDER"):
                raise ValueError("The editable Blender scene is invalid.")
            manifest["validation"] = validate_geometry(
                stage / "car.glb", stage / "regulations.json"
            )
        else:
            manifest["validation"] = validate_release(stage, manifest)
        if inspection_only:
            (stage / "inspection.json").write_text(json.dumps(manifest, indent=2))
        stage.rename(destination)
    version.manifest = manifest
    version.status = "draft" if inspection_only else "ready"
    version.visual_review = {}
    for job in jobs:
        if not inspection_only and job.status in {"queued", "failed"}:
            job.status = "succeeded"
            job.finished_at = now()
            job.error = None
            job.result = {"adopted_native_build": True, **manifest["validation"]}
    audit(
        db,
        "import_inspection" if inspection_only else "adopt_native_build",
        version.id,
        manifest["validation"],
    )
    return version
