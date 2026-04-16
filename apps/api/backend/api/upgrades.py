from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID

from backend.database import get_db
from backend.models.models import Race, Upgrade
from backend.models.enums import UpgradeCategory
from backend.schemas.schemas import (
    UpgradeBatchIngestRequest,
    UpgradeBatchIngestResult,
    UpgradeCreate,
    UpgradeIntelligencePreviewRequest,
    UpgradeIntelligencePreviewResponse,
    UpgradeRead,
)
from backend.upgrade_parser import analyze_upgrade
from backend.ingestion import ingest_upgrade_items
from backend.services.upgrade_tracker import collect_upgrade_ingest_items

router = APIRouter()


def _upgrade_with_joins(db: Session, upgrade_id: UUID):
    return (
        db.query(Upgrade)
        .options(
            joinedload(Upgrade.team),
            joinedload(Upgrade.race),
            joinedload(Upgrade.component),
        )
        .filter(Upgrade.id == upgrade_id)
        .first()
    )


def _apply_intelligence(payload: UpgradeCreate) -> dict:
    data = payload.model_dump()
    intel = analyze_upgrade(
        description=payload.description,
        technical_detail=payload.technical_detail,
        expected_effect=payload.expected_effect,
        source=payload.source,
    )

    data["category"] = data.get("category") or intel.category
    if not data.get("aero_reasoning"):
        data["aero_reasoning"] = intel.aero_reasoning
    if not data.get("mechanical_reasoning"):
        data["mechanical_reasoning"] = intel.mechanical_reasoning
    if not data.get("performance_hypothesis"):
        data["performance_hypothesis"] = intel.performance_hypothesis
    if data.get("confidence") in (None, 0.5):
        data["confidence"] = intel.confidence
    return data


@router.get("/", response_model=List[UpgradeRead])
def list_upgrades(
    category: Optional[UpgradeCategory] = None,
    team_id: Optional[UUID] = None,
    race_id: Optional[UUID] = None,
    race_weekend: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Upgrade).options(
        joinedload(Upgrade.team),
        joinedload(Upgrade.race),
        joinedload(Upgrade.component),
    )
    if category:
        q = q.filter(Upgrade.category == category)
    if team_id:
        q = q.filter(Upgrade.team_id == team_id)
    if race_id:
        q = q.filter(Upgrade.race_id == race_id)
    if race_weekend:
        q = q.join(Upgrade.race).filter(Race.name.ilike(f"%{race_weekend}%"))
    return q.order_by(Upgrade.created_at.desc()).offset(offset).limit(limit).all()


@router.post("/intelligence/preview", response_model=UpgradeIntelligencePreviewResponse)
def preview_upgrade_intelligence(payload: UpgradeIntelligencePreviewRequest):
    intel = analyze_upgrade(
        description=payload.description,
        technical_detail=payload.technical_detail,
        expected_effect=payload.expected_effect,
        source=payload.source,
    )
    return UpgradeIntelligencePreviewResponse(
        inferred_category=intel.category,
        inferred_component_zone=intel.component_zone,
        confidence=intel.confidence,
        aero_reasoning=intel.aero_reasoning,
        mechanical_reasoning=intel.mechanical_reasoning,
        performance_hypothesis=intel.performance_hypothesis,
        signals=intel.signals,
    )


@router.post("/ingest", response_model=UpgradeBatchIngestResult, status_code=201)
def ingest_upgrades(payload: UpgradeBatchIngestRequest, db: Session = Depends(get_db)):
    outcome = ingest_upgrade_items(
        db=db,
        items=payload.items,
        enrich_missing_fields=payload.enrich_missing_fields,
        skip_duplicates=payload.skip_duplicates,
    )
    db.commit()

    upgrades = [_upgrade_with_joins(db, upgrade.id) for upgrade in outcome.created]
    return UpgradeBatchIngestResult(
        created=len(outcome.created),
        skipped_duplicates=outcome.skipped_duplicates,
        upgrades=[u for u in upgrades if u is not None],
    )


@router.post("/fetch", status_code=201)
def fetch_upgrades(
    season: Optional[int] = Query(default=None),
    max_entries: int = Query(default=50, ge=1, le=200),
    enrich_missing_fields: bool = Query(default=True),
    skip_duplicates: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """
    Fetch external RSS upgrade reports, map them to known teams/components/races,
    then ingest them through the existing enrichment + dedupe pipeline.
    """
    items, stats = collect_upgrade_ingest_items(
        db=db,
        season=season,
        max_entries=max_entries,
    )

    if not items:
        return {
            "scanned_entries": stats.scanned_entries,
            "candidates": stats.candidates,
            "created": 0,
            "skipped_duplicates": 0,
            "skipped_non_upgrade": stats.skipped_non_upgrade,
            "skipped_no_team": stats.skipped_no_team,
            "skipped_no_component": stats.skipped_no_component,
            "skipped_no_race": stats.skipped_no_race,
            "feed_errors": stats.feed_errors,
            "upgrade_ids": [],
        }

    outcome = ingest_upgrade_items(
        db=db,
        items=items,
        enrich_missing_fields=enrich_missing_fields,
        skip_duplicates=skip_duplicates,
    )
    db.commit()

    return {
        "scanned_entries": stats.scanned_entries,
        "candidates": stats.candidates,
        "created": len(outcome.created),
        "skipped_duplicates": outcome.skipped_duplicates,
        "skipped_non_upgrade": stats.skipped_non_upgrade,
        "skipped_no_team": stats.skipped_no_team,
        "skipped_no_component": stats.skipped_no_component,
        "skipped_no_race": stats.skipped_no_race,
        "feed_errors": stats.feed_errors,
        "upgrade_ids": [str(upgrade.id) for upgrade in outcome.created],
    }


@router.get("/{upgrade_id}", response_model=UpgradeRead)
def get_upgrade(upgrade_id: UUID, db: Session = Depends(get_db)):
    upgrade = _upgrade_with_joins(db, upgrade_id)
    if not upgrade:
        raise HTTPException(status_code=404, detail="Upgrade not found")
    return upgrade


@router.post("/", response_model=UpgradeRead, status_code=201)
def create_upgrade(payload: UpgradeCreate, db: Session = Depends(get_db)):
    upgrade = Upgrade(**_apply_intelligence(payload))
    db.add(upgrade)
    db.commit()
    db.refresh(upgrade)
    return _upgrade_with_joins(db, upgrade.id)


@router.delete("/{upgrade_id}", status_code=204)
def delete_upgrade(upgrade_id: UUID, db: Session = Depends(get_db)):
    upgrade = db.query(Upgrade).filter(Upgrade.id == upgrade_id).first()
    if not upgrade:
        raise HTTPException(status_code=404, detail="Upgrade not found")
    db.delete(upgrade)
    db.commit()
