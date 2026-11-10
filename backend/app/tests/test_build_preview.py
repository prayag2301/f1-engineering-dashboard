"""A validated private mesh must never become a public or publishable release."""

import json
import shutil
import pytest
from PIL import Image
from app.services.releases import bootstrap_baseline, queue_build, build_preview, now
from app.services.local_builds import adopt_build
from app.services.validation import validate_release


def inspection_fixture(db, settings, monkeypatch, tmp_path):
    version = bootstrap_baseline(db, "mclaren")
    folder = tmp_path / "incoming"
    folder.mkdir()
    for name in ("build_car.py", "wing_profiles.py", "catalog.json"):
        shutil.copy2(settings.MODELING_ROOT / name, folder / name)
    shutil.copy2(
        settings.REFERENCE_ROOT / "regulations-2026.json", folder / "regulations.json"
    )
    (folder / "spec.json").write_text(
        json.dumps(
            {
                "team_key": version.team_key,
                "parameters": {
                    k: v["parameters"]
                    for k, v in version.manifest["components"].items()
                },
            }
        )
    )
    (folder / "geometry.json").write_text(
        json.dumps(
            {
                "generator_version": version.manifest["generator_version"],
                "component_hashes": {
                    k: "a" * 64 for k in version.manifest["components"]
                },
            }
        )
    )
    (folder / "source.blend").write_bytes(b"BLENDER fixture")
    (folder / "car.glb").write_bytes(b"validated inspection mesh")
    monkeypatch.setattr(
        "app.services.local_builds.validate_geometry", lambda *a: {"triangles": 42}
    )
    return version, folder


def test_imported_inspection_is_private_and_full_build_can_replace_it(
    client, db, settings, monkeypatch, tmp_path
):
    version, folder = inspection_fixture(db, settings, monkeypatch, tmp_path)
    adopt_build(db, version.id, folder, inspection_only=True)
    db.commit()
    assert version.status == "draft" and version.manifest["inspection_only"]
    assert not (settings.RELEASE_ROOT / str(version.id)).exists()
    url = version.manifest["assets"]["glb"]["url"]
    assert client.get(url).status_code == 404
    assert client.get("/api/v1/cars/mclaren/versions").json() == []
    client.headers["Authorization"] = "Bearer test-maintainer-token"
    assert client.get(url).content == b"validated inspection mesh"
    assert client.get(url).headers["cache-control"] == "private, no-store"
    dashboard = client.get("/api/v1/review/dashboard").json()
    assert dashboard["versions"][0]["manifest"]["inspection_only"]
    assert (
        client.post(f"/api/v1/review/versions/{version.id}/publish").status_code == 409
    )
    with pytest.raises(ValueError, match="not complete releases"):
        validate_release(folder, version.manifest)
    job = queue_build(db, version)
    db.commit()
    assert not version.manifest["assets"] and not version.manifest["inspection_only"]
    assert client.get(url).status_code == 200
    queued = client.get("/api/v1/review/dashboard").json()["versions"][0]
    assert queued["status"] == "building" and queued["manifest"]["inspection_only"]
    imported = settings.RELEASE_ROOT / ".inspections" / str(version.id) / "car.glb"
    original = imported.read_bytes()
    imported.write_bytes(b"tampered")
    assert client.get(url).status_code == 404
    imported.write_bytes(original)
    version.status = "failed"
    db.commit()
    assert build_preview(db, version)["manifest"]["inspection_only"]
    # Full adoption uses a separate destination and the full artifact gate.
    for prefix in ("preview_", "render_"):
        for view in ("front", "side", "rear", "three_quarter"):
            Image.new("RGB", (1, 1)).save(folder / f"{prefix}{view}.png")
    calls = []
    monkeypatch.setattr(
        "app.services.local_builds.validate_release",
        lambda *a: calls.append(a) or {"valid": True},
    )
    adopt_build(db, version.id, folder)
    db.commit()
    assert len(calls) == 1 and version.status == "ready"
    assert not version.manifest["inspection_only"] and job.status == "succeeded"
    assert (settings.RELEASE_ROOT / str(version.id) / "car.glb").is_file()


