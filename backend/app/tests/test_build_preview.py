"""A validated private mesh must never become a public or publishable release."""

import json
from PIL import Image
from app.services.releases import bootstrap_baseline, queue_build, build_preview, now


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
