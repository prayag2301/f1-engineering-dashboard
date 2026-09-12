"""Reviewable evidence, immutable car snapshots, and durable build state."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Uuid,
    UniqueConstraint,
    CheckConstraint,
)
from app.database import Base
from app.models.models import Upgrade


def utcnow():
    return datetime.now(timezone.utc)


class SourceDocument(Base):
    __tablename__ = "source_documents"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    title = Column(Text, nullable=False)
    publisher = Column(String(200), nullable=False)
    source_type = Column(String(40), nullable=False, default="article")
    published_at = Column(DateTime(timezone=True))
    retrieved_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    event_name = Column(String(200))
    text = Column(Text, nullable=False)
    pages = Column(JSON, nullable=False, default=list)
    image_urls = Column(JSON, nullable=False, default=list)
    rights = Column(
        Text,
        nullable=False,
        default="Reference only; external media is not redistributed.",
    )
    __table_args__ = (UniqueConstraint("canonical_url", "content_hash"),)


class UpgradeCandidate(Base):
    __tablename__ = "upgrade_candidates"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id = Column(Uuid, ForeignKey("source_documents.id"), nullable=False)
    team_key = Column(String(40))
    season = Column(Integer, nullable=False, default=2026)
    component = Column(String(60))
    event_name = Column(String(200))
    observed_at = Column(DateTime(timezone=True))
    summary = Column(Text, nullable=False)
    supporting_passage = Column(Text, nullable=False)
    page = Column(Integer)
    evidence_status = Column(String(30), nullable=False, default="unverified")
    representation = Column(String(30), nullable=False, default="annotation_only")
    status = Column(String(30), nullable=False, default="draft")
    review_notes = Column(Text, nullable=False, default="")
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    legacy_upgrade_id = Column(Uuid, ForeignKey(Upgrade.id))
    __table_args__ = (
        CheckConstraint("status IN ('draft','approved','rejected')"),
        CheckConstraint("representation IN ('annotation_only','modeled')"),
        CheckConstraint(
            "evidence_status IN ('unverified','reported','confirmed','conflicting')"
        ),
    )


class ComponentRevision(Base):
    __tablename__ = "component_revisions"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    team_key = Column(String(40), nullable=False)
    season = Column(Integer, nullable=False)
    component = Column(String(60), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    source_ids = Column(JSON, nullable=False, default=list)
    uncertainty = Column(Text, nullable=False)
    revision_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("team_key", "season", "component", "revision_hash"),
    )


class CarVersion(Base):
    __tablename__ = "car_versions"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    team_key = Column(String(40), nullable=False, index=True)
    season = Column(Integer, nullable=False, default=2026)
    label = Column(String(200), nullable=False)
    configuration_event = Column(String(200), nullable=False)
    configuration_kind = Column(
        String(30), nullable=False, default="evolution", server_default="evolution"
    )
    reverts_to_id = Column(Uuid, ForeignKey("car_versions.id"))
    as_of = Column(DateTime(timezone=True), nullable=False)
    evidence_cutoff = Column(DateTime(timezone=True), nullable=False)
    parent_id = Column(Uuid, ForeignKey("car_versions.id"))
    status = Column(String(30), nullable=False, default="draft")
    component_revisions = Column(JSON, nullable=False, default=dict)
    candidate_ids = Column(JSON, nullable=False, default=list)
    manifest = Column(JSON, nullable=False, default=dict)
    visual_review = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    published_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('draft','building','ready','published','failed')"),
    )


class ReleasePointer(Base):
    __tablename__ = "release_pointers"
    team_key = Column(String(40), primary_key=True)
    season = Column(Integer, primary_key=True)
    version_id = Column(Uuid, ForeignKey("car_versions.id"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class BuildJob(Base):
    __tablename__ = "build_jobs"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id = Column(Uuid, ForeignKey("car_versions.id"))
    kind = Column(String(30), nullable=False, default="build")
    status = Column(String(30), nullable=False, default="queued")
    schedule_key = Column(String(100), unique=True)
    parameters = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=False, default=dict)
    error = Column(Text)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at = Column(DateTime(timezone=True))
    heartbeat_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('queued','running','succeeded','failed')"),
    )


class ReviewAudit(Base):
    __tablename__ = "review_audit"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    action = Column(String(40), nullable=False)
    target_id = Column(String(60), nullable=False)
    detail = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
