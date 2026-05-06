from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.models import Upgrade
from backend.schemas.schemas import UpgradeIngestItem
from backend.upgrade_parser import analyze_upgrade


@dataclass
class BatchIngestOutcome:
    created: list[Upgrade]
    skipped_duplicates: int


def _is_duplicate(db: Session, item: UpgradeIngestItem) -> bool:
    return (
        db.query(Upgrade)
        .filter(Upgrade.team_id == item.team_id)
        .filter(Upgrade.race_id == item.race_id)
        .filter(Upgrade.component_id == item.component_id)
        .filter(Upgrade.description == item.description)
        .first()
        is not None
    )


def _build_upgrade_model(item: UpgradeIngestItem, enrich_missing_fields: bool) -> Upgrade:
    payload = item.model_dump()

    if enrich_missing_fields:
        intel = analyze_upgrade(
            description=item.description,
            technical_detail=item.technical_detail,
            expected_effect=item.expected_effect,
            source=item.source,
        )
        payload["category"] = payload.get("category") or intel.category
        payload["confidence"] = payload.get("confidence")
        if payload["confidence"] is None:
            payload["confidence"] = intel.confidence
        payload["aero_reasoning"] = payload.get("aero_reasoning") or intel.aero_reasoning
        payload["mechanical_reasoning"] = payload.get("mechanical_reasoning") or intel.mechanical_reasoning
        payload["performance_hypothesis"] = (
            payload.get("performance_hypothesis") or intel.performance_hypothesis
        )

    if payload.get("category") is None:
        # Database requires category even if enrichment was disabled.
        payload["category"] = analyze_upgrade(
            description=item.description,
            technical_detail=item.technical_detail,
            expected_effect=item.expected_effect,
            source=item.source,
        ).category

    if payload.get("confidence") is None:
        payload["confidence"] = 0.5

    return Upgrade(**payload)


def ingest_upgrade_items(
    db: Session,
    items: list[UpgradeIngestItem],
    enrich_missing_fields: bool = True,
    skip_duplicates: bool = True,
) -> BatchIngestOutcome:
    created: list[Upgrade] = []
    skipped_duplicates = 0

    for item in items:
        if skip_duplicates and _is_duplicate(db, item):
            skipped_duplicates += 1
            continue

        upgrade = _build_upgrade_model(item, enrich_missing_fields=enrich_missing_fields)
        db.add(upgrade)
        db.flush()
        created.append(upgrade)

    return BatchIngestOutcome(created=created, skipped_duplicates=skipped_duplicates)
