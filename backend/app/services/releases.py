"""Snapshot creation and publication. No mutable 'latest.glb' files."""

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.releases import (
    CarVersion,
    ComponentRevision,
    UpgradeCandidate,
    SourceDocument,
    BuildJob,
    ReleasePointer,
    ReviewAudit,
)
from app.schemas.releases import VersionInput
from app.services.catalog import catalog, content_hash, validate_parameters

VIEWS = ("front", "side", "rear", "three_quarter")


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def audit(db, action, target, detail=None):
    db.add(
        ReviewAudit(
            action=action, target_id=str(target), detail=jsonable_encoder(detail or {})
        )
    )


def source_public(source):
    return {
        "id": str(source.id),
        "url": source.url,
        "title": source.title,
        "publisher": source.publisher,
        "published_at": (
            source.published_at.isoformat() if source.published_at else None
        ),
        "retrieved_at": source.retrieved_at.isoformat(),
        "source_type": source.source_type,
        "event_name": source.event_name,
        "image_urls": source.image_urls,
        "rights": source.rights,
    }


def candidate_public(candidate, source=None):
    fields = (
        "team_key",
        "season",
        "component",
        "event_name",
        "summary",
        "supporting_passage",
        "page",
        "evidence_status",
        "representation",
        "status",
        "review_notes",
    )
    result = {key: getattr(candidate, key) for key in fields}
    result.update(
        id=str(candidate.id),
        source_id=str(candidate.source_id),
        observed_at=(
            candidate.observed_at.isoformat() if candidate.observed_at else None
        ),
    )
    result["legacy_upgrade_id"] = (
        str(candidate.legacy_upgrade_id) if candidate.legacy_upgrade_id else None
    )
    if source:
        result["source"] = source_public(source)
    return result


def version_public(version, current_id=None):
    return {
        "id": str(version.id),
        "team_key": version.team_key,
        "season": version.season,
        "label": version.label,
        "configuration_event": version.configuration_event,
        "configuration_kind": version.configuration_kind,
        "reverts_to_id": str(version.reverts_to_id) if version.reverts_to_id else None,
        "as_of": version.as_of.isoformat(),
        "evidence_cutoff": version.evidence_cutoff.isoformat(),
        "status": version.status,
        "parent_id": str(version.parent_id) if version.parent_id else None,
        "published_at": (
            version.published_at.isoformat() if version.published_at else None
        ),
        "is_current": current_id is not None and str(current_id) == str(version.id),
        "notes": version.notes,
        "component_revisions": version.component_revisions,
        "manifest": version.manifest,
        "visual_review": version.visual_review,
    }


def revision(db, team, season, component, parameters, sources, uncertainty):
    validate_parameters(component, parameters)
    source_ids = sorted(str(s) for s in sources)
    digest = content_hash(
        {
            "generator": catalog()["generator_version"],
            "parameters": parameters,
            "source_ids": source_ids,
            "uncertainty": uncertainty,
        }
    )
    record = (
        db.query(ComponentRevision)
        .filter_by(
            team_key=team, season=season, component=component, revision_hash=digest
        )
        .first()
    )
    if record:
        return record
    record = ComponentRevision(
        team_key=team,
        season=season,
        component=component,
        parameters=parameters,
        source_ids=source_ids,
        uncertainty=uncertainty,
        revision_hash=digest,
    )
    db.add(record)
    db.flush()
    return record