@pytest.mark.parametrize("fault", ["source", "fingerprints", "queued", "geometry"])
def test_invalid_inspection_never_becomes_available(
    db, settings, monkeypatch, tmp_path, fault
):
    version, folder = inspection_fixture(db, settings, monkeypatch, tmp_path)
    if fault == "source":
        (folder / "wing_profiles.py").write_text("changed source")
    elif fault == "fingerprints":
        p = folder / "geometry.json"
        data = json.loads(p.read_text())
        data["component_hashes"].pop("nose")
        p.write_text(json.dumps(data))
    elif fault == "queued":
        queue_build(db, version)
    else:

        def invalid(*args):
            raise ValueError("Invalid mesh")

        monkeypatch.setattr("app.services.local_builds.validate_geometry", invalid)
    with pytest.raises(ValueError):
        adopt_build(db, version.id, folder, inspection_only=True)
    assert not version.manifest.get("inspection_only")
    assert not (settings.RELEASE_ROOT / ".inspections" / str(version.id)).exists()


def preparing(db, settings, monkeypatch):
    version = bootstrap_baseline(db, "ferrari")
    job = queue_build(db, version)
    job.status, job.attempts, job.started_at = "running", 1, now()
    db.commit()
    stage = settings.RELEASE_ROOT / ".staging" / f"{job.id}-1"
    stage.mkdir(parents=True)
    (stage / "car.glb").write_bytes(b"validated mesh fixture")
    (stage / "geometry.json").write_text(
        json.dumps(
            {
                "generator_version": version.manifest["generator_version"],
                "component_hashes": {
                    key: "fixture" for key in version.manifest["components"]
                },
            }
        )
    )
    Image.new("RGB", (1920, 1080)).save(stage / "preview_three_quarter.png")
    (stage / "preview_side.png").write_bytes(b"incomplete PNG")
    monkeypatch.setattr(
        "app.services.validation.validate_geometry", lambda *a: {"triangles": 42}
    )
    return version, job, stage


def test_preview_is_private_and_cannot_publish(client, db, settings, monkeypatch):
    version, job, stage = preparing(db, settings, monkeypatch)
    manifest_before = json.dumps(version.manifest, sort_keys=True)
    url = f"/api/v1/review/versions/{version.id}/preview/{job.id}/1/car.glb"
    assert client.get(url).status_code in (401, 403)
    assert client.get("/api/v1/cars/ferrari/versions").json() == []
    client.headers["Authorization"] = "Bearer test-maintainer-token"
    dashboard = client.get("/api/v1/review/dashboard").json()
    preview = dashboard["versions"][0]
    assert preview["status"] == "building"
    assert preview["manifest"]["build_preview"] is True
    assert set(preview["manifest"]["assets"]) == {"glb", "preview_three_quarter"}
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert client.get(url.replace("car.glb", "source.blend")).status_code == 404
    assert (
        client.post(f"/api/v1/review/versions/{version.id}/publish").status_code == 409
    )
    assert json.dumps(version.manifest, sort_keys=True) == manifest_before
    # A stale browser may never fetch an old attempt after a retry.
    job.attempts = 2
    db.commit()
    assert client.get(url).status_code == 404


def test_partial_invalid_and_failed_exports_stay_unavailable(db, settings, monkeypatch):
    version, job, stage = preparing(db, settings, monkeypatch)
    (stage / "geometry.json").write_text('{"unfinished":')
    assert build_preview(db, version) is None
    (stage / "geometry.json").write_text(
        json.dumps(
            {
                "generator_version": version.manifest["generator_version"],
                "component_hashes": {},
            }
        )
    )

    def invalid(*args):
        raise ValueError("Invalid geometry")

    monkeypatch.setattr("app.services.validation.validate_geometry", invalid)
    assert build_preview(db, version) is None
    monkeypatch.setattr("app.services.validation.validate_geometry", lambda *a: {})
    job.status = "failed"
    db.commit()
    assert build_preview(db, version) is None


def test_preview_rejects_unannounced_component_changes(db, settings, monkeypatch):
    version, job, stage = preparing(db, settings, monkeypatch)
    parent = bootstrap_baseline(db, "ferrari", force_new=True)
    parent.status = "published"
    parent.manifest = {
        **parent.manifest,
        "component_hashes": {
            key: "parent geometry" for key in parent.manifest["components"]
        },
    }
    version.parent_id = parent.id
    version.manifest = {
        **version.manifest,
        "components": {
            key: {**value, "changed": False}
            for key, value in version.manifest["components"].items()
        },
    }
    db.commit()
    assert build_preview(db, version) is None
