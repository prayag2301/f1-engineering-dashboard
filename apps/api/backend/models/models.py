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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database import Base
from backend.models.enums import UpgradeCategory, ComponentZone


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