def create_version(db: Session, payload: VersionInput):
    if payload.as_of > now() or payload.evidence_cutoff > now():
        raise HTTPException(422, "Version dates cannot be in the future.")
    components = catalog()["components"]
    parent = None
    if payload.parent_id:
        parent = db.get(CarVersion, payload.parent_id)
        if (
            not parent
            or parent.status != "published"
            or parent.team_key != payload.team_key
            or parent.season != payload.season
        ):
            raise HTTPException(
                422, "The parent must be a published version of this team and season."
            )
        if payload.as_of < aware(parent.as_of):
            raise HTTPException(
                422,
                "New versions must not predate their parent; use rollback to select an earlier release.",
            )
    mapping = dict(parent.component_revisions) if parent else {}
    reversion = None
    if payload.configuration_kind == "reversion":
        reversion = (
            db.get(CarVersion, payload.reverts_to_id) if payload.reverts_to_id else None
        )
        if (
            not parent
            or not reversion
            or reversion.status != "published"
            or reversion.team_key != payload.team_key
            or reversion.season != payload.season
        ):
            raise HTTPException(
                422,
                "A reversion requires a published parent and a published target for the same team and season.",
            )
        if aware(reversion.as_of) > payload.as_of or payload.revisions:
            raise HTTPException(
                422,
                "Revert to an earlier complete configuration without additional shape revisions.",
            )
        mapping = dict(reversion.component_revisions)
    elif payload.reverts_to_id:
        raise HTTPException(
            422, "A reversion target requires configuration kind reversion."
        )
    if payload.configuration_kind == "no_change" and payload.revisions:
        raise HTTPException(422, "A no-change release cannot revise geometry.")
    reconstruction = payload.configuration_kind == "reconstruction"
    if reconstruction and (
        not parent
        or payload.as_of != aware(parent.as_of)
        or payload.configuration_event != parent.configuration_event
        or payload.candidate_ids
        or not payload.revisions
        or len(payload.notes.strip()) < 20
    ):
        raise HTTPException(
            422,
            "A reconstruction correction requires a published parent, the same observed date and event, explicit revisions and explanatory notes, without upgrade claims.",
        )
    records = []
    source_ids = set()
    changed = set()
    changes = []
    for candidate_id in dict.fromkeys(payload.candidate_ids):
        candidate = db.get(UpgradeCandidate, candidate_id)
        if (
            not candidate
            or candidate.status != "approved"
            or candidate.team_key != payload.team_key
            or candidate.season != payload.season
        ):
            raise HTTPException(
                422, "Every candidate must be approved for this team and season."
            )
        if not candidate.observed_at or aware(candidate.observed_at) > payload.as_of:
            raise HTTPException(
                422,
                "Candidate observation date must be on or before the configuration date.",
            )
        source = db.get(SourceDocument, candidate.source_id)
        if aware(source.published_at or source.retrieved_at) > payload.evidence_cutoff:
            raise HTTPException(
                422,
                "Candidate source was published or first retrieved after the evidence cutoff.",
            )
        records.append(candidate)
        source_ids.add(str(source.id))
        changes.append(candidate_public(candidate, source))
    for item in payload.revisions:
        if item.component in changed:
            raise HTTPException(422, "Supply each revised component only once.")
        for source_id in item.source_ids:
            source = db.get(SourceDocument, source_id)
            if not source:
                raise HTTPException(
                    422, "A component revision references an unknown source."
                )
            if (
                aware(source.published_at or source.retrieved_at)
                > payload.evidence_cutoff
            ):
                raise HTTPException(
                    422,
                    "Component evidence was published or first retrieved after the cutoff.",
                )
            source_ids.add(str(source_id))
        if (
            parent
            and not reconstruction
            and not any(
                c.component == item.component
                and c.representation == "modeled"
                and c.evidence_status == "confirmed"
                and c.source_id in item.source_ids
                for c in records
            )
        ):
            raise HTTPException(
                422,
                "Each changed shape needs an approved, confirmed modeled candidate for that component.",
            )
        try:
            record = revision(
                db,
                payload.team_key,
                payload.season,
                item.component,
                item.parameters,
                item.source_ids,
                item.uncertainty,
            )
        except ValueError as e:
            raise HTTPException(422, str(e))
        mapping[item.component] = str(record.id)
        changed.add(item.component)
    if set(mapping) != set(components):
        raise HTTPException(
            422, "A baseline must provide every component in the catalog."
        )
    if reversion:
        changed = {
            name
            for name, value in mapping.items()
            if parent.component_revisions.get(name) != value
        }
        if any(
            not any(
                c.component == name
                and c.evidence_status == "confirmed"
                and c.representation == "modeled"
                for c in records
            )
            for name in changed
        ):
            raise HTTPException(
                422,
                "Each reverted component needs approved evidence that the previous shape was fitted again.",
            )
    for candidate in records:
        if candidate.representation == "modeled" and candidate.component not in changed:
            raise HTTPException(
                422, "A modeled candidate needs an explicit component revision."
            )
        if (
            candidate.representation == "annotation_only"
            and candidate.component in changed
        ):
            raise HTTPException(
                422,
                "An annotation-only candidate cannot change the same component's shape.",
            )
    component_manifest = {}
    for name, revision_id in mapping.items():
        rec = db.get(ComponentRevision, UUID(revision_id))
        source_ids.update(rec.source_ids)
        component_manifest[name] = {
            "revision_id": revision_id,
            "label": components[name]["label"],
            "anchor": components[name]["anchor"],
            "parameters": rec.parameters,
            "source_ids": rec.source_ids,
            "uncertainty": rec.uncertainty,
            "changed": parent is not None
            and parent.component_revisions.get(name) != revision_id,
        }
    source_records = [db.get(SourceDocument, UUID(s)) for s in sorted(source_ids)]
    if any(
        aware(s.published_at or s.retrieved_at) > payload.evidence_cutoff
        for s in source_records
    ):
        raise HTTPException(
            422, "Inherited component evidence is newer than the requested cutoff."
        )
    version = CarVersion(
        team_key=payload.team_key,
        season=payload.season,
        label=payload.label,
        configuration_event=payload.configuration_event,
        configuration_kind=payload.configuration_kind,
        reverts_to_id=payload.reverts_to_id,
        as_of=payload.as_of,
        evidence_cutoff=payload.evidence_cutoff,
        parent_id=payload.parent_id,
        component_revisions=mapping,
        candidate_ids=[str(c.id) for c in records],
        notes=payload.notes,
        manifest={
            "schema_version": 1,
            "generator_version": catalog()["generator_version"],
            "reconstruction_correction": reconstruction,
            "units": "metres",
            "up_axis": "Y",
            "forward_axis": "-Z",
            "components": component_manifest,
            "sources": [source_public(s) for s in source_records],
            "changes": changes,
            "no_new_modeled_change": parent is not None
            and mapping == parent.component_revisions,
            "assets": {},
            "reconstruction_notice": "Exterior reconstruction from public references. Unseen surfaces and uncited dimensions are estimates.",
        },
    )
    db.add(version)
    db.flush()
    audit(db, "create_version", version.id)
    return version


