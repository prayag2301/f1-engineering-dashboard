"""Durable jobs, CPU Blender execution, and a timezone-aware weekly intake."""

from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from uuid import UUID
from zoneinfo import ZoneInfo

from celery import Celery
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import SessionLocal
from app.models.releases import BuildJob, CarVersion
from app.services.releases import aware, now

settings = get_settings()
celery_app = Celery("f1", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    timezone="Europe/Berlin",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 10800},
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_routes={"app.tasks.tick": {"queue": "scheduler"}},
    beat_schedule={"recover-and-collect": {"task": "app.tasks.tick", "schedule": 60.0}},
)


def scheduled_week(moment):
    local = aware(moment).astimezone(ZoneInfo("Europe/Berlin"))
    monday = (local - timedelta(days=local.weekday())).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    if local < monday:
        monday -= timedelta(days=7)
    return "weekly:" + monday.date().isoformat()


@celery_app.task(name="app.tasks.tick")
def tick():
    with SessionLocal() as db:
        # Leases are renewed by the render subprocess monitor, including long 4K renders.
        for job in db.query(BuildJob).filter_by(status="running"):
            if job.heartbeat_at and aware(job.heartbeat_at) < now() - timedelta(
                minutes=5
            ):
                job.status = "failed" if job.attempts >= 3 else "queued"
                job.error = (
                    "Worker stopped responding; retry limit reached."
                    if job.status == "failed"
                    else "Recovered after worker interruption."
                )
                if job.version_id and job.status == "failed":
                    version = db.get(CarVersion, job.version_id)
                    if version and version.status != "published":
                        version.status = "failed"
        # Bounded retries survive process restarts; published pointers are never touched.
        for job in db.query(BuildJob).filter_by(kind="collect", status="failed"):
            if (
                job.attempts < 3
                and job.finished_at
                and aware(job.finished_at)
                < now() - timedelta(minutes=15 * max(1, job.attempts))
            ):
                job.status = "queued"
        key = scheduled_week(now())
        if not db.query(BuildJob).filter_by(schedule_key=key).first():
            db.add(BuildJob(kind="collect", status="queued", schedule_key=key))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        queued = [
            str(j.id) for j in db.query(BuildJob).filter_by(status="queued").all()
        ]
    for job_id in queued:
        execute_job.apply_async(args=[job_id], retry=False)


class LostLease(RuntimeError):
    pass


class CollectionFailure(RuntimeError):
    def __init__(self, result):
        super().__init__(
            "All configured sources failed. Existing car releases are unchanged; retry collection or import source text manually."
        )
        self.result = result


def heartbeat(job_id, attempt):
    with SessionLocal() as db:
        job = db.get(BuildJob, job_id)
        if not job or job.status != "running" or job.attempts != attempt:
            raise LostLease("This execution was superseded by a recovered job.")
        job.heartbeat_at = now()
        db.commit()


def collect_sources(job_id, attempt):
    from app.services.sources import fetch_bytes, import_source, discover_links
    from app.schemas.releases import SourceImport

    config = json.loads((settings.REFERENCE_ROOT / "sources.json").read_text())
    result = {
        "documents": 0,
        "candidates": 0,
        "duplicates": 0,
        "sources": [],
        "errors": [],
    }
    for entry in config["sources"]:
        heartbeat(job_id, attempt)
        try:
            data, mime, url = fetch_bytes(entry["url"])
            items = discover_links(entry, data, url)
            feed_dates = {item["url"]: item["published_at"] for item in items}
            links = [item["url"] for item in items]
            if not links:
                result["errors"].append(
                    {
                        "url": url,
                        "error": "No readable matching article links; source coverage is incomplete.",
                    }
                )
            stats = {
                "url": url,
                "checked_at": now().isoformat(),
                "links": len(links),
                "imported": 0,
            }
            for link in links[: entry.get("limit", 5)]:
                heartbeat(job_id, attempt)
                try:
                    with SessionLocal() as db:
                        source, candidates, duplicate = import_source(
                            db,
                            SourceImport(
                                url=link, fallback_published_at=feed_dates.get(link)
                            ),
                        )
                        db.commit()
                        result["documents"] += int(not duplicate)
                        result["duplicates"] += int(duplicate)
                        result["candidates"] += len(candidates)
                        stats["imported"] += 1
                except Exception as e:
                    result["errors"].append({"url": link, "error": str(e)[:500]})
            result["sources"].append(stats)
        except Exception as e:
            result["errors"].append({"url": entry["url"], "error": str(e)[:500]})
    result["coverage"] = "partial" if result["errors"] else "complete"
    result["message"] = (
        "No new modeled change established. Collected claims await review."
    )
    if not result["sources"] or (
        result["errors"] and not any(s["imported"] for s in result["sources"])
    ):
        raise CollectionFailure(result)
    return result


