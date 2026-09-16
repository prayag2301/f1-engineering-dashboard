from datetime import datetime, timezone
import hmac
import json
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import COOKIE, require_admin, is_admin, signer
from app.config import get_settings
from app.database import get_db
from app.models.releases import (
    CarVersion,
    ReleasePointer,
    UpgradeCandidate,
    SourceDocument,
    BuildJob,
    ReviewAudit,
)
from app.schemas.releases import (
    Login,
    SourceImport,
    CandidateReview,
    VersionInput,
    VisualReview,
    Rollback,
)
from app.services.catalog import catalog
from app.services.releases import (
    candidate_public,
    version_public,
    source_public,
    create_version,
    queue_build,
    artifact_path,
    build_preview,
    publish,
    audit,
    now,
)
from app.services.sources import import_source, canonical_url

public = APIRouter()
admin = APIRouter(dependencies=[Depends(require_admin)])
auth = APIRouter()


def get_version(db, version_id):
    version = db.get(CarVersion, version_id)
    if not version:
        raise HTTPException(404, "Car version not found.")
    return version


def job_public(job):
    return {
        "id": str(job.id),
        "version_id": str(job.version_id) if job.version_id else None,
        "kind": job.kind,
        "status": job.status,
        "attempts": job.attempts,
        "error": job.error,
        "result": job.result,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def dispatch(job):
    # The scheduler also dispatches queued jobs. A broker outage never loses the DB job.
    try:
        from app.tasks import execute_job

        execute_job.apply_async(args=[str(job.id)], retry=False)
    except Exception:
        pass


@auth.post("/session")
def login(payload: Login, request: Request, response: Response):
    if (
        request.headers.get("x-f1-review") != "1"
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "Open the review screen to sign in.")
    serializer = signer()
    if not hmac.compare_digest(
        payload.token.encode(), get_settings().ADMIN_TOKEN.encode()
    ):
        raise HTTPException(401, "Incorrect review token.")
    response.set_cookie(
        COOKIE,
        serializer.dumps("maintainer"),
        max_age=43200,
        httponly=True,
        samesite="strict",
        secure=get_settings().COOKIE_SECURE,
        path="/",
    )
    return {"authenticated": True}


@auth.get("/session")
def session(request: Request):
    return {"authenticated": is_admin(request)}


@admin.delete("/session")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"authenticated": False}


@public.get("/cars/catalog")
def get_catalog():
    return {
        "teams": catalog()["teams"],
        "components": catalog()["components"],
        "season": 2026,
    }


@public.get("/cars/{team}/versions")
def versions(team: str, season: int = 2026, db: Session = Depends(get_db)):
    if team not in catalog()["teams"] or season != 2026:
        raise HTTPException(404, "Team/season not supported.")
    pointer = db.get(ReleasePointer, (team, season))
    records = (
        db.query(CarVersion)
        .filter_by(team_key=team, season=season, status="published")
        .order_by(CarVersion.as_of.desc(), CarVersion.created_at.desc())
        .all()
    )
    return [version_public(v, pointer.version_id if pointer else None) for v in records]


@public.get("/cars/{team}/versions/{version_id}")
def version_detail(team: str, version_id: UUID, db: Session = Depends(get_db)):
    version = get_version(db, version_id)
    if version.team_key != team or version.status != "published":
        raise HTTPException(404, "Published version not found.")
    pointer = db.get(ReleasePointer, (team, version.season))
    return version_public(version, pointer.version_id if pointer else None)


@public.api_route("/releases/{version_id}/{filename}", methods=["GET", "HEAD"])
def release_asset(
    version_id: UUID, filename: str, request: Request, db: Session = Depends(get_db)
):
    version = get_version(db, version_id)
    if version.status != "published" and not is_admin(request):
        raise HTTPException(404, "Published artifact not found.")
    path = artifact_path(version, filename)
    mime = {
        ".glb": "model/gltf-binary",
        ".png": "image/png",
        ".json": "application/json",
        ".blend": "application/octet-stream",
    }.get(path.suffix, "application/octet-stream")
    return FileResponse(
        path,
        media_type=mime,
        filename=filename,
        content_disposition_type="inline",
        headers={
            "Cache-Control": (
                "public, max-age=31536000, immutable"
                if version.status == "published"
                else "private, no-store"
            )
        },
    )


@public.api_route("/models/{team}/latest.glb", methods=["GET", "HEAD"])
def latest_model(team: str, season: int = 2026, db: Session = Depends(get_db)):
    pointer = db.get(ReleasePointer, (team, season))
    if not pointer:
        raise HTTPException(404, "No published car for this team and season.")
    return RedirectResponse(
        f"/api/v1/releases/{pointer.version_id}/car.glb",
        status_code=307,
        headers={"Cache-Control": "no-cache"},
    )


