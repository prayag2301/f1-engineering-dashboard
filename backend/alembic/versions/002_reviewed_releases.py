"""Add evidence/release tables and normalize existing enum labels in place.

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa
import json
from pathlib import Path

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    frozen = json.loads(Path(__file__).with_name("002_release_tables.json").read_text())
    # Old create_all databases stored enum names; migration 001 stored values.
    # Rename labels, preserving all existing IDs and rows in either layout.
    if bind.dialect.name == "postgresql":
        for name, labels_by_name in frozen["enums"].items():
            labels = set(
                bind.execute(
                    sa.text(
                        "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid=t.oid WHERE t.typname=:name"
                    ),
                    {"name": name},
                ).scalars()
            )
            for previous, value in labels_by_name.items():
                if previous in labels and previous != value and value not in labels:
                    op.execute(
                        f"ALTER TYPE {name} RENAME VALUE '{previous}' TO '{value}'"
                    )
    # Frozen DDL: future ORM changes must not silently alter historical migrations.
    tables = frozen["tables"]
    existing = set(sa.inspect(bind).get_table_names())
    for table in tables:
        if table["name"] not in existing:
            op.execute(table["table"])
            for index in table["indexes"]:
                op.execute(index)


def downgrade():
    for table in (
        "review_audit",
        "build_jobs",
        "release_pointers",
        "car_versions",
        "component_revisions",
        "upgrade_candidates",
        "source_documents",
    ):
        op.drop_table(table)