def queue_build(db, version):
    if version.status == "published":
        raise HTTPException(
            409, "Published versions are immutable. Create a new draft."
        )
    pending = (
        db.query(BuildJob)
        .filter(
            BuildJob.version_id == version.id,
            BuildJob.status.in_(("queued", "running")),
        )
        .first()
    )
    if pending:
        return pending
    if version.status == "ready":
        raise HTTPException(
            409,
            "This version already has validated artifacts. Create a new draft for a rebuild.",
        )
    job = BuildJob(version_id=version.id, kind="build", status="queued")
    version.status = "building"
    version.visual_review = {}
    db.add(job)
    db.flush()
    audit(db, "queue_build", version.id, {"job_id": str(job.id)})
    return job


def artifact_path(version, filename):
    # The manifest is the only file allowlist; no arbitrary paths are served.
    permitted = {a["filename"] for a in version.manifest.get("assets", {}).values()}
    if filename not in permitted or Path(filename).name != filename:
        raise HTTPException(404, "Artifact not found.")
    path = get_settings().RELEASE_ROOT / str(version.id) / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact unavailable.")
    return path


def publish(db, version):
    if version.status != "ready":
        raise HTTPException(409, "Build and validate the draft before publishing.")
    if (
        not all(version.visual_review.get(view) for view in VIEWS)
        or not version.visual_review.get("reference_urls")
        or len(version.visual_review.get("notes", "")) < 20
    ):
        raise HTTPException(
            422, "Complete all four reference comparisons before publishing."
        )
    from app.services.validation import validate_release

    validation = validate_release(
        get_settings().RELEASE_ROOT / str(version.id), version.manifest
    )
    version.manifest = {**version.manifest, "validation": validation}
    version.status = "published"
    version.published_at = now()
    pointer = db.get(ReleasePointer, (version.team_key, version.season))
    if pointer:
        pointer.version_id = version.id
        pointer.updated_at = now()
    else:
        db.add(
            ReleasePointer(
                team_key=version.team_key, season=version.season, version_id=version.id
            )
        )
    audit(db, "publish", version.id)


