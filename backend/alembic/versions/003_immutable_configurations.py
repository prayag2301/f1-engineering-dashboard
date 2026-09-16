"""Explicit circuit configurations/reversions and PostgreSQL immutability guards.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("car_versions")}
    if "configuration_kind" not in columns:
        op.add_column(
            "car_versions",
            sa.Column(
                "configuration_kind",
                sa.String(30),
                nullable=False,
                server_default="evolution",
            ),
        )
    if "reverts_to_id" not in columns:
        op.add_column(
            "car_versions",
            sa.Column(
                "reverts_to_id",
                sa.Uuid(),
                sa.ForeignKey("car_versions.id", name="fk_car_reversion"),
            ),
        )
    if bind.dialect.name == "postgresql":
        op.execute(
            """CREATE FUNCTION f1_guard_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_TABLE_NAME = 'car_versions' THEN
            IF OLD.status != 'published' THEN
              IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;
          END IF;
          RAISE EXCEPTION 'Immutable % record; create a new revision instead', TG_TABLE_NAME;
        END $$"""
        )
        for table in ("car_versions", "component_revisions", "source_documents"):
            op.execute(
                f"CREATE TRIGGER guard_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION f1_guard_immutable()"
            )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in ("car_versions", "component_revisions", "source_documents"):
            op.execute(f"DROP TRIGGER guard_immutable ON {table}")
        op.execute("DROP FUNCTION f1_guard_immutable()")
    op.drop_column("car_versions", "reverts_to_id")
    op.drop_column("car_versions", "configuration_kind")
