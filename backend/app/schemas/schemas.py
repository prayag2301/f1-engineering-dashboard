from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from app.models.enums import UpgradeCategory, ComponentZone, EventStatus, AssetType


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamBase(BaseModel):
    name: str = Field(..., max_length=100)
    full_name: str = Field(..., max_length=200)
    base: Optional[str] = None
    team_principal: Optional[str] = None
    power_unit: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Race ──────────────────────────────────────────────────────────────────────

class RaceBase(BaseModel):
    name: str = Field(..., max_length=200)
    circuit: str = Field(..., max_length=200)
    country: Optional[str] = None
    round_number: int
    season: int
    date: datetime


class RaceCreate(RaceBase):
    pass


class RaceRead(RaceBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Component ─────────────────────────────────────────────────────────────────

class ComponentBase(BaseModel):
    name: str = Field(..., max_length=200)
    zone: ComponentZone
    description: Optional[str] = None


class ComponentCreate(ComponentBase):
    pass


class ComponentRead(ComponentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Upgrade ───────────────────────────────────────────────────────────────────

class UpgradeBase(BaseModel):
    team_id: UUID
    race_id: UUID
    component_id: UUID
    category: UpgradeCategory
    description: str
    technical_detail: Optional[str] = None
    expected_effect: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    aero_reasoning: Optional[str] = None
    mechanical_reasoning: Optional[str] = None
    performance_hypothesis: Optional[str] = None
    source: Optional[str] = None


class UpgradeCreate(UpgradeBase):
    category: Optional[UpgradeCategory] = None


class UpgradeRead(UpgradeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    team: Optional[TeamRead] = None
    race: Optional[RaceRead] = None
    component: Optional[ComponentRead] = None

    class Config:
        from_attributes = True


# ── Performance Delta ─────────────────────────────────────────────────────────

class PerformanceDeltaBase(BaseModel):
    team_id: UUID
    race_id: UUID
    fp1_time: Optional[float] = None
    fp2_time: Optional[float] = None
    fp3_time: Optional[float] = None
    quali_time: Optional[float] = None
    race_best_lap: Optional[float] = None
    delta_fp1_to_quali: Optional[float] = None
    delta_quali_to_race: Optional[float] = None
    delta_race_over_race: Optional[float] = None
    upgrade_efficiency_score: Optional[float] = None
    notes: Optional[str] = None


class PerformanceDeltaCreate(PerformanceDeltaBase):
    pass


class PerformanceDeltaRead(PerformanceDeltaBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Sprint 2: Upgrade Intelligence / Ingestion ───────────────────────────────

class UpgradeIntelligencePreviewRequest(BaseModel):
    description: str
    technical_detail: Optional[str] = None
    expected_effect: Optional[str] = None
    source: Optional[str] = None


class UpgradeIntelligencePreviewResponse(BaseModel):
    inferred_category: UpgradeCategory
    inferred_component_zone: ComponentZone
    confidence: float = Field(..., ge=0.0, le=1.0)
    aero_reasoning: str
    mechanical_reasoning: str
    performance_hypothesis: str
    signals: List[str]


class UpgradeIngestItem(BaseModel):
    team_id: UUID
    race_id: UUID
    component_id: UUID
    description: str
    technical_detail: Optional[str] = None
    expected_effect: Optional[str] = None
    category: Optional[UpgradeCategory] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    aero_reasoning: Optional[str] = None
    mechanical_reasoning: Optional[str] = None
    performance_hypothesis: Optional[str] = None
    source: Optional[str] = None


class UpgradeBatchIngestRequest(BaseModel):
    items: List[UpgradeIngestItem] = Field(..., min_length=1, max_length=200)
    enrich_missing_fields: bool = True
    skip_duplicates: bool = True


class UpgradeBatchIngestResult(BaseModel):
    created: int
    skipped_duplicates: int
    upgrades: List[UpgradeRead]


# ── Event ─────────────────────────────────────────────────────────────────────

class EventBase(BaseModel):
    race_id: UUID
    status: EventStatus = EventStatus.PENDING


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    status: EventStatus


class EventRead(EventBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    race: Optional[RaceRead] = None

    class Config:
        from_attributes = True


# ── Evidence ──────────────────────────────────────────────────────────────────

class EvidenceBase(BaseModel):
    upgrade_id: UUID
    source: str
    license: str = "unknown"
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    media_path: Optional[str] = None
    article_path: Optional[str] = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceRead(EvidenceBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Asset ─────────────────────────────────────────────────────────────────────

class AssetBase(BaseModel):
    upgrade_id: UUID
    asset_type: AssetType
    path: str
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


# ── Regulation Constraint ─────────────────────────────────────────────────────

class RegulationConstraintBase(BaseModel):
    season: int
    component: str
    parameter: str
    value: float
    unit: str
    article_ref: Optional[str] = None
    notes: Optional[str] = None


class RegulationConstraintCreate(RegulationConstraintBase):
    pass


class RegulationConstraintRead(RegulationConstraintBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Callout ───────────────────────────────────────────────────────────────────

class CalloutBase(BaseModel):
    upgrade_id: UUID
    label: str
    anchor_type: str = "symbolic"
    anchor_ref: str = ""
    description: str = ""


class CalloutCreate(CalloutBase):
    pass


class CalloutRead(CalloutBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
