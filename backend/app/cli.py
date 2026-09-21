"""Local maintainer commands, invoked inside the API container."""

import argparse
import json
from pathlib import Path
from uuid import UUID
from app.database import SessionLocal
from app.models.releases import BuildJob, CarVersion
from app.api.releases import dispatch
from app.services.releases import queue_build, audit, reconstruct_launch


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "collect", help="Collect configured public sources into the review inbox"
    )
    sub.add_parser("jobs", help="List recent build and collection jobs")
    intake = sub.add_parser(
        "import-weekly", help="Import changed report URLs into the evidence inbox"
    )
    intake.add_argument("report", type=Path)
    build = sub.add_parser("build", help="Queue a draft build; never publish")
    build.add_argument("version_id", type=UUID)
    correction = sub.add_parser(
        "correct-launch",
        help="Build a draft correction of an existing published launch reference; never publish",
    )
    correction.add_argument("parent_id", type=UUID)
    native = sub.add_parser(
        "adopt-native",
        help="Validate a native Blender build and attach it to an unfinished draft",
    )
    native.add_argument("version_id", type=UUID)
    native.add_argument("directory", type=Path)
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "adopt-native":
            from app.services.local_builds import adopt_build

            version = adopt_build(db, args.version_id, args.directory)
            db.commit()
            print(f"Validated draft {version.id}; four-view review remains required.")
            return
        if args.command == "import-weekly":
            from app.services.sources import import_source
            from app.schemas.releases import SourceImport

            report = json.loads(args.report.read_text())
            if report.get("schema_version") != 1 or not isinstance(
                report.get("documents"), list
            ):
                parser.error("Unsupported weekly report")
            for item in report["documents"]:
                if not item.get("changed", True):
                    continue
                try:
                    source, candidates, duplicate = import_source(
                        db, SourceImport(url=item["url"])
                    )
                    db.commit()
                    print(
                        source.url,
                        "duplicate" if duplicate else f"{len(candidates)} candidates",
                    )
                except Exception as error:
                    db.rollback()
                    print(item["url"], "FAILED", str(error)[:300])
            return
        if args.command == "jobs":
            for job in (
                db.query(BuildJob).order_by(BuildJob.created_at.desc()).limit(30)
            ):
                print(
                    job.id, job.kind, job.status, job.version_id or "", job.error or ""
                )
            return
        if args.command == "collect":
            job = BuildJob(kind="collect", status="queued")
            db.add(job)
            db.flush()
            audit(db, "manual_collection", job.id)
        elif args.command == "correct-launch":
            version = reconstruct_launch(db, db.get(CarVersion, args.parent_id))
            job = queue_build(db, version)
            print(f"Draft reconstruction {version.id}; four-view review required.")
        else:
            version = db.get(CarVersion, args.version_id)
            if not version:
                parser.error("Unknown version")
            job = queue_build(db, version)
        db.commit()
        dispatch(job)
        print(f"Queued {job.kind} job {job.id}. Inspect it at /review.")


if __name__ == "__main__":
    main()
