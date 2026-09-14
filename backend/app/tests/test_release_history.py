from datetime import datetime, timezone, timedelta
from uuid import UUID
from unittest.mock import Mock
import json
import pytest
from fastapi import HTTPException
from PIL import Image
from app.models.releases import CarVersion, ReleasePointer, BuildJob
from app.schemas.releases import VersionInput, SourceImport
from app.services.releases import (
    bootstrap_baseline,
    create_version,
    reconstruct_launch,
    publish,
    queue_build,
    now,
    VIEWS,
)
from app.services.sources import import_source
from app.services.validation import validate_release, sha256
from app.services.validation import validate_component_history
from app import tasks


def test_modeled_claim_cannot_pass_with_unchanged_surfaces():
    parent = {"component_hashes": {"suspension": "same"}}
    draft = {
        "components": {"suspension": {"changed": True}},
        "component_hashes": {"suspension": "same"},
        "changes": [{"component": "suspension", "representation": "modeled"}],
    }
    with pytest.raises(ValueError, match="have not changed"):
        validate_component_history(draft, parent)
    draft["component_hashes"]["suspension"] = "revised"
    validate_component_history(draft, parent)
    draft["components"]["suspension"]["changed"] = False
    with pytest.raises(ValueError, match="explicit reviewed revision"):
        validate_component_history(draft, parent)


def approved_parent(db, monkeypatch):
    version = bootstrap_baseline(db, "ferrari")
    version.status = "ready"
    version.visual_review = {
        **dict.fromkeys(VIEWS, True),
        "reference_urls": ["https://fia.com/reference"],
        "notes": "Synthetic test fixture; never published outside this isolated database.",
    }
    monkeypatch.setattr(
        "app.services.validation.validate_release", lambda *a: {"valid": True}
    )
    publish(db, version)
    db.commit()
    return version


def candidate(db, representation="annotation_only"):
    _, rows, _ = import_source(
        db,
        SourceImport(
            url="https://fia.com/test-wing",
            text="Ferrari introduced a revised front wing endplate for the next event.",
            published_at="2026-03-01T00:00:00Z",
            event_name="Test event",
        ),
    )
    row = rows[0]
    row.status = "approved"
    row.evidence_status = "confirmed"
    row.representation = representation
    row.observed_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
    db.commit()
    return row


def next_payload(parent, **changes):
    data = dict(
        team_key="ferrari",
        label="Test event release",
        configuration_event="Test event",
        as_of="2026-03-02T00:00:00Z",
        evidence_cutoff=now(),
        parent_id=parent.id,
    )
    data.update(changes)
    return VersionInput(**data)


