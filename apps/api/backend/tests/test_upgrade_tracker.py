"""Unit tests for upgrade_tracker mapping helpers (no network/database required)."""

from datetime import datetime
from types import SimpleNamespace

from backend.services.upgrade_tracker import (
    _component_hints,
    _default_race,
    _extract_component,
    _extract_race,
    _extract_team,
    _looks_like_upgrade,
    _parse_feed_xml,
    _race_aliases,
    _team_aliases,
)


def _team(name: str, full_name: str):
    return SimpleNamespace(name=name, full_name=full_name)


def _component(name: str, zone: str):
    return SimpleNamespace(name=name, zone=SimpleNamespace(value=zone))


def _race(name: str, season: int, round_number: int, date: datetime):
    return SimpleNamespace(name=name, season=season, round_number=round_number, date=date)


class TestParseFeedXml:
    def test_reads_rss_items(self):
        xml_text = """
        <rss>
          <channel>
            <item>
              <title>Ferrari brings floor upgrade to Bahrain GP</title>
              <description>New fence geometry improves sealing.</description>
              <link>https://example.com/ferrari-floor</link>
            </item>
          </channel>
        </rss>
        """

        entries = _parse_feed_xml(xml_text, source_url="https://example.com/feed", max_items=10)
        assert len(entries) == 1
        assert entries[0].title.startswith("Ferrari brings floor upgrade")
        assert entries[0].link == "https://example.com/ferrari-floor"


class TestUpgradeSignals:
    def test_detects_upgrade_like_text(self):
        assert _looks_like_upgrade("Mercedes introduces revised front wing package") is True

    def test_rejects_non_upgrade_text(self):
        assert _looks_like_upgrade("Weekend timetable and weather forecast") is False


class TestTeamExtraction:
    def test_extracts_team_with_alias(self):
        teams = [
            _team("Red Bull", "Oracle Red Bull Racing"),
            _team("Ferrari", "Scuderia Ferrari"),
        ]
        aliases = _team_aliases(teams)

        team = _extract_team("Oracle Red Bull reveals new diffuser", aliases)
        assert team is not None
        assert team.name == "Red Bull"


class TestComponentExtraction:
    def test_extracts_best_component_match(self):
        components = [
            _component("Front Wing Endplate", "Front Wing"),
            _component("Diffuser Strake", "Diffuser"),
        ]
        hints = _component_hints(components)

        component = _extract_component(
            "The team revised front wing endplate geometry for better outwash",
            hints,
        )
        assert component is not None
        assert component.name == "Front Wing Endplate"


class TestRaceExtraction:
    def test_extracts_race_by_name(self):
        races = [
            _race("Bahrain GP", 2025, 4, datetime(2025, 4, 13)),
            _race("Miami GP", 2025, 6, datetime(2025, 5, 4)),
        ]
        aliases = _race_aliases(races)
        fallback = _default_race(races)

        race = _extract_race("Major floor package planned for Bahrain GP", aliases, fallback)
        assert race is not None
        assert race.name == "Bahrain GP"

    def test_falls_back_to_latest_race(self):
        races = [
            _race("Bahrain GP", 2025, 4, datetime(2025, 4, 13)),
            _race("Miami GP", 2025, 6, datetime(2025, 5, 4)),
        ]
        aliases = _race_aliases(races)
        fallback = _default_race(races)

        race = _extract_race("Undisclosed venue gets update package", aliases, fallback)
        assert race is not None
        assert race.name == "Miami GP"
