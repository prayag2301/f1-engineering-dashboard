"""Local maintainer commands, invoked inside the API container."""

import argparse
from uuid import UUID
from app.database import SessionLocal
from app.models.releases import BuildJob, CarVersion
from app.api.releases import dispatch
from app.services.releases import queue_build, audit


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "collect", help="Collect configured public sources into the review inbox"
    )
    sub.add_parser("jobs", help="List recent build and collection jobs")
    build = sub.add_parser("build", help="Queue a draft build; never publish")
    build.add_argument("version_id", type=UUID)
    args = parser.parse_args()
    with SessionLocal() as db:
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
