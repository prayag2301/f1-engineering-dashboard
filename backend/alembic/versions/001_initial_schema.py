"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-01

Creates all tables: teams, races, components, upgrades, performance_deltas,
events, evidence, assets, callouts, regulation_constraints.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enum types ---
    postgresql.ENUM(
        "Aero", "Mechanical", "Cooling", "Floor", "Suspension", "Power Unit", "Other",
        name="upgradecategory",
    ).create(op.get_bind(), checkfirst=True)

    postgresql.ENUM(
        "pending", "ingesting", "annotating", "reconstructing", "published",
        name="eventstatus",
    ).create(op.get_bind(), checkfirst=True)

    postgresql.ENUM(
        "glb", "ply", "splat", "image", "video", "heatmap",
        name="assettype",
    ).create(op.get_bind(), checkfirst=True)

    postgresql.ENUM(
        "Front Wing", "Rear Wing", "Floor", "Floor Edge", "Sidepod", "Diffuser",
        "Bargeboard", "Engine Cover", "Brake Duct", "Suspension Arm", "Halo", "Nose", "Other",
        name="componentzone",
    ).create(op.get_bind(), checkfirst=True)

    # --- teams ---
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("base", sa.String(200)),
        sa.Column("team_principal", sa.String(100)),
        sa.Column("power_unit", sa.String(100)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)

    # --- races ---
    op.create_table(
        "races",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("circuit", sa.String(200), nullable=False),
        sa.Column("country", sa.String(100)),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_races_name", "races", ["name"])
    op.create_index("ix_races_season", "races", ["season"])

    # --- components ---
    op.create_table(
        "components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "zone",
            sa.Enum(
                "Front Wing", "Rear Wing", "Floor", "Floor Edge", "Sidepod", "Diffuser",
                "Bargeboard", "Engine Cover", "Brake Duct", "Suspension Arm", "Halo", "Nose", "Other",
                name="componentzone",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_components_name", "components", ["name"])

    # --- upgrades ---
    op.create_table(
        "upgrades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("race_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("components.id"), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "Aero", "Mechanical", "Cooling", "Floor", "Suspension", "Power Unit", "Other",
                name="upgradecategory",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("technical_detail", sa.Text()),
        sa.Column("expected_effect", sa.String(500)),
        sa.Column("confidence", sa.Float()),
        sa.Column("aero_reasoning", sa.Text()),
        sa.Column("mechanical_reasoning", sa.Text()),
        sa.Column("performance_hypothesis", sa.Text()),
        sa.Column("source", sa.String(500)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_upgrades_category", "upgrades", ["category"])

    # --- performance_deltas ---
    op.create_table(
        "performance_deltas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("race_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("fp1_time", sa.Float()),
        sa.Column("fp2_time", sa.Float()),
        sa.Column("fp3_time", sa.Float()),
        sa.Column("quali_time", sa.Float()),
        sa.Column("race_best_lap", sa.Float()),
        sa.Column("delta_fp1_to_quali", sa.Float()),
        sa.Column("delta_quali_to_race", sa.Float()),
        sa.Column("delta_race_over_race", sa.Float()),
        sa.Column("upgrade_efficiency_score", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )

    # --- events ---
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("race_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("races.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "ingesting", "annotating", "reconstructing", "published",
                name="eventstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_events_status", "events", ["status"])

    # --- evidence ---
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upgrade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("upgrades.id"), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("license", sa.String(100)),
        sa.Column("credibility_score", sa.Float()),
        sa.Column("media_path", sa.String(500)),
        sa.Column("article_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime()),
    )

    # --- assets ---
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upgrade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("upgrades.id"), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum("glb", "ply", "splat", "image", "video", "heatmap", name="assettype"),
            nullable=False,
        ),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text())),
        sa.Column("created_at", sa.DateTime()),
    )

    # --- callouts ---
    op.create_table(
        "callouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upgrade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("upgrades.id"), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("anchor_type", sa.String(50)),
        sa.Column("anchor_ref", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )

    # --- regulation_constraints ---
    op.create_table(
        "regulation_constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("component", sa.String(100), nullable=False),
        sa.Column("parameter", sa.String(200), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("article_ref", sa.String(100)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_regulation_constraints_season", "regulation_constraints", ["season"])
    op.create_index("ix_regulation_constraints_component", "regulation_constraints", ["component"])


def downgrade() -> None:
    op.drop_index("ix_regulation_constraints_component", table_name="regulation_constraints")
    op.drop_index("ix_regulation_constraints_season", table_name="regulation_constraints")
    op.drop_table("regulation_constraints")
    op.drop_table("callouts")
    op.drop_table("assets")
    op.drop_table("evidence")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_table("events")
    op.drop_table("performance_deltas")
    op.drop_index("ix_upgrades_category", table_name="upgrades")
    op.drop_table("upgrades")
    op.drop_index("ix_components_name", table_name="components")
    op.drop_table("components")
    op.drop_index("ix_races_season", table_name="races")
    op.drop_index("ix_races_name", table_name="races")
    op.drop_table("races")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

    sa.Enum(name="componentzone").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="assettype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="upgradecategory").drop(op.get_bind(), checkfirst=True)