@admin.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    current = {(p.team_key, p.season): p.version_id for p in db.query(ReleasePointer)}

    def reviewed_version(version):
        value = version_public(version, current.get((version.team_key, version.season)))
        preview = build_preview(db, version)
        if preview:
            value["manifest"] = preview["manifest"]
        return value

    return {
        "versions": [
            reviewed_version(v)
            for v in db.query(CarVersion)
            .order_by(CarVersion.created_at.desc())
            .limit(100)
        ],
        "candidates": [
            candidate_public(c, db.get(SourceDocument, c.source_id))
            for c in db.query(UpgradeCandidate)
            .order_by(UpgradeCandidate.created_at.desc())
            .limit(200)
        ],
        "jobs": [
            job_public(j)
            for j in db.query(BuildJob).order_by(BuildJob.created_at.desc()).limit(50)
        ],
        "sources": [
            source_public(s)
            for s in db.query(SourceDocument)
            .order_by(SourceDocument.retrieved_at.desc())
            .limit(100)
        ],
        "audit": [
            {
                "action": a.action,
                "target_id": a.target_id,
                "detail": a.detail,
                "created_at": a.created_at.isoformat(),
            }
            for a in db.query(ReviewAudit)
            .order_by(ReviewAudit.created_at.desc())
            .limit(50)
        ],
    }


@admin.get("/versions/{version_id}")
def draft_detail(version_id: UUID, db: Session = Depends(get_db)):
    version = get_version(db, version_id)
    pointer = db.get(ReleasePointer, (version.team_key, version.season))
    return version_public(version, pointer.version_id if pointer else None)


@admin.get("/versions/{version_id}/preview/{job_id}/{attempt}/{filename}")
def draft_preview_asset(
    version_id: UUID,
    job_id: UUID,
    attempt: int,
    filename: str,
    db: Session = Depends(get_db),
):
    preview = build_preview(db, get_version(db, version_id))
    if (
        not preview
        or preview["job_id"] != str(job_id)
        or preview["attempt"] != attempt
        or filename
        not in {a["filename"] for a in preview["manifest"]["assets"].values()}
    ):
        raise HTTPException(404, "Draft preview is not available for this attempt.")
    return FileResponse(
        preview["stage"] / filename,
        media_type="model/gltf-binary" if filename == "car.glb" else "image/png",
        headers={"Cache-Control": "private, no-store"},
    )


@admin.post("/sources", status_code=201)
def source_import(payload: SourceImport, db: Session = Depends(get_db)):
    try:
        source, candidates, duplicate = import_source(db, payload)
    except Exception as e:
        db.rollback()
        raise HTTPException(422, f"Source import failed: {e}")
    audit(
        db,
        "import_source",
        source.id,
        {"duplicate": duplicate, "candidates": len(candidates)},
    )
    db.commit()
    return {
        "source": source_public(source),
        "candidates": [candidate_public(c) for c in candidates],
        "duplicate": duplicate,
    }


