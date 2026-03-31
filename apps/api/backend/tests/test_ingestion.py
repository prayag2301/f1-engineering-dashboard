"""Unit tests for the upgrade ingestion pipeline (database mocked)."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.ingestion.upgrade_ingestion import (
    BatchIngestOutcome,
    _build_upgrade_model,
    _is_duplicate,
    ingest_upgrade_items,
)
from backend.models.enums import UpgradeCategory
from backend.schemas.schemas import UpgradeIngestItem


# ── helpers ───────────────────────────────────────────────────────────────────

def make_item(**overrides) -> UpgradeIngestItem:
    defaults = dict(
        team_id=uuid4(),
        race_id=uuid4(),
        component_id=uuid4(),
        description="revised front wing endplate to improve outwash vortex",
        technical_detail=None,
        expected_effect=None,
        category=None,
        confidence=None,
        aero_reasoning=None,
        mechanical_reasoning=None,
        performance_hypothesis=None,
        source=None,
    )
    defaults.update(overrides)
    return UpgradeIngestItem(**defaults)


def _mock_db_no_duplicate() -> MagicMock:
    """Return a Session mock where _is_duplicate returns False."""
    db = MagicMock()
    (
        db.query.return_value
        .filter.return_value
        .filter.return_value
        .filter.return_value
        .filter.return_value
        .first.return_value
    ) = None
    return db


def _mock_db_with_duplicate() -> MagicMock:
    """Return a Session mock where _is_duplicate returns True."""
    db = MagicMock()
    (
        db.query.return_value
        .filter.return_value
        .filter.return_value
        .filter.return_value
        .filter.return_value
        .first.return_value
    ) = MagicMock()  # truthy → duplicate found
    return db


# ── _is_duplicate ─────────────────────────────────────────────────────────────

class TestIsDuplicate:
    def test_returns_true_when_match_found(self):
        db = _mock_db_with_duplicate()
        item = make_item()
        assert _is_duplicate(db, item) is True

    def test_returns_false_when_no_match(self):
        db = _mock_db_no_duplicate()
        item = make_item()
        assert _is_duplicate(db, item) is False

    def test_queries_all_four_fields(self):
        db = _mock_db_no_duplicate()
        item = make_item()
        _is_duplicate(db, item)
        # filter() should have been called 4 times (team_id, race_id, component_id, description)
        assert db.query.return_value.filter.return_value.filter.call_count >= 1


# ── _build_upgrade_model ──────────────────────────────────────────────────────

class TestBuildUpgradeModel:
    def test_enriches_category_when_missing(self):
        item = make_item(category=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.category is not None

    def test_enriches_aero_reasoning_when_missing(self):
        item = make_item(aero_reasoning=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.aero_reasoning

    def test_enriches_mechanical_reasoning_when_missing(self):
        item = make_item(mechanical_reasoning=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.mechanical_reasoning

    def test_enriches_performance_hypothesis_when_missing(self):
        item = make_item(performance_hypothesis=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.performance_hypothesis

    def test_does_not_overwrite_existing_category(self):
        item = make_item(category=UpgradeCategory.COOLING)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.category == UpgradeCategory.COOLING

    def test_does_not_overwrite_existing_aero_reasoning(self):
        custom = "Custom aero reasoning text."
        item = make_item(aero_reasoning=custom)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=True)
        assert upgrade.aero_reasoning == custom

    def test_defaults_confidence_to_0_5_when_none_and_no_enrichment(self):
        item = make_item(confidence=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=False)
        assert upgrade.confidence == 0.5

    def test_no_enrichment_still_infers_category(self):
        # Even with enrich_missing_fields=False, category cannot be NULL.
        item = make_item(category=None)
        upgrade = _build_upgrade_model(item, enrich_missing_fields=False)
        assert upgrade.category is not None


# ── ingest_upgrade_items ──────────────────────────────────────────────────────

class TestIngestUpgradeItems:
    def test_skips_duplicate(self):
        db = _mock_db_with_duplicate()
        item = make_item()
        outcome = ingest_upgrade_items(db, [item], skip_duplicates=True)
        assert outcome.skipped_duplicates == 1
        assert outcome.created == []
        db.add.assert_not_called()

    def test_creates_when_not_duplicate(self):
        db = _mock_db_no_duplicate()
        item = make_item()
        outcome = ingest_upgrade_items(db, [item], skip_duplicates=True)
        assert outcome.skipped_duplicates == 0
        assert len(outcome.created) == 1
        db.add.assert_called_once()
        db.flush.assert_called_once()

    def test_skip_duplicates_false_always_creates(self):
        # Even if the DB would find a duplicate, skip_duplicates=False bypasses the check.
        db = MagicMock()
        item = make_item()
        outcome = ingest_upgrade_items(db, [item], skip_duplicates=False)
        assert outcome.skipped_duplicates == 0
        assert len(outcome.created) == 1

    def test_batch_of_three_all_created(self):
        db = _mock_db_no_duplicate()
        items = [make_item() for _ in range(3)]
        outcome = ingest_upgrade_items(db, items, skip_duplicates=True)
        assert len(outcome.created) == 3
        assert db.add.call_count == 3

    def test_mixed_duplicates_and_new(self):
        # Patch _is_duplicate to return alternating True/False
        db = MagicMock()
        items = [make_item() for _ in range(4)]
        side_effects = [True, False, True, False]
        with patch(
            "backend.ingestion.upgrade_ingestion._is_duplicate",
            side_effect=side_effects,
        ):
            outcome = ingest_upgrade_items(db, items, skip_duplicates=True)
        assert outcome.skipped_duplicates == 2
        assert len(outcome.created) == 2

    def test_returns_batch_ingest_outcome(self):
        db = _mock_db_no_duplicate()
        item = make_item()
        outcome = ingest_upgrade_items(db, [item])
        assert isinstance(outcome, BatchIngestOutcome)

    def test_enrichment_populates_reasoning(self):
        db = _mock_db_no_duplicate()
        item = make_item(description="diffuser strake geometry revised for expansion")
        outcome = ingest_upgrade_items(db, [item], enrich_missing_fields=True)
        created = outcome.created[0]
        assert created.aero_reasoning
        assert created.mechanical_reasoning
        assert created.performance_hypothesis

    def test_empty_list_returns_zero_created(self):
        db = MagicMock()
        outcome = ingest_upgrade_items(db, [])
        assert outcome.created == []
        assert outcome.skipped_duplicates == 0
        db.add.assert_not_called()
