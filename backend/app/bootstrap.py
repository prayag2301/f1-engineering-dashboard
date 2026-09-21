"""Idempotent migrations and unpublished catalog reference baselines."""

from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config import get_settings
from app.database import engine, SessionLocal
from app.models.models import Team
from app.services.catalog import catalog
from app.services.releases import bootstrap_baseline, queue_build


def migrate():
    base = Path(__file__).resolve().parents[1]
    config = Config(str(base / "alembic.ini"))
    config.set_main_option("script_location", str(base / "alembic"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "teams" in tables and "alembic_version" not in tables:
        # Stamp only the old migration after checking its actual table/column layout.
        from app.models.models import Base

        initial = {
            name: table
            for name, table in Base.metadata.tables.items()
            if name
            in {
                "teams",
                "races",
                "components",
                "upgrades",
                "performance_deltas",
                "events",
                "evidence",
                "assets",
                "callouts",
                "regulation_constraints",
            }
        }
        for name, table in initial.items():
            if name not in tables:
                table.create(engine, checkfirst=True)
            else:
                existing = {column["name"] for column in inspector.get_columns(name)}
                if not set(table.columns.keys()).issubset(existing):
                    raise RuntimeError(
                        f"Legacy table {name} differs from the initial schema; back up and migrate it explicitly."
                    )
        command.stamp(config, "001")
    command.upgrade(config, "head")


def main():
    migrate()
    with SessionLocal() as db:
        for key, info in catalog()["teams"].items():
            name = info.get("short_name", info["name"])
            if not db.query(Team).filter_by(name=name).first():
                db.add(Team(name=name, full_name=info["name"]))
            version = bootstrap_baseline(db, key)
            if version.status == "draft":
                queue_build(db, version)
        db.commit()
    print(
        "Database ready. Catalog reference drafts are queued; sign in at /review to inspect and publish."
    )


if __name__ == "__main__":
    main()
