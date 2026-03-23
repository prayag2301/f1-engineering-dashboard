import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from backend.database import Base
from backend.models.enums import UpgradeCategory, ComponentZone, EventStatus, AssetType


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    base = Column(String(200))
    team_principal = Column(String(100))
    power_unit = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrades = relationship("Upgrade", back_populates="team")
    performance_deltas = relationship("PerformanceDelta", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"


class Race(Base):
    __tablename__ = "races"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    circuit = Column(String(200), nullable=False)
    country = Column(String(100))
    round_number = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrades = relationship("Upgrade", back_populates="race")
    performance_deltas = relationship("PerformanceDelta", back_populates="race")
    events = relationship("Event", back_populates="race")

    def __repr__(self):
        return f"<Race {self.name} ({self.season})>"


class Component(Base):
    __tablename__ = "components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    zone = Column(SAEnum(ComponentZone), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrades = relationship("Upgrade", back_populates="component")

    def __repr__(self):
        return f"<Component {self.name} ({self.zone})>"


class Upgrade(Base):
    __tablename__ = "upgrades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    race_id = Column(UUID(as_uuid=True), ForeignKey("races.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("components.id"), nullable=False)

    category = Column(SAEnum(UpgradeCategory), nullable=False, index=True)
    description = Column(Text, nullable=False)
    technical_detail = Column(Text)
    expected_effect = Column(String(500))
    confidence = Column(Float, default=0.5)

    aero_reasoning = Column(Text)
    mechanical_reasoning = Column(Text)
    performance_hypothesis = Column(Text)

    source = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team", back_populates="upgrades")
    race = relationship("Race", back_populates="upgrades")
    component = relationship("Component", back_populates="upgrades")
    evidence = relationship("Evidence", back_populates="upgrade", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="upgrade", cascade="all, delete-orphan")
    callouts = relationship("Callout", back_populates="upgrade", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Upgrade {self.team_id} @ {self.race_id}: {self.category}>"


class PerformanceDelta(Base):
    __tablename__ = "performance_deltas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    race_id = Column(UUID(as_uuid=True), ForeignKey("races.id"), nullable=False)

    fp1_time = Column(Float)
    fp2_time = Column(Float)
    fp3_time = Column(Float)
    quali_time = Column(Float)
    race_best_lap = Column(Float)

    delta_fp1_to_quali = Column(Float)
    delta_quali_to_race = Column(Float)
    delta_race_over_race = Column(Float)

    upgrade_efficiency_score = Column(Float)
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="performance_deltas")
    race = relationship("Race", back_populates="performance_deltas")

    def __repr__(self):
        return f"<PerformanceDelta {self.team_id} @ {self.race_id}>"


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    race_id = Column(UUID(as_uuid=True), ForeignKey("races.id"), nullable=False)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    race = relationship("Race", back_populates="events")

    def __repr__(self):
        return f"<Event {self.race_id}: {self.status}>"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upgrade_id = Column(UUID(as_uuid=True), ForeignKey("upgrades.id"), nullable=False)
    source = Column(String(500), nullable=False)
    license = Column(String(100), default="unknown")
    credibility_score = Column(Float, default=0.5)
    media_path = Column(String(500))
    article_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrade = relationship("Upgrade", back_populates="evidence")

    def __repr__(self):
        return f"<Evidence {self.source} for {self.upgrade_id}>"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upgrade_id = Column(UUID(as_uuid=True), ForeignKey("upgrades.id"), nullable=False)
    asset_type = Column(SAEnum(AssetType), nullable=False)
    path = Column(String(500), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrade = relationship("Upgrade", back_populates="assets")

    def __repr__(self):
        return f"<Asset {self.asset_type}: {self.path}>"


class Callout(Base):
    __tablename__ = "callouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upgrade_id = Column(UUID(as_uuid=True), ForeignKey("upgrades.id"), nullable=False)
    label = Column(String(200), nullable=False)
    anchor_type = Column(String(50), default="symbolic")
    anchor_ref = Column(String(200), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    upgrade = relationship("Upgrade", back_populates="callouts")

    def __repr__(self):
        return f"<Callout {self.label} on {self.upgrade_id}>"
