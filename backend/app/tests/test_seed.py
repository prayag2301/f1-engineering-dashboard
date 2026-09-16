"""Unit tests for seed endpoint behavior (database mocked)."""
from unittest.mock import MagicMock
import pytest
from app.config import get_settings

@pytest.fixture(autouse=True)
def enable_explicit_demo(monkeypatch):
    monkeypatch.setattr(get_settings(),"ENABLE_DEMO_DATA",True)

from app.api.seed import seed_database


class TestSeedDatabase:
    def test_returns_already_seeded_when_team_exists(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = MagicMock()

        result = seed_database(db=db)

        assert result == {"message": "Database already seeded", "seeded": False, "regulation_constraints_seeded": 0}
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_seeds_teams_races_components_upgrades_events_evidence_and_deltas(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter_by.return_value.first.return_value = None

        result = seed_database(db=db)

        assert result["seeded"] is True
        assert result["message"] == "Database seeded successfully"
        assert result["teams"] > 0
        assert result["races"] > 0
        assert result["components"] > 0
        assert result["upgrades"] > 0
        assert result["events"] > 0
        assert result["evidence"] > 0
        assert result["performance_deltas"] > 0

        expected_adds = (
            result["teams"]
            + result["races"]
            + result["components"]
            + result["upgrades"]
            + result["events"]
            + result["evidence"]
            + result["performance_deltas"]
        )
        assert db.add.call_count == expected_adds
        assert db.commit.call_count == 1