def reconstruct_launch(db, parent):
    """Queueable modeling correction; never reinterpret a later race as a launch."""
    if not parent or parent.status != "published":
        raise HTTPException(422, "Select a published launch reference to correct.")
    info = catalog()["teams"][parent.team_key]
    launch_date = datetime.fromisoformat(info["baseline_date"].replace("Z", "+00:00"))
    if parent.season != 2026 or aware(parent.as_of) != launch_date:
        raise HTTPException(
            422, "The launch reconstruction cannot replace a later race configuration."
        )
    if parent.manifest.get("generator_version") == catalog()["generator_version"]:
        raise HTTPException(
            422,
            "This release already uses the current launch reconstruction. Use explicit component revisions for further corrections.",
        )
    return create_version(
        db,
        VersionInput(
            team_key=parent.team_key,
            parent_id=parent.id,
            label=f"{info['car_name']} · launch reconstruction {catalog()['generator_version']}",
            configuration_kind="reconstruction",
            configuration_event=parent.configuration_event,
            as_of=parent.as_of,
            evidence_cutoff=now(),
            notes="Reconstruction correction of the original launch configuration: separate team inlet, body-ramp, airbox and nose contours, plus a visible cockpit inner tub. This does not establish a new racing upgrade. Exact dimensions and hidden surfaces remain estimates.",
            revisions=[
                dict(
                    component=name,
                    parameters=parent.manifest["components"][name]["parameters"],
                    source_ids=parent.manifest["components"][name]["source_ids"],
                    uncertainty=note,
                )
                for name, note in info["component_notes"].items()
            ],
        ),
    )


def bootstrap_baseline(db, team, *, force_new=False):
    """Create an honestly dated draft, never an automatically published car."""
    info = catalog()["teams"][team]
    existing = (
        db.query(CarVersion)
        .filter_by(team_key=team, season=2026, parent_id=None)
        .order_by(CarVersion.created_at.desc())
        .first()
    )
    if existing and not force_new:
        return existing
    source = (
        db.query(SourceDocument).filter_by(canonical_url=info["source_url"]).first()
    )
    if not source:
        source = SourceDocument(
            url=info["source_url"],
            canonical_url=info["source_url"],
            content_hash=content_hash(info["notes"]),
            title=info["title"],
            publisher=info["publisher"],
            source_type="reference_gallery",
            published_at=datetime.fromisoformat(
                info["baseline_date"].replace("Z", "+00:00")
            ),
            event_name=info["event"],
            text=info["notes"],
            image_urls=info["reference_images"],
            pages=[],
        )
        db.add(source)
        db.flush()
    payload = VersionInput(
        team_key=team,
        label=f"{info['car_name']} · launch reference",
        configuration_event=info["event"],
        configuration_kind="baseline",
        as_of=info["baseline_date"],
        evidence_cutoff=now(),
        notes=info["notes"],
        revisions=[
            {
                "component": name,
                "parameters": info["parameters"].get(name, {}),
                "source_ids": [source.id],
                "uncertainty": info.get("component_notes", {}).get(
                    name,
                    "Visible exterior proportions reconstructed from launch photographs; exact dimensions and hidden surfaces are estimated. "
                    + info["notes"],
                ),
            }
            for name in catalog()["components"]
        ],
    )
    return create_version(db, payload)