@admin.patch("/candidates/{candidate_id}")
def review_candidate(
    candidate_id: UUID, payload: CandidateReview, db: Session = Depends(get_db)
):
    candidate = db.get(UpgradeCandidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found.")
    # Draft snapshots contain copies of the evidence; published evidence cannot change.
    for version in db.query(CarVersion).filter_by(status="published"):
        if str(candidate_id) in version.candidate_ids:
            raise HTTPException(
                409,
                "This evidence is part of a published release; import a correction as new evidence.",
            )
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(candidate, key, value)
    if candidate.component and candidate.component not in catalog()["components"]:
        raise HTTPException(422, "Unknown component.")
    if candidate.legacy_upgrade_id:
        from app.models.models import Upgrade, Race, Team

        legacy = db.get(Upgrade, candidate.legacy_upgrade_id)
        race = db.get(Race, legacy.race_id) if legacy else None
        team = db.get(Team, legacy.team_id) if legacy else None
        if (
            not legacy
            or not race
            or race.season != candidate.season
            or not team
            or not candidate.team_key
            or candidate.team_key not in team.name.lower()
        ):
            raise HTTPException(
                422,
                "Legacy upgrade links must match this candidate's team and season; old demonstration records cannot enter a 2026 release.",
            )
    if candidate.status == "approved":
        if not all(
            (
                candidate.team_key,
                candidate.component,
                candidate.event_name,
                candidate.observed_at,
            )
        ):
            raise HTTPException(
                422, "Resolve the team, component, event, and observation date first."
            )
        if candidate.evidence_status in {"unverified", "conflicting"}:
            raise HTTPException(
                422, "Unverified or conflicting claims cannot be approved."
            )
        if candidate.representation == "modeled" and (
            candidate.evidence_status != "confirmed" or len(candidate.review_notes) < 20
        ):
            raise HTTPException(
                422,
                "Modeled changes require confirmed visual evidence and notes explaining the reconstruction.",
            )
        if len(candidate.supporting_passage) < 5:
            raise HTTPException(422, "A supporting passage is required.")
        source = db.get(SourceDocument, candidate.source_id)
        passage = re.sub(r"\s+", " ", candidate.supporting_passage).strip()
        if passage not in re.sub(r"\s+", " ", source.text):
            raise HTTPException(
                422,
                "The supporting passage must appear in the imported source text. Import a new source for additional evidence.",
            )
        if candidate.page and source.pages:
            cited_page = next(
                (p["text"] for p in source.pages if p["page"] == candidate.page), ""
            )
            if passage not in re.sub(r"\s+", " ", cited_page):
                raise HTTPException(
                    422, "The passage does not appear on the cited PDF page."
                )
        candidate.reviewed_at = now()
    audit(db, "review_candidate", candidate.id, values)
    db.commit()
    return candidate_public(candidate, db.get(SourceDocument, candidate.source_id))


@admin.post("/versions", status_code=201)
def new_version(payload: VersionInput, db: Session = Depends(get_db)):
    version = create_version(db, payload)
    db.commit()
    return version_public(version)


@admin.post("/versions/{version_id}/build", status_code=202)
def build(version_id: UUID, db: Session = Depends(get_db)):
    version = db.query(CarVersion).filter_by(id=version_id).with_for_update().first()
    if not version:
        raise HTTPException(404, "Car version not found.")
    job = queue_build(db, version)
    db.commit()
    dispatch(job)
    return job_public(job)


@admin.put("/versions/{version_id}/visual-review")
def visual_review(
    version_id: UUID, payload: VisualReview, db: Session = Depends(get_db)
):
    version = get_version(db, version_id)
    if version.status != "ready":
        raise HTTPException(409, "Only a built, unpublished draft can be reviewed.")
    for url in payload.reference_urls:
        try:
            canonical_url(url)
        except ValueError as e:
            raise HTTPException(422, str(e))
    version.visual_review = {**payload.model_dump(), "reviewed_at": now().isoformat()}
    audit(db, "visual_review", version.id, version.visual_review)
    db.commit()
    return version_public(version)


@admin.post("/versions/{version_id}/publish")
def publish_version(version_id: UUID, db: Session = Depends(get_db)):
    version = db.query(CarVersion).filter_by(id=version_id).with_for_update().first()
    if not version:
        raise HTTPException(404, "Car version not found.")
    try:
        publish(db, version)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return version_public(version, version.id)


@admin.post("/cars/{team}/rollback")
def rollback(team: str, payload: Rollback, db: Session = Depends(get_db)):
    version = get_version(db, payload.version_id)
    if version.team_key != team or version.status != "published":
        raise HTTPException(422, "Select a published version of this team.")
    pointer = (
        db.query(ReleasePointer)
        .filter_by(team_key=team, season=version.season)
        .with_for_update()
        .first()
    )
    if not pointer:
        raise HTTPException(404, "No current release.")
    audit(
        db,
        "rollback",
        version.id,
        {"previous_version": str(pointer.version_id), "reason": payload.reason},
    )
    pointer.version_id = version.id
    pointer.updated_at = now()
    db.commit()
    return version_public(version, version.id)


@admin.post("/collect", status_code=202)
def collect(db: Session = Depends(get_db)):
    job = BuildJob(kind="collect", status="queued")
    db.add(job)
    db.commit()
    dispatch(job)
    return job_public(job)


@public.post(
    "/models/{team}/regenerate", status_code=202, dependencies=[Depends(require_admin)]
)
def regenerate_alias(team: str, season: int = 2026, db: Session = Depends(get_db)):
    if team not in catalog()["teams"] or season != 2026:
        raise HTTPException(404, "Team/season not supported.")
    pointer = db.get(ReleasePointer, (team, season))
    if pointer:
        parent = get_version(db, pointer.version_id)
        version = create_version(
            db,
            VersionInput(
                team_key=team,
                season=season,
                label=parent.label + " · new draft",
                configuration_event=parent.configuration_event,
                as_of=parent.as_of,
                evidence_cutoff=now(),
                parent_id=parent.id,
                notes="No new modeled change established.",
            ),
        )
    else:
        from app.services.releases import bootstrap_baseline

        version = bootstrap_baseline(db, team)
        if version.status == "ready":
            # A baseline can need another modeling pass before any publication.
            # Freeze the current catalog into a new draft and retain the old artifacts.
            version = bootstrap_baseline(db, team, force_new=True)
    job = queue_build(db, version)
    db.commit()
    dispatch(job)
    return job_public(job)


@admin.post("/jobs/{job_id}/retry", status_code=202)
def retry(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(BuildJob).filter_by(id=job_id).with_for_update().first()
    if not job or job.status != "failed":
        raise HTTPException(409, "Only a failed job can be retried.")
    if job.version_id:
        version = get_version(db, job.version_id)
        if version.status == "published":
            raise HTTPException(409, "Published versions cannot be rebuilt.")
        version.status = "building"
    job.status = "queued"
    job.error = None
    job.finished_at = None
    job.started_at = None
    audit(db, "retry_job", job.id)
    db.commit()
    dispatch(job)
    return job_public(job)