def build_version(job_id, version_id, attempt):
    from app.services.validation import (
        sha256,
        validate_release,
        validate_component_history,
    )
    from app.services.catalog import catalog

    root = settings.RELEASE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    stage = root / ".staging" / (str(job_id) + "-" + str(attempt))
    stage.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        version = db.get(CarVersion, version_id)
        if version.status in {"ready", "published"}:
            return {
                "version_id": str(version_id),
                "recovered_complete_build": True,
                **validate_release(root / str(version_id), version.manifest),
            }
        manifest = json.loads(json.dumps(version.manifest))
        spec = {
            "team_key": version.team_key,
            "season": version.season,
            "version_id": str(version.id),
            "parameters": {
                name: c["parameters"] for name, c in manifest["components"].items()
            },
        }
        parent = db.get(CarVersion, version.parent_id) if version.parent_id else None
        can_reuse = bool(
            parent and parent.component_revisions == version.component_revisions
        )
        parent_id = parent.id if parent else None
        parent_manifest = parent.manifest if parent else None
    (stage / "spec.json").write_text(json.dumps(spec, indent=2))
    if can_reuse:
        # An annotation-only release reuses identical geometry, camera, and materials.
        manifest["generator_version"] = parent_manifest["generator_version"]
        for asset in parent_manifest["assets"].values():
            source = root / str(parent_id) / asset["filename"]
            if sha256(source) != asset["sha256"]:
                raise ValueError("Parent release artifact changed.")
            if asset["filename"] != "spec.json":
                shutil.copy2(source, stage / asset["filename"])
    else:
        if manifest.get("generator_version") != catalog()["generator_version"]:
            raise ValueError(
                "This draft targets a different modeling generator. Create a new draft with the current references instead of rebuilding it with different source code."
            )
        shutil.copy2(settings.MODELING_ROOT / "build_car.py", stage / "build_car.py")
        shutil.copy2(settings.MODELING_ROOT / "catalog.json", stage / "catalog.json")
        shutil.copy2(
            settings.REFERENCE_ROOT / "regulations-2026.json",
            stage / "regulations.json",
        )
        command = [
            settings.BLENDER_BINARY,
            "--background",
            "--python-exit-code",
            "1",
            "--python",
            str(stage / "build_car.py"),
            "--",
            "--input",
            str(stage / "spec.json"),
            "--output",
            str(stage),
            "--samples",
            str(settings.RENDER_SAMPLES),
        ]
        with (stage / "build.log").open("w") as log:
            process = subprocess.Popen(
                command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
            started = time.monotonic()
            try:
                while process.poll() is None:
                    heartbeat(job_id, attempt)
                    if time.monotonic() - started > settings.BUILD_TIMEOUT_SECONDS:
                        raise TimeoutError(
                            "Blender exceeded the configured build timeout."
                        )
                    time.sleep(10)
                if process.returncode:
                    lines = (
                        (stage / "build.log").read_text(errors="replace").splitlines()
                    )
                    raise RuntimeError("Blender failed: " + "\n".join(lines[-18:]))
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=20)
    filenames = {
        "glb": "car.glb",
        "source": "source.blend",
        "geometry": "geometry.json",
        "spec": "spec.json",
        "builder": "build_car.py",
        "catalog": "catalog.json",
        "regulations": "regulations.json",
    }
    filenames.update(
        {
            prefix + view: prefix + view + ".png"
            for prefix in ("preview_", "render_")
            for view in ("front", "side", "rear", "three_quarter")
        }
    )
    assets = {
        key: {
            "filename": name,
            "url": f"/api/v1/releases/{version_id}/{name}",
            "sha256": sha256(stage / name),
            "bytes": (stage / name).stat().st_size,
        }
        for key, name in filenames.items()
    }
    manifest["assets"] = assets
    geometry = json.loads((stage / "geometry.json").read_text())
    manifest["component_hashes"] = geometry["component_hashes"]
    if parent_manifest:
        validate_component_history(manifest, parent_manifest)
    manifest["validation"] = validate_release(stage, manifest)
    manifest["built_at"] = now().isoformat()
    destination = root / str(version_id)
    with SessionLocal() as db:
        job = db.query(BuildJob).filter_by(id=job_id).with_for_update().one()
        if job.status != "running" or job.attempts != attempt:
            raise LostLease("Superseded build cannot replace artifacts.")
        version = db.query(CarVersion).filter_by(id=version_id).with_for_update().one()
        if version.status == "published":
            raise ValueError("Refusing to mutate a published release.")
        # Files and the version are finalized while holding the job lease and version lock.
        if destination.exists():
            shutil.rmtree(destination)
        stage.rename(destination)
        version.manifest = manifest
        version.status = "ready"
        version.visual_review = {}
        db.commit()

    return {
        "version_id": str(version_id),
        "reused_geometry": can_reuse,
        **manifest["validation"],
    }


@celery_app.task(name="app.tasks.execute_job")
def execute_job(job_id):
    identity = UUID(job_id)
    with SessionLocal() as db:
        job = db.query(BuildJob).filter_by(id=identity).with_for_update().first()
        if not job or job.status != "queued":
            return {"skipped": True}
        job.status = "running"
        job.attempts += 1
        job.started_at = now()
        job.heartbeat_at = now()
        job.error = None
        version_id = job.version_id
        kind = job.kind
        attempt = job.attempts
        db.commit()
    try:
        result = (
            build_version(identity, version_id, attempt)
            if kind == "build"
            else collect_sources(identity, attempt)
        )
        with SessionLocal() as db:
            job = db.query(BuildJob).filter_by(id=identity).with_for_update().one()
            if job.attempts != attempt or job.status != "running":
                return {"superseded": True}
            job.status = "succeeded"
            job.result = result
            job.finished_at = now()
            db.commit()
        return result
    except Exception as e:
        with SessionLocal() as db:
            job = db.query(BuildJob).filter_by(id=identity).with_for_update().one()
            if job.attempts != attempt or job.status != "running":
                return {"superseded": True}
            job.status = "failed"
            job.error = str(e)[-6000:]
            job.finished_at = now()
            if isinstance(e, CollectionFailure):
                job.result = e.result
            if version_id:
                version = db.get(CarVersion, version_id)
                if version.status != "published":
                    version.status = "failed"
            db.commit()
        return {"error": str(e)}