def test_annotation_only_copies_complete_configuration(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    claim = candidate(db)
    version = create_version(db, next_payload(parent, candidate_ids=[claim.id]))
    assert version.component_revisions == parent.component_revisions
    assert version.manifest["no_new_modeled_change"]
    assert version.manifest["changes"][0]["representation"] == "annotation_only"
    claim.summary = "A later correction"
    assert version.manifest["changes"][0]["summary"] != "A later correction"


def test_reconstruction_corrects_model_without_claiming_a_car_upgrade(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    original = json.loads(json.dumps(parent.manifest))
    item = parent.manifest["components"]["sidepods"]
    payload = next_payload(
        parent,
        configuration_kind="reconstruction",
        as_of=parent.as_of,
        configuration_event=parent.configuration_event,
        notes="Correct the inlet outline against the original launch gallery.",
        revisions=[
            dict(
                component="sidepods",
                parameters=item["parameters"],
                source_ids=item["source_ids"],
                uncertainty="Revised shoulder contour; dimensions remain visual estimates.",
            )
        ],
    )
    version = create_version(db, payload)
    assert version.manifest["reconstruction_correction"]
    assert version.manifest["changes"] == []
    assert version.status == "draft" and not version.visual_review
    assert (
        version.component_revisions["sidepods"]
        != parent.component_revisions["sidepods"]
    )
    assert version.component_revisions["wheels"] == parent.component_revisions["wheels"]
    assert parent.manifest == original
    for changes in (
        {"as_of": "2026-05-01T00:00:00Z"},
        {"configuration_event": "A different event"},
        {"candidate_ids": [candidate(db).id]},
        {"revisions": []},
        {"notes": ""},
        {"parent_id": None},
    ):
        with pytest.raises(HTTPException):
            create_version(db, VersionInput(**{**payload.model_dump(), **changes}))


def test_launch_correction_preserves_other_revisions_and_rejects_later_event(
    db, monkeypatch
):
    from app.services.catalog import catalog

    current_catalog = catalog()
    old_catalog = json.loads(json.dumps(current_catalog))
    old_catalog["generator_version"] = "2026.1"
    old_catalog["teams"]["ferrari"]["component_notes"] = {}
    monkeypatch.setattr("app.services.releases.catalog", lambda: old_catalog)
    parent = approved_parent(db, monkeypatch)
    monkeypatch.setattr("app.services.releases.catalog", lambda: current_catalog)
    version = reconstruct_launch(db, parent)
    revised = {
        key
        for key, value in version.component_revisions.items()
        if value != parent.component_revisions[key]
    }
    assert revised == {"chassis", "nose", "sidepods", "engine_cover"}
    assert version.configuration_kind == "reconstruction"
    assert version.candidate_ids == []
    version.status = "published"
    with pytest.raises(HTTPException, match="already uses"):
        reconstruct_launch(db, version)
    parent.as_of = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with pytest.raises(HTTPException, match="later race"):
        reconstruct_launch(db, parent)


def test_only_supported_component_revision_changes(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    claim = candidate(db, "modeled")
    params = {
        **parent.manifest["components"]["front_wing"]["parameters"],
        "camber": 0.06,
    }
    version = create_version(
        db,
        next_payload(
            parent,
            candidate_ids=[claim.id],
            revisions=[
                {
                    "component": "front_wing",
                    "parameters": params,
                    "source_ids": [claim.source_id],
                    "uncertainty": "Test reconstruction with explicitly reviewed wing camber.",
                }
            ],
        ),
    )
    changed = {
        c
        for c, r in version.component_revisions.items()
        if parent.component_revisions[c] != r
    }
    assert changed == {"front_wing"}
    assert not version.manifest["no_new_modeled_change"]


def test_shape_cannot_come_from_annotation_only_claim(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    claim = candidate(db)
    with pytest.raises(HTTPException):
        create_version(
            db,
            next_payload(
                parent,
                candidate_ids=[claim.id],
                revisions=[
                    {
                        "component": "front_wing",
                        "parameters": parent.manifest["components"]["front_wing"][
                            "parameters"
                        ],
                        "source_ids": [claim.source_id],
                        "uncertainty": "Not enough visual evidence to reconstruct this change.",
                    }
                ],
            ),
        )


def test_publication_requires_review_and_preserves_pointer_on_failure(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    version = create_version(db, next_payload(parent))
    version.status = "ready"
    db.commit()
    with pytest.raises(HTTPException):
        publish(db, version)
    version.visual_review = dict(parent.visual_review)
    monkeypatch.setattr(
        "app.services.validation.validate_release",
        Mock(side_effect=ValueError("Tampered artifact")),
    )
    with pytest.raises(ValueError):
        publish(db, version)
    assert db.get(ReleasePointer, ("ferrari", 2026)).version_id == parent.id
    assert parent.status == "published" and version.status == "ready"


def test_two_publications_and_rollback_keep_history(admin, db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    version = create_version(db, next_payload(parent))
    version.status = "ready"
    version.visual_review = dict(parent.visual_review)
    publish(db, version)
    db.commit()
    assert db.get(ReleasePointer, ("ferrari", 2026)).version_id == version.id
    response = admin.post(
        "/api/v1/review/cars/ferrari/rollback",
        json={
            "version_id": str(parent.id),
            "reason": "Restore the previous configuration after review.",
        },
    )
    assert response.status_code == 200, response.text
    versions = admin.get("/api/v1/cars/ferrari/versions").json()
    assert len(versions) == 2
    assert [v["id"] for v in versions if v["is_current"]] == [str(parent.id)]
    reviewed = admin.get("/api/v1/review/dashboard").json()["versions"]
    assert [v["id"] for v in reviewed if v["is_current"]] == [str(parent.id)]
    assert admin.get(f"/api/v1/review/versions/{parent.id}").json()["is_current"]
    assert not admin.get(f"/api/v1/review/versions/{version.id}").json()["is_current"]
    assert (
        admin.head("/api/v1/models/ferrari/latest.glb", follow_redirects=False)
        .headers["location"]
        .endswith(f"{parent.id}/car.glb")
    )
    with pytest.raises(HTTPException):
        queue_build(db, parent)


def test_evidence_after_cutoff_and_wrong_parent_are_rejected(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    claim = candidate(db)
    with pytest.raises(HTTPException):
        create_version(
            db,
            next_payload(
                parent, candidate_ids=[claim.id], evidence_cutoff="2026-02-01T00:00:00Z"
            ),
        )
    with pytest.raises(HTTPException):
        create_version(db, next_payload(parent, team_key="mercedes"))


@pytest.mark.parametrize(
    "moment,expected",
    [
        ("2026-03-23T08:59:00Z", "weekly:2026-03-16"),
        ("2026-03-23T09:00:00Z", "weekly:2026-03-23"),
        ("2026-03-30T08:00:00Z", "weekly:2026-03-30"),
        ("2026-10-26T08:59:00Z", "weekly:2026-10-19"),
        ("2026-10-26T09:00:00Z", "weekly:2026-10-26"),
    ],
)
def test_weekly_schedule_observes_berlin_dst(moment, expected):
    assert (
        tasks.scheduled_week(datetime.fromisoformat(moment.replace("Z", "+00:00")))
        == expected
    )


def test_recovery_has_one_catchup_and_rejects_old_lease(db, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=db.bind))
    dispatch = Mock()
    monkeypatch.setattr(tasks.execute_job, "apply_async", dispatch)
    job = BuildJob(
        kind="collect",
        status="running",
        attempts=1,
        heartbeat_at=now() - timedelta(minutes=6),
    )
    db.add(job)
    db.commit()
    tasks.tick()
    tasks.tick()
    db.expire_all()
    assert db.get(BuildJob, job.id).status == "queued"
    assert db.query(BuildJob).filter(BuildJob.schedule_key.is_not(None)).count() == 1
    with pytest.raises(tasks.LostLease):
        tasks.heartbeat(job.id, 1)


def test_artifact_gate_checks_editable_sources_and_all_render_sizes(tmp_path):
    manifest = {"assets": {}, "components": {}, "component_hashes": {}}
    names = {
        "glb": "car.glb",
        "source": "source.blend",
        "geometry": "geometry.json",
        "builder": "build_car.py",
        "catalog": "catalog.json",
        "regulations": "regulations.json",
        "spec": "spec.json",
    }
    for key, name in names.items():
        path = tmp_path / name
        path.write_text("synthetic test artifact")
        manifest["assets"][key] = {"filename": name, "sha256": sha256(path)}
    for prefix in ("preview_", "render_"):
        for view in VIEWS:
            key = prefix + view
            path = tmp_path / (key + ".png")
            Image.new(
                "RGB", (1920, 1080) if prefix == "preview_" else (3840, 2160)
            ).save(path)
            manifest["assets"][key] = {"filename": path.name, "sha256": sha256(path)}
    (tmp_path / "build_car.py").write_text("tampered")
    with pytest.raises(ValueError, match="builder"):
        validate_release(tmp_path, manifest)
    manifest["assets"]["builder"]["sha256"] = sha256(tmp_path / "build_car.py")
    image_path = tmp_path / "render_front.png"
    Image.new("RGB", (1920, 1080)).save(image_path)
    manifest["assets"]["render_front"]["sha256"] = sha256(image_path)
    with pytest.raises(ValueError, match="dimensions"):
        validate_release(tmp_path, manifest)


def test_annotation_build_reuses_every_parent_render_without_blender(
    db, settings, monkeypatch
):
    from sqlalchemy.orm import sessionmaker

    parent = approved_parent(db, monkeypatch)
    folder = settings.RELEASE_ROOT / str(parent.id)
    folder.mkdir()
    names = {
        "glb": "car.glb",
        "source": "source.blend",
        "geometry": "geometry.json",
        "builder": "build_car.py",
        "catalog": "catalog.json",
        "regulations": "regulations.json",
        "spec": "spec.json",
    }
    names.update(
        {
            prefix + view: prefix + view + ".png"
            for prefix in ("preview_", "render_")
            for view in VIEWS
        }
    )
    hashes = {key: "test-component-hash" for key in parent.component_revisions}
    for key, name in names.items():
        (folder / name).write_text(
            json.dumps({"component_hashes": hashes})
            if key == "geometry"
            else "frozen parent " + key
        )
    assets = {
        key: {"filename": name, "sha256": sha256(folder / name)}
        for key, name in names.items()
    }
    parent.manifest = {
        **parent.manifest,
        "assets": assets,
        "component_hashes": hashes,
        "generator_version": "earlier-frozen-generator",
    }
    db.commit()
    version = create_version(db, next_payload(parent))
    job = queue_build(db, version)
    job.status = "running"
    job.attempts = 1
    db.commit()
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=db.bind))
    process = Mock(
        side_effect=AssertionError("Annotation-only builds must not invoke Blender")
    )
    monkeypatch.setattr(tasks.subprocess, "Popen", process)
    result = tasks.build_version(job.id, version.id, 1)
    db.expire_all()
    assert (
        result["reused_geometry"] and db.get(CarVersion, version.id).status == "ready"
    )
    process.assert_not_called()
    assert (
        db.get(CarVersion, version.id).manifest["generator_version"]
        == "earlier-frozen-generator"
    )
    output = settings.RELEASE_ROOT / str(version.id)
    for key, name in names.items():
        if key != "spec":
            assert (folder / name).read_bytes() == (output / name).read_bytes()
    assert json.loads((output / "spec.json").read_text())["version_id"] == str(
        version.id
    )


def test_stale_draft_cannot_silently_use_a_new_generator(db, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    version = bootstrap_baseline(db, "ferrari")
    version.manifest = {**version.manifest, "generator_version": "obsolete-generator"}
    job = queue_build(db, version)
    job.status = "running"
    job.attempts = 1
    db.commit()
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=db.bind))
    process = Mock()
    monkeypatch.setattr(tasks.subprocess, "Popen", process)
    with pytest.raises(ValueError, match="different modeling generator"):
        tasks.build_version(job.id, version.id, 1)
    process.assert_not_called()


def test_failed_worker_and_manual_retry_preserve_current_release(
    admin, db, monkeypatch
):
    from sqlalchemy.orm import sessionmaker

    parent = approved_parent(db, monkeypatch)
    version = create_version(db, next_payload(parent))
    job = queue_build(db, version)
    db.commit()
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=db.bind))
    monkeypatch.setattr(
        tasks,
        "build_version",
        Mock(side_effect=RuntimeError("CPU renderer interrupted")),
    )
    result = tasks.execute_job(str(job.id))
    db.expire_all()
    assert result["error"] == "CPU renderer interrupted"
    assert db.get(CarVersion, version.id).status == "failed"
    assert db.get(ReleasePointer, ("ferrari", 2026)).version_id == parent.id
    response = admin.post(f"/api/v1/review/jobs/{job.id}/retry")
    assert response.status_code == 202 and response.json()["status"] == "queued"


def test_explicit_reversion_restores_old_assembly_ids(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    claim = candidate(db, "modeled")
    params = {
        **parent.manifest["components"]["front_wing"]["parameters"],
        "camber": 0.06,
    }
    changed = create_version(
        db,
        next_payload(
            parent,
            candidate_ids=[claim.id],
            revisions=[
                {
                    "component": "front_wing",
                    "parameters": params,
                    "source_ids": [claim.source_id],
                    "uncertainty": "Reviewed synthetic wing configuration.",
                }
            ],
        ),
    )
    changed.status = "ready"
    changed.visual_review = dict(parent.visual_review)
    publish(db, changed)
    db.commit()
    reverted = create_version(
        db,
        next_payload(
            changed,
            configuration_kind="reversion",
            reverts_to_id=parent.id,
            candidate_ids=[claim.id],
        ),
    )
    assert reverted.component_revisions == parent.component_revisions
    assert reverted.reverts_to_id == parent.id
    assert reverted.manifest["components"]["front_wing"]["changed"]


def test_unknown_publication_date_uses_retrieval_cutoff(db, monkeypatch):
    parent = approved_parent(db, monkeypatch)
    _, rows, _ = import_source(
        db,
        SourceImport(
            url="https://fia.com/undated",
            text="Ferrari revised its front wing for the current configuration.",
        ),
    )
    row = rows[0]
    row.status = "approved"
    row.evidence_status = "reported"
    row.observed_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
    db.commit()
    with pytest.raises(HTTPException):
        create_version(
            db,
            next_payload(
                parent, candidate_ids=[row.id], evidence_cutoff="2026-03-02T00:00:00Z"
            ),
        )


def test_expired_final_attempt_cannot_demote_a_published_release(db, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    parent = approved_parent(db, monkeypatch)
    job = BuildJob(
        kind="build",
        version_id=parent.id,
        status="running",
        attempts=3,
        heartbeat_at=now() - timedelta(minutes=6),
    )
    db.add(job)
    db.commit()
    monkeypatch.setattr(tasks, "SessionLocal", sessionmaker(bind=db.bind))
    monkeypatch.setattr(tasks.execute_job, "apply_async", Mock())
    tasks.tick()
    db.expire_all()
    assert db.get(BuildJob, job.id).status == "failed"
    assert db.get(CarVersion, parent.id).status == "published"
    assert db.get(ReleasePointer, ("ferrari", 2026)).version_id == parent.id
