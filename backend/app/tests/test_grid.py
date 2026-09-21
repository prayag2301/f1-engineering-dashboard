from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
from uuid import uuid4

import pytest
from app.models.releases import SourceDocument
from app.services.catalog import catalog
from app.services.releases import bootstrap_baseline
from app.services.sources import extract_candidates, TEAM_PATTERNS
from app.schemas.releases import CandidateReview


@pytest.mark.parametrize("team", list(TEAM_PATTERNS))
def test_each_constructor_bootstraps_and_can_be_reviewed(db, team):
    version = bootstrap_baseline(db, team)
    assert version.team_key == team
    assert set(version.component_revisions) == set(catalog()["components"])
    assert bootstrap_baseline(db, team).id == version.id
    assert CandidateReview(team_key=team).team_key == team
    if team not in {"ferrari", "mercedes"}:
        assert "Madrid" in version.label
        assert version.as_of.month == 9


@pytest.mark.parametrize(
    "team,token",
    [
        ("mclaren", "McLaren"),
        ("red_bull", "RB22"),
        ("aston_martin", "AMR26"),
        ("alpine", "Alpine"),
        ("williams", "FW48"),
        ("haas", "VF-26"),
        ("racing_bulls", "Racing Bulls"),
        ("audi", "Audi"),
        ("cadillac", "MAC-26"),
    ],
)
def test_upgrade_assignment_covers_full_grid(team, token):
    source = SourceDocument(
        id=uuid4(),
        text=f"{token} introduced a revised front wing.",
        pages=[],
        source_type="article",
    )
    rows = extract_candidates(source)
    assert len(rows) == 1 and rows[0].team_key == team
    assert rows[0].component == "front_wing" and rows[0].status == "draft"


def test_ambiguous_teams_are_not_guessed():
    source = SourceDocument(
        id=uuid4(),
        text="Red Bull and Racing Bulls introduced revised front wings.",
        pages=[],
        source_type="article",
    )
    assert all(c.team_key is None for c in extract_candidates(source))


def report_module():
    path = Path(__file__).resolve().parents[3] / "scripts/weekly_report.py"
    spec = importlib.util.spec_from_file_location("weekly_report", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_weekly_report_tracks_image_changes_and_undated_sources(monkeypatch):
    report = report_module()
    monkeypatch.setattr(report, "fetch_bytes", lambda url: (b"x", "text/html", url))
    parsed = {
        "title": "McLaren technical gallery",
        "text": "A revised McLaren sidepod.",
        "published_at": None,
        "image_urls": ["https://example.com/one.jpg"],
    }
    monkeypatch.setattr(report, "parse_document", lambda *args: dict(parsed))
    config = {
        "sources": [{"url": "https://www.mclaren.com/gallery", "kind": "document"}]
    }
    first = report.collect(config)
    assert (
        first["documents"][0]["changed"]
        and first["documents"][0]["published_at"] is None
    )
    assert not report.collect(config, previous=first)["documents"][0]["changed"]
    parsed["image_urls"] = ["https://example.com/two.jpg"]
    assert report.collect(config, previous=first)["documents"][0]["changed"]


def test_weekly_report_retains_partial_failures_and_excludes_old_dates(monkeypatch):
    report = report_module()

    def fetch(url):
        if "fia.com" in url:
            raise ValueError("publisher unavailable")
        return b"x", "text/html", url

    monkeypatch.setattr(report, "fetch_bytes", fetch)
    monkeypatch.setattr(
        report,
        "parse_document",
        lambda *args: {
            "title": "Old McLaren article",
            "text": "old",
            "image_urls": [],
            "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        },
    )
    result = report.collect(
        {
            "sources": [
                {"url": "https://fia.com/doc", "kind": "document"},
                {"url": "https://mclaren.com/doc", "kind": "document"},
            ]
        }
    )
    assert (
        result["coverage"] == "partial"
        and result["documents"] == []
        and len(result["errors"]) == 1
    )


def test_discovery_filters_other_sports_and_external_navigation():
    from app.services.sources import discover_links

    feed = b"<rss><channel><item><title>Red Bull upgrades in MotoGP</title><link>https://the-race.com/motogp/red-bull-f1</link></item><item><title>Williams F1 upgrades</title><link>https://the-race.com/formula-1/williams</link></item></channel></rss>"
    assert [
        x["url"]
        for x in discover_links({"kind": "feed"}, feed, "https://the-race.com/rss/")
    ] == ["https://the-race.com/formula-1/williams"]
    html = b'<main><a href="/news/new-floor">technical floor</a><a href="/news/new-floor">duplicate</a><a href="https://other.example/new-floor">technical</a></main><footer><a href="/news/legal">technical</a></footer>'
    assert [
        x["url"]
        for x in discover_links(
            {"kind": "index", "link_pattern": "/news/"},
            html,
            "https://alpinef1.com/news",
        )
    ] == ["https://alpinef1.com/news/new-floor"]


def test_future_season_claim_is_not_imported_as_current_upgrade():
    source = SourceDocument(
        id=uuid4(),
        text="Aston Martin introduced a new floor for its 2027 car.",
        pages=[],
        source_type="article",
    )
    assert extract_candidates(source, season=2026) == []


def test_native_import_rejects_published_versions_before_reading_files(db, tmp_path):
    from app.services.local_builds import adopt_build

    version = bootstrap_baseline(db, "audi")
    version.status = "published"
    db.flush()
    with pytest.raises(ValueError, match="unfinished draft"):
        adopt_build(db, version.id, tmp_path)


def test_native_import_rejects_wrong_constructor_and_active_worker(db, tmp_path):
    from app.services.local_builds import adopt_build
    from app.models.releases import BuildJob

    version = bootstrap_baseline(db, "cadillac")
    (tmp_path / "spec.json").write_text(
        json.dumps({"team_key": "audi", "parameters": {}})
    )
    with pytest.raises(ValueError, match="specification"):
        adopt_build(db, version.id, tmp_path)
    db.add(BuildJob(version_id=version.id, kind="build", status="running"))
    db.flush()
    with pytest.raises(ValueError, match="active build"):
        adopt_build(db, version.id, tmp_path)
